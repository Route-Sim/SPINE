---
title: "Simulation Queue Infrastructure"
summary: "Thread-safe queues exposing canonical <domain>.<action>/<signal> envelopes between the simulation loop and WebSocket boundary."
source_paths:
  - "world/sim/queues.py"
  - "tests/world/test_sim_queues.py"
last_updated: "2025-12-09"
owner: "Mateusz Polis"
tags: ["module", "api", "infra"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["controller.md", "handlers/agent.md", "handlers/map.md", "../../io/websocket_server.md"]
---

# Simulation Queue Infrastructure

> **Purpose:** Provides thread-safe communication infrastructure between the simulation controller and WebSocket server threads using validated message queues.

## Context & Motivation

The SPINE simulation requires bidirectional communication between:
- **Frontend → Simulation**: Actions to start/stop/pause simulation, add/remove agents, manage packages and sites
- **Simulation → Frontend**: Signals like tick markers, agent updates, world events, package lifecycle events
- Canonical `<domain>.<action>` / `<domain>.<signal>` identifiers keep this communication aligned with the published WebSocket API.

This module implements thread-safe queues with Pydantic validation to ensure reliable, type-safe communication between threads.

## Responsibilities & Boundaries

**In-scope:**
- Thread-safe queue implementations for actions and signals
- Pydantic models for message validation
- Convenience functions for common message types
- Package lifecycle signal definitions
- Site management signal definitions
- Queue size management and error handling

**Out-of-scope:**
- Message routing logic (handled by controller/server)
- WebSocket protocol details (handled by FastAPI)
- Simulation logic (handled by World class)

## Architecture & Design

### Core Components

**ActionQueue**: Thread-safe queue for frontend → simulation actions
- Backed by `queue.Queue` with configurable maxsize
- Exposes blocking, timeout-aware `put`/`get` plus `get_nowait()` for polling loops
- Stores fully validated `ActionRequest` envelopes (`{"action": "<domain>.<action>", "params": {...}}`)

**SignalQueue**: Thread-safe queue for simulation → frontend signals
- Mirrors the ActionQueue API for symmetry
- Streams `Signal` envelopes back to the WebSocket broadcaster

**Message Models & Enumerations**
- `ActionRequest` (defined in `world/sim/actions/action_parser.py`) guarantees the canonical action shape and delegates field validation to the parser layer
- `ActionType` enumerates the supported `<domain>.<action>` identifiers used throughout helpers and tests
- `Signal` consolidates outbound payloads into `{ "signal": "<domain>.<signal>", "data": {...} }`
- `SignalType` enumerates the canonical outbound identifiers, ensuring parity with the WebSocket contract

### Data Flow

```
Frontend → WebSocket → ActionQueue → SimulationController → World
World → SimulationController → SignalQueue → WebSocket → Frontend
```

## Algorithms & Complexity

**Queue Operations**: O(1) for put/get operations
- Thread-safe using Python's `queue.Queue`
- Lock-free for single-threaded access patterns
- Timeout-based blocking for multi-threaded coordination

**Message Validation**: O(n) where n is message size
- Pydantic validation on all incoming messages
- Early rejection of malformed actions
- Type coercion and field validation
- Context-aware validation (e.g., `agent_id` required for `ADD_AGENT` actions)
- Model validators ensure data consistency across fields

## Public API / Usage

### Queue Management
```python
# Create queues
action_queue = ActionQueue(maxsize=1000)
signal_queue = SignalQueue(maxsize=1000)

# Enqueue validated envelopes
action_queue.put(create_start_action(tick_rate=30.0), timeout=1.0)
signal = signal_queue.get_nowait()
```

### Canonical Envelope Shapes

```json
{
  "action": "<domain>.<action>",
  "params": {
    "param_1": "param_1_value",
    "param_2": "param_2_value"
  }
}

{
  "signal": "<domain>.<signal>",
  "data": {
    "param_1": "value",
    "param_2": 123
  }
}
```

### Building Creation Round-trip

```python
from world.sim.queues import (
    create_building_create_action,
    create_building_created_signal,
)

# Parking building creation
create_action = create_building_create_action(
    building_id="parking-node42",
    node_id=42,
    capacity=40,
    building_type="parking",
)
action_queue.put(create_action, timeout=1.0)

# Simulation thread constructs Parking instance and broadcasts confirmation
parking_payload = {
    "id": "parking-node42",
    "type": "parking",
    "capacity": 40,
    "current_agents": [],
}
signal_queue.put(
    create_building_created_signal(
        building_data=parking_payload,
        node_id=42,
        tick=state.current_tick,
    )
)
```

Use this helper pair to request additional building capacity at runtime. The handler supports both parking buildings (with `capacity` parameter) and site buildings (with `name` and `activity_rate` parameters). The handler returns the canonical building data (parking buildings include an empty `current_agents` list until dedicated parking logic assigns trucks; site buildings include `active_packages` and `statistics`).

**Note**: The `create_building_create_action` helper currently only supports parking buildings. For site creation, construct the action manually with `building_type="site"`, `name`, and `activity_rate` parameters. A future enhancement may add a dedicated `create_site_create_action` helper.

### Agent Describe Round-trip

```python
from core.types import AgentID
from world.sim.queues import (
    create_agent_described_signal,
    create_describe_agent_action,
)

# Build a describe request from the frontend thread
describe_action = create_describe_agent_action(agent_id="truck-1")
action_queue.put(describe_action, timeout=1.0)

# Later, emit the corresponding response signal from the simulation thread
# `world` references the HandlerContext.world instance in the simulation loop
agent_state = world.agents[AgentID("truck-1")].serialize_full()
# `state` references the current `SimulationState` on the simulation thread
signal_queue.put(create_agent_described_signal(agent_state, tick=state.current_tick))
```

This helper pair formalises the request/response contract for on-demand agent inspections without requiring the simulation loop to be running.

### Agent List Round-trip

```python
from world.sim.queues import create_agent_listed_signal, create_list_agents_action

# Optional filter by kind
list_action = create_list_agents_action(agent_kind="truck")
action_queue.put(list_action, timeout=1.0)

# Simulation thread aggregates agent payloads
agents_payload = [
    world.agents[agent_id].serialize_full() | {"agent_id": str(agent_id)}
    for agent_id in world.agents
]
signal_queue.put(
    create_agent_listed_signal(
        agents=agents_payload,
        total=len(agents_payload),
        tick=state.current_tick,
    )
)
```

Use this pattern to provide the UI with a consistent snapshot of all (or filtered) agents without requesting a full state dump.

### Package Lifecycle Signals
```python
# Package created signal
package_created = create_package_created_signal(
    package_data={
        "id": "pkg-123",
        "origin_site": "warehouse-a",
        "destination_site": "warehouse-b",
        "size": 15.0,
        "value_currency": 1500.0,
        "priority": "HIGH",
        "urgency": "EXPRESS",
        "spawn_tick": 1000,
        "pickup_deadline_tick": 4600,
        "delivery_deadline_tick": 8200,
        "status": "WAITING_PICKUP"
    },
    tick=1000
)

# Package expired signal
package_expired = create_package_expired_signal(
    package_id="pkg-123",
    site_id="warehouse-a",
    value_lost=1500.0,
    tick=4600
)

# Package picked up signal
package_picked_up = create_package_picked_up_signal(
    package_id="pkg-123",
    agent_id="truck-1",
    tick=2000
)

# Package delivered signal
package_delivered = create_package_delivered_signal(
    package_id="pkg-123",
    site_id="warehouse-b",
    value=1500.0,
    tick=5000
)
```

### Building Update Signals

Buildings emit update signals only when their state explicitly changes (unlike agents which update every tick). This event-driven approach reduces signal traffic for relatively static building state.

```python
from world.sim.queues import create_building_updated_signal

# Building updated signal (emitted when parking occupancy, site packages, or statistics change)
building_updated = create_building_updated_signal(
    building_id="parking-node42",
    building_data={
        "id": "parking-node42",
        "type": "parking",
        "capacity": 40,
        "current_agents": ["truck-1", "truck-2"]
    },
    tick=1500
)
```

### ActionType Identifiers
- `simulation.start`: Begin simulation with optional `tick_rate` and `speed`
- `simulation.stop`: Stop simulation
- `simulation.pause` / `simulation.resume`: Pause or resume the loop
- `simulation.update`: Update simulation configuration (e.g., change tick rate and/or speed - at least one required)
- `agent.create` / `agent.delete` / `agent.update`: Agent management primitives
- `agent.describe`: Request the full serialized state for a single agent
- `agent.list`: Request aggregated serialized state for all agents, optionally filtered by `agent_kind`
- `map.export` / `map.import` / `map.create`: Map persistence controls
- `state.request`: Request complete state snapshot
- `package.create` / `package.cancel`: Package lifecycle (future)
- `site.create` / `site.update`: Site management (future)
- `building.create`: Provision buildings (parking or site) on an existing node

### Signal Format

All signals follow the standardized format matching the API reference:

```json
{
  "signal": "domain.signal",
  "data": {
    "field1": value1,
    "field2": value2,
    ...
  }
}
```

All contextual information (tick, agent_id, error messages, etc.) is consolidated into the `data` dict. The `signal` field uses domain.signal format (e.g., `"simulation.started"`, `"agent.updated"`, `"error"`).

### `map.created` Payload

The `map.created` helper embeds a complete graph snapshot alongside generation metadata. The snapshot includes all nodes with their buildings, edges, and all graph structure data.

```json
{
  "signal": "map.created",
  "data": {
    "map_width": 10000,
    "...": "...",
    "generated_sites": 45,
    "graph": {
      "nodes": [
        {"id": "1", "x": 0.0, "y": 0.0, "buildings": []},
        {"id": "2", "x": 120.0, "y": 45.0, "buildings": [{"id": "site-1", "type": "site", ...}]}
      ],
      "edges": [
        {
          "id": "10",
          "from_node": "1",
          "to_node": "2",
          "length_m": 115.0,
          "mode": 1,
          "road_class": "L",
          "lanes": 2,
          "max_speed_kph": 50.0,
          "weight_limit_kg": null
        }
      ]
    }
  }
}
```

The signal includes complete graph data with all buildings, providing full map fidelity in a single response.

### Signal Types
- `tick.start`/`tick.end`: Tick boundary markers (data includes `tick`)
- `agent.described`: Full agent snapshot emitted in direct response to `agent.describe` (data includes serialized agent state and `tick`)
- `agent.listed`: Aggregated agent payload emitted in response to `agent.list` (data includes `total`, `agents`, and `tick`)
- `agent.updated`: Agent state changes (data includes `agent_id`, `tick`, and agent state)
- `event.created`: General world events (data includes `tick` and event details)
- `error`: Error notifications (data includes `code`, `message`, optional `tick`)
- `simulation.started`/`simulation.stopped`/`simulation.paused`/`simulation.resumed`: Simulation state changes
- `simulation.updated`: Simulation configuration updated (data includes `tick_rate` and `speed`)
- `simulation.tick_rate_warning`: Warning when tick rate cannot be maintained (data includes `target_tick_rate`, `actual_processing_time_ms`, `required_time_ms`, `message`, optional `tick`)
- `map.exported`/`map.imported`/`map.created`: Map operation confirmations
- `state.snapshot_start`/`state.snapshot_end`: State snapshot boundaries
- `state.full_map_data`: Complete map structure
- `state.full_agent_data`: Complete agent state
- `package.created`/`package.expired`/`package.picked_up`/`package.delivered`: Package lifecycle events
- `building.created`: Building (parking or site) instantiated on the specified node (payload includes `building` dict and `node_id`)
- `building.updated`: Building state changed (payload includes `building_id`, `building` dict, and `tick`) - emitted only when state explicitly changes

## Implementation Notes

**Thread Safety**: Uses Python's built-in `queue.Queue` which is thread-safe

**Validation**: Upstream `ActionParser` produces `ActionRequest` envelopes; queues assume canonical structure and focus on transport semantics
- Helper factories ensure their payloads satisfy downstream handler expectations
- `Signal` enforces the `data` payload to always be a dictionary, matching the documented API

**Error Handling**: Queue full/timeout exceptions propagated to callers

**Performance**: Non-blocking operations available for high-throughput scenarios

## Tests

Comprehensive test coverage includes:
- Basic queue operations (put/get/empty/size)
- Thread safety with concurrent operations
- Message validation and error handling
- Convenience function correctness
- Queue full/timeout scenarios
- Canonical envelope helpers match the documented `<domain>.<action>` / `<domain>.<signal>` protocol

## Performance

**Benchmarks**:
- Queue operations: ~1μs per operation
- Message validation: ~10μs per message
- Memory usage: ~1KB per 1000 queued messages

**Bottlenecks**: Pydantic validation can be slow for large messages
**Optimizations**: Use `get_nowait()` for polling, batch operations where possible

## Security & Reliability

**Validation**: All incoming messages validated before processing
**Error Handling**: Graceful degradation on queue full/timeout
**Resource Management**: Configurable queue sizes prevent memory exhaustion
**Logging**: All queue operations logged for debugging

## References

- [world/sim/controller.py](../controller.md) - Action processing
- [world/io/websocket_server.py](../../io/websocket_server.md) - Signal broadcasting
- [Pydantic Documentation](https://docs.pydantic.dev/) - Message validation
