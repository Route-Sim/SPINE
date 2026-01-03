---
title: "WebSocket-Based State Management"
summary: "Implementation of WebSocket-based map and simulation state export/import functionality, replacing file-based operations with real-time data transfer."
source_paths:
  - "world/sim/queues.py"
  - "world/sim/handlers/map.py"
  - "world/sim/handlers/simulation.py"
  - "world/world.py"
last_updated: "2026-01-03"
owner: "Mateusz Polis"
tags: ["websocket", "state-management", "serialization", "api"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["queues.md", "controller.md"]
---

# WebSocket-Based State Management

> **Purpose:** This module implements WebSocket-based export/import functionality for both map-only and complete simulation state, enabling real-time data transfer between client and server without file system operations.

## Context & Motivation

Previously, the system used file-based operations (`export_graph`, `import_graph`) to save and load maps locally on the server. This approach had several limitations:

1. **Client-Server Separation**: Client couldn't directly access server's file system
2. **No State Portability**: Maps were tied to server's local storage
3. **Limited Functionality**: Only graph structure could be saved, not complete simulation state
4. **Security Concerns**: File system access from WebSocket clients

The new implementation addresses these issues by:
- Sending all data via WebSocket messages
- Supporting two modes: map-only and full simulation state
- Enabling client-side storage and management
- Maintaining backward compatibility with existing functionality

## Responsibilities & Boundaries

### In-Scope
- Export/import graph structure (nodes, edges, buildings) via WebSocket
- Export/import complete simulation state (graph + agents + packages + metadata)
- Data serialization and deserialization
- Validation of imported data
- Signal emission for successful operations

### Out-of-Scope
- Client-side storage implementation
- File format conversions
- Data compression
- Incremental state updates

## Architecture & Design

### Two-Mode System

#### Mode 1: Map-Only Export/Import
**Actions**: `map.export`, `map.import`
**Signals**: `map.exported`, `map.imported`

Handles only the graph structure:
- Nodes (with positions and buildings)
- Edges (with properties)
- Building configurations

Does NOT include:
- Agents
- Packages
- Simulation metadata (tick, fuel price, etc.)

**Use Case**: Save/load map layouts without simulation state

#### Mode 2: Full Simulation State Export/Import
**Actions**: `simulation.export_state`, `simulation.import_state`
**Signals**: `simulation.state_exported`, `simulation.state_imported`

Handles complete world state:
- Graph structure (all nodes, edges, buildings)
- All agents with full state
- All packages with status
- Simulation metadata (tick, dt_s, fuel price, current day)

**Use Case**: Save/load complete simulation snapshots (save game functionality)

### Data Flow

#### Export Flow
```
Client Action → ActionQueue → Handler → World.get_full_state() / graph.to_dict()
                                              ↓
                                        Signal with data
                                              ↓
                                        SignalQueue → WebSocket → Client
```

#### Import Flow
```
Client Action (with data) → ActionQueue → Handler → World.restore_from_state() / Graph.from_dict()
                                                           ↓
                                                    Validation & Restoration
                                                           ↓
                                                    Confirmation Signal
```

### Key Components

#### 1. Action Types (queues.py)
New action types added:
- `ActionType.EXPORT_STATE = "simulation.export_state"`
- `ActionType.IMPORT_STATE = "simulation.import_state"`

Modified action types:
- `ActionType.EXPORT_MAP = "map.export"` (now WebSocket-based)
- `ActionType.IMPORT_MAP = "map.import"` (now WebSocket-based)

#### 2. Signal Types (queues.py)
New signal types added:
- `SignalType.SIMULATION_STATE_EXPORTED = "simulation.state_exported"`
- `SignalType.SIMULATION_STATE_IMPORTED = "simulation.state_imported"`

Modified signal types:
- `SignalType.MAP_EXPORTED = "map.exported"` (now includes map_data)
- `SignalType.MAP_IMPORTED = "map.imported"` (confirmation only)

#### 3. Map Handler (handlers/map.py)

**handle_export(_params, context)**
- Validates simulation is stopped
- Calls `context.world.graph.to_dict()`
- Emits `map.exported` signal with graph data

**handle_import(params, context)**
- Validates simulation is stopped
- Validates `map_data` parameter
- Creates new Graph from dict
- Replaces world's graph
- Emits `map.imported` confirmation signal

#### 4. Simulation Handler (handlers/simulation.py)

**handle_export_state(_params, context)**
- Validates simulation is stopped
- Calls `context.world.get_full_state()`
- Emits `simulation.state_exported` signal with complete state

**handle_import_state(params, context)**
- Validates simulation is stopped
- Validates `state_data` parameter
- Calls `context.world.restore_from_state(state_data)`
- Emits `simulation.state_imported` confirmation signal

#### 5. World Methods (world.py)

**get_full_state() → dict[str, Any]**
Returns complete world state:
```python
{
    "graph": self.graph.to_dict(),
    "agents": [agent.serialize_full() for agent in self.agents.values()],
    "packages": [package.to_dict() for package in self.packages.values()],
    "metadata": {
        "tick": self.tick,
        "dt_s": self.dt_s,
        "global_fuel_price": self.global_fuel_price,
        ...
    }
}
```

**restore_from_state(state_data: dict[str, Any]) → None**
Restores world from state dictionary:
1. Validates required fields
2. Restores graph structure
3. Restores metadata (tick, dt_s, fuel price)
4. Clears existing agents and packages
5. Restores packages from data
6. Restores agents (requires agent factory logic)
7. Emits state_restored event

## Algorithms & Complexity

### Export Operations
- **Map Export**: O(N + E) where N = nodes, E = edges
  - Iterates through all nodes and edges once
  - Building serialization is O(B) per node

- **State Export**: O(N + E + A + P) where A = agents, P = packages
  - Graph export: O(N + E)
  - Agent serialization: O(A)
  - Package serialization: O(P)

### Import Operations
- **Map Import**: O(N + E + B)
  - Graph reconstruction from dict
  - Node and edge creation
  - Building restoration

- **State Import**: O(N + E + B + A + P)
  - Map import: O(N + E + B)
  - Agent reconstruction: O(A)
  - Package reconstruction: O(P)
  - Note: Agent reconstruction may be more complex depending on agent type

### Edge Cases
1. **Empty State**: Valid, creates empty world
2. **Partial State**: Rejected with validation error
3. **Invalid Agent Types**: Logged as warning, agent skipped
4. **Concurrent Operations**: Prevented by simulation state check

## Public API / Usage

### Map Export
```json
{
  "action": "map.export",
  "params": {}
}
```

Response:
```json
{
  "signal": "map.exported",
  "data": {
    "map_data": {
      "nodes": [...],
      "edges": [...]
    }
  }
}
```

### Map Import
```json
{
  "action": "map.import",
  "params": {
    "map_data": {
      "nodes": [...],
      "edges": [...]
    }
  }
}
```

### Simulation State Export
```json
{
  "action": "simulation.export_state",
  "params": {}
}
```

Response:
```json
{
  "signal": "simulation.state_exported",
  "data": {
    "state_data": {
      "graph": {...},
      "agents": [...],
      "packages": [...],
      "metadata": {...}
    }
  }
}
```

### Simulation State Import
```json
{
  "action": "simulation.import_state",
  "params": {
    "state_data": {
      "graph": {...},
      "agents": [...],
      "packages": [...],
      "metadata": {...}
    }
  }
}
```

## Implementation Notes

### Design Trade-offs

1. **WebSocket vs File System**
   - ✅ Client has full control over storage
   - ✅ No server file system dependencies
   - ✅ Works across different deployments
   - ❌ Larger WebSocket messages
   - ❌ Client must handle storage

2. **Two Modes vs Single Mode**
   - ✅ Flexibility for different use cases
   - ✅ Smaller payloads for map-only operations
   - ✅ Clear separation of concerns
   - ❌ More API endpoints to maintain
   - ❌ Potential confusion about which to use

3. **Complete State vs Incremental**
   - ✅ Simple, atomic operations
   - ✅ Guaranteed consistency
   - ❌ Large payloads for full state
   - ❌ No support for partial updates

### Agent Reconstruction

The `restore_from_state` method includes basic agent reconstruction logic:

```python
if agent_kind == "truck":
    agent = Truck.from_dict(agent_data, self)
    self.agents[agent_id] = agent
```

**Limitations**:
- Currently only supports truck agents
- Unknown agent types are logged and skipped
- Requires `from_dict` class method on agent classes

**Future Enhancement**:
Consider implementing an agent factory pattern:
```python
agent_factory = AgentFactory()
agent = agent_factory.create_from_dict(agent_kind, agent_data, self)
```

### Validation

Both import operations validate:
1. Simulation is stopped (prevents race conditions)
2. Required parameters are present
3. Data types are correct
4. Graph structure is valid (via Graph.from_dict)

Errors are:
- Logged to server console
- Emitted as error signals to client
- Raised as exceptions (caught by action processor)

## Security & Reliability

### Security Considerations

1. **No File System Access**: Eliminates path traversal vulnerabilities
2. **Data Validation**: All imported data is validated before use
3. **State Isolation**: Each client manages their own state data
4. **Simulation Lock**: Cannot import while simulation is running

### Error Handling

All handlers implement comprehensive error handling:
```python
try:
    # Operation
    _emit_signal(context, success_signal)
except ValueError as e:
    _emit_error(context, f"Validation error: {e}")
    raise
except Exception as e:
    _emit_error(context, f"Unexpected error: {e}")
    raise
```

### Reliability Features

1. **Atomic Operations**: State is fully replaced or not at all
2. **Validation Before Modification**: Data is validated before world state changes
3. **Event Emission**: State changes are tracked via events
4. **Logging**: All operations are logged for debugging

## Performance

### Benchmarks

Typical operation times (estimated):
- Map export (100 nodes): ~10ms
- Map import (100 nodes): ~20ms
- State export (100 nodes, 10 agents): ~15ms
- State import (100 nodes, 10 agents): ~30ms

### Optimization Opportunities

1. **Compression**: Add gzip compression for large state data
2. **Incremental Updates**: Support partial state updates
3. **Lazy Loading**: Stream large datasets in chunks
4. **Caching**: Cache serialized state for repeated exports

### Known Bottlenecks

1. **Large Graphs**: O(N) serialization can be slow for 1000+ nodes
2. **Agent Reconstruction**: Complex agent types may be slow to recreate
3. **WebSocket Message Size**: Very large states may hit message size limits

## Testing

### Test Coverage

Key test scenarios:
1. Export empty map
2. Export map with buildings
3. Import valid map data
4. Import invalid map data (missing fields)
5. Export complete state
6. Import complete state
7. Attempt export while simulation running (should fail)
8. Attempt import while simulation running (should fail)

### Integration Tests

See `tests/world/test_sim_controller.py` for integration tests covering:
- End-to-end export/import flows
- Error handling
- Signal emission
- State consistency

## References

### Related Modules
- [queues.md](queues.md) - Action and signal definitions
- [controller.md](controller.md) - Simulation controller
- [world.md](../world.md) - World state management
- [graph.md](../graph/graph.md) - Graph serialization

### API Documentation
- [api-reference.md](../../../api-reference.md) - Complete API reference with examples

### Design Decisions
- Replaced file-based operations with WebSocket data transfer
- Separated map-only and full state operations for flexibility
- Implemented atomic state restoration for consistency
