---
title: "Simulation Queue Infrastructure"
summary: "Thread-safe queues exposing canonical <domain>.<action>/<signal> envelopes between the simulation loop and WebSocket boundary."
source_paths:
  - "world/sim/queues.py"
  - "tests/world/test_sim_queues.py"
last_updated: "2025-11-08"
owner: "Mateusz Polis"
tags: ["module", "api", "infra"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["controller.md", "handlers/map.md", "../../io/websocket_server.md"]
---

# Simulation Queue Infrastructure

> **Purpose:** Provides thread-safe communication infrastructure between the simulation controller and WebSocket server threads using validated message queues.

## Context & Motivation

The SPINE simulation requires bidirectional communication between:
- **Frontend → Simulation**: Commands to start/stop/pause simulation, add/remove agents, manage packages and sites
- **Simulation → Frontend**: Events like tick markers, agent updates, world events, package lifecycle events
- Canonical `<domain>.<action>` / `<domain>.<signal>` identifiers keep this communication aligned with the published WebSocket API.

This module implements thread-safe queues with Pydantic validation to ensure reliable, type-safe communication between threads.

## Responsibilities & Boundaries

**In-scope:**
- Thread-safe queue implementations for commands and events
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

**ActionQueue**: Thread-safe queue for frontend → simulation commands
- Backed by `queue.Queue` with configurable maxsize
- Exposes blocking, timeout-aware `put`/`get` plus `get_nowait()` for polling loops
- Stores fully validated `ActionRequest` envelopes (`{"action": "<domain>.<action>", "params": {...}}`)

**SignalQueue**: Thread-safe queue for simulation → frontend events
- Mirrors the ActionQueue API for symmetry
- Streams `Signal` envelopes back to the WebSocket broadcaster

**Message Models & Enumerations**
- `ActionRequest` (defined in `world/sim/actions/action_parser.py`) guarantees the canonical command shape and delegates field validation to the parser layer
- `ActionType` enumerates the supported `<domain>.<action>` identifiers used throughout helpers and tests
- `Signal` consolidates outbound payloads into `{ "signal": "<domain>.<signal>", "data": {...} }`
- `SignalType` enumerates the canonical outbound identifiers, ensuring parity with the WebSocket contract

### Data Flow

```
Frontend → WebSocket → CommandQueue → SimulationController → World
World → SimulationController → EventQueue → WebSocket → Frontend
```

## Algorithms & Complexity

**Queue Operations**: O(1) for put/get operations
- Thread-safe using Python's `queue.Queue`
- Lock-free for single-threaded access patterns
- Timeout-based blocking for multi-threaded coordination

**Message Validation**: O(n) where n is message size
- Pydantic validation on all incoming messages
- Early rejection of malformed commands
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

### Package Lifecycle Signals
```python
# Package created signal
package_created = create_package_created_signal(
    package_data={
        "id": "pkg-123",
        "origin_site": "warehouse-a",
        "destination_site": "warehouse-b",
        "size_kg": 25.0,
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

# Site statistics update signal
site_stats = create_site_stats_signal(
    site_id="warehouse-a",
    stats={
        "packages_generated": 150,
        "packages_picked_up": 140,
        "packages_delivered": 135,
        "packages_expired": 5,
        "total_value_delivered": 150000.0,
        "total_value_expired": 5000.0
    },
    tick=1000
)
```

### ActionType Identifiers
- `simulation.start`: Begin simulation with optional `tick_rate`
- `simulation.stop`: Stop simulation
- `simulation.pause` / `simulation.resume`: Pause or resume the loop
- `tick_rate.update`: Change simulation speed (`tick_rate` required)
- `agent.create` / `agent.delete` / `agent.update`: Agent management primitives
- `map.export` / `map.import` / `map.create`: Map persistence controls
- `state.request`: Request complete state snapshot
- `package.create` / `package.cancel`: Package lifecycle (future)
- `site.create` / `site.update`: Site management (future)

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

The `map.created` helper now embeds a lightweight graph snapshot alongside generation metadata. The snapshot omits building payloads and agent data to keep the signal concise.

```json
{
  "signal": "map.created",
  "data": {
    "map_width": 10000,
    "...": "...",
    "generated_sites": 45,
    "graph": {
      "nodes": [
        {"id": "1", "x": 0.0, "y": 0.0},
        {"id": "2", "x": 120.0, "y": 45.0}
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

Use `state.full_map_data` when a complete dump (including building inventories) is required.

### Signal Types
- `tick.start`/`tick.end`: Tick boundary markers (data includes `tick`)
- `agent.updated`: Agent state changes (data includes `agent_id`, `tick`, and agent state)
- `event.created`: General world events (data includes `tick` and event details)
- `error`: Error notifications (data includes `code`, `message`, optional `tick`)
- `simulation.started`/`simulation.stopped`/`simulation.paused`/`simulation.resumed`: Simulation state changes
- `map.exported`/`map.imported`/`map.created`: Map operation confirmations
- `state.snapshot_start`/`state.snapshot_end`: State snapshot boundaries
- `state.full_map_data`: Complete map structure
- `state.full_agent_data`: Complete agent state
- `package.created`/`package.expired`/`package.picked_up`/`package.delivered`: Package lifecycle events
- `site.stats_update`: Site statistics updates

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

- [world/sim/controller.py](../controller.md) - Command processing
- [world/io/websocket_server.py](../../io/websocket_server.md) - Event broadcasting
- [Pydantic Documentation](https://docs.pydantic.dev/) - Message validation
