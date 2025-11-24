---
title: "Simulation Controller"
summary: "Manages the simulation loop, processes commands from frontend, and emits events to WebSocket clients in a dedicated thread. Includes performance monitoring, timing adjustments, and statistics collection."
source_paths:
  - "world/sim/controller.py"
last_updated: "2025-01-27"
owner: "Mateusz Polis"
tags: ["module", "api", "algorithm"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["queues.md"]
---

# Simulation Controller

> **Purpose:** Orchestrates the simulation lifecycle by running the World step loop in a dedicated thread, processing frontend commands, and emitting events to WebSocket clients.

## Context & Motivation

The simulation needs to run continuously while accepting real-time commands from the frontend. This controller bridges the gap between:
- **Continuous simulation**: World.step() loop at configurable tick rate
- **Interactive control**: Start/stop/pause commands from frontend
- **Real-time updates**: Agent modifications and state changes
- **Event streaming**: Tick markers and agent updates to frontend

## Responsibilities & Boundaries

**In-scope:**
- Simulation loop management with configurable tick rate and speed
- Command processing from frontend (start/stop/pause/modify agents)
- Event emission to frontend (tick markers, agent updates, errors)
- Thread-safe state management (running/paused/stopped)
- Agent lifecycle management (add/remove/modify)
- Performance timing and tick rate maintenance
- Statistics collection and background file writing
- Warning signals when tick rate cannot be maintained

**Out-of-scope:**
- WebSocket communication (handled by WebSocketServer)
- World simulation logic (handled by World class)
- Message validation (handled by Pydantic models)

## Architecture & Design

### Core Components

**SimulationController**: Main orchestrator class
- Owns World instance and manages its lifecycle
- Runs in dedicated thread with configurable tick rate
- Processes commands from CommandQueue
- Emits events to EventQueue

**SimulationState**: Thread-safe state management
- Running/paused/stopped states
- Current tick counter and tick rate
- Thread-safe access with locks

### Command Processing Flow

```
CommandQueue → _process_commands() → _handle_command() → World operations
```

### Event Emission Flow

```
World.step() → _process_step_result() → EventQueue → WebSocket clients
```

### Thread Architecture

```
Main Thread: WebSocket server + event broadcasting
Simulation Thread: Controller loop + World.step()
```

## Algorithms & Complexity

**Simulation Loop**: O(1) per tick
- Fixed-time step simulation with configurable rate and speed
- Command processing between ticks with timing measurement
- Event emission after each tick
- Sleep time adjustment to account for processing overhead
- Performance statistics collection per tick

**Command Processing**: O(n) where n = number of queued commands
- Non-blocking command processing with timing measurement
- Error handling with event emission
- Agent lifecycle management

**State Management**: O(1) with thread-safe locks
- Atomic state transitions
- Thread-safe property access
- Lock contention minimized

**Statistics Collection**: O(1) per tick, O(b) per batch write
- Per-tick statistics stored in memory
- Batched writes to file (default 1000 ticks per batch)
- Background thread for non-blocking file I/O

## Public API / Usage

### Controller Lifecycle
```python
controller = SimulationController(world, command_queue, event_queue)
controller.start()  # Start simulation thread
controller.stop()   # Stop simulation thread
```

### Command Handling
```python
# Start simulation
command = SimCommand(type=CommandType.START, tick_rate=30.0)
command_queue.put(command)

# Add agent
command = SimCommand(
    type=CommandType.ADD_AGENT,
    agent_id="agent_1",
    agent_kind="transport",
    agent_data={"x": 100, "y": 200}
)
command_queue.put(command)
```

### State Queries
```python
# Check simulation state
if controller.state.running:
    print(f"Tick: {controller.state.current_tick}")
    print(f"Rate: {controller.state.tick_rate}")
```

## Implementation Notes

**Thread Safety**: All state access protected by locks
**Error Handling**: Exceptions caught and emitted as error events
**Agent Management**: Dynamic agent creation based on kind
**Tick Markers**: Explicit tick_start/tick_end events for frontend synchronization
**State Snapshots**: Complete state transmission for frontend initialization and recovery

### State Snapshot Functionality

The controller provides complete state snapshot capabilities for frontend synchronization:

**When State Snapshots Are Sent**:
- On simulation start (after `SIMULATION_STARTED` signal)
- When new WebSocket clients connect during running/paused simulation
- On explicit `REQUEST_STATE` action

**State Snapshot Sequence**:
1. `STATE_SNAPSHOT_START` - Marks beginning of transmission
2. `FULL_MAP_DATA` - Complete graph structure (nodes, edges, buildings)
3. `FULL_AGENT_DATA` - One signal per agent with complete state
4. `STATE_SNAPSHOT_END` - Marks end of transmission

**State Data Includes**:
- Complete map structure with all nodes and edges
- All agent states with position, status, and telemetry
- Simulation metadata (tick, time, etc.)

### Command Types Handled
- `START`: Begin simulation with optional tick rate (triggers state snapshot)
- `STOP`: Stop simulation completely
- `PAUSE`/`RESUME`: Pause/resume running simulation
- `SET_TICK_RATE`: Change simulation speed
- `ADD_AGENT`: Create new agent with specified kind and data
- `DELETE_AGENT`: Remove agent by ID
- `MODIFY_AGENT`: Update agent properties
- `EXPORT_MAP`/`IMPORT_MAP`: Map management operations
- `REQUEST_STATE`: Request complete state snapshot

### Event Types Emitted
- `TICK_START`/`TICK_END`: Tick boundary markers
- `AGENT_UPDATE`: Agent state changes (only when changed)
- `WORLD_EVENT`: General world events
- `ERROR`: Error notifications
- `SIMULATION_*`: Simulation state changes
- `SIMULATION_TICK_RATE_WARNING`: Warning when tick rate cannot be maintained
- `MAP_EXPORTED`/`MAP_IMPORTED`: Map operation confirmations
- `STATE_SNAPSHOT_START`/`STATE_SNAPSHOT_END`: State snapshot boundaries
- `FULL_MAP_DATA`: Complete map structure
- `FULL_AGENT_DATA`: Complete agent state

## Tests

Comprehensive test coverage includes:
- Controller lifecycle (start/stop)
- Command processing for all command types
- State management and thread safety
- Error handling and event emission
- Integration with World class
- Agent lifecycle management

## Performance

**Tick Rate**: Configurable from 0.1 to 100 Hz
**Speed Control**: Simulation speed (simulation seconds per real second) configurable from 0.01 to 10.0
**Timing Precision**: Uses `time.perf_counter()` for high-precision timing measurements
**Sleep Adjustment**: Automatically adjusts sleep time to account for processing overhead, maintaining exact tick rate
**Command Processing**: Non-blocking, processes all queued commands per tick with timing measurement
**Memory Usage**: Minimal overhead, reuses World instance
**Thread Overhead**: Two threads: simulation loop + statistics writer
**Statistics Collection**: Batched writes (default 1000 ticks) to prevent I/O blocking
**Warning System**: Emits warnings when processing time exceeds available time per tick

## Security & Reliability

**Error Isolation**: Simulation errors don't crash WebSocket server
**Graceful Degradation**: Invalid commands emit error events
**Resource Management**: Configurable tick rate prevents CPU overload
**Logging**: All operations logged with appropriate levels

## Performance Monitoring & Statistics

The controller includes comprehensive performance monitoring:

### Timing Measurements
- **Action Processing Time**: Measured for each tick using `time.perf_counter()`
- **Simulation Step Time**: Measured for each world.step() call
- **Total Processing Time**: Sum of action processing + simulation step
- **Achieved Rate**: Calculated as `1000.0 / total_time_ms` (ticks per second)

### Statistics Collection
- Statistics are collected per tick using `TickStatisticsDTO`
- Batched into `StatisticsBatchDTO` (default: 1000 ticks per batch)
- Written to JSON files in `stats/` directory by background thread
- File naming: `stats_batch_{batch_id:06d}_{timestamp}.json`

### Tick Rate Maintenance
- Sleep time is adjusted: `max(0, (1.0 / tick_rate) - processing_time)`
- Ensures exact tick rate is maintained when processing is fast enough
- Warning signal emitted when processing time exceeds available time per tick
- Warning includes: target tick rate, actual processing time, required time, and descriptive message

### Configuration
- `stats_dir`: Directory for statistics files (default: `stats/`)
- `stats_batch_size`: Number of ticks per batch (default: 1000)

## References

- [world/sim/queues.md](queues.md) - Message infrastructure
- [world/sim/dto/statistics-dto.md](dto/statistics-dto.md) - Statistics DTOs
- [world/world.md](../world.md) - World simulation logic
- [agents/base.md](../../../agents/base.md) - Agent base classes
