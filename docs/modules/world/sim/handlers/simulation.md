---
title: "Simulation Control Action Handler"
summary: "Orchestrates simulation lifecycle commands (start, stop, pause, resume, update) with consistent state management and signal emission."
source_paths:
  - "world/sim/handlers/simulation.py"
last_updated: "2025-11-23"
owner: "Mateusz Polis"
tags: ["module", "api", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["agent.md", "building.md", "map.md"]
---

# Simulation Control Action Handler

> **Purpose:** Executes simulation control actions (`simulation.start`, `simulation.stop`, `simulation.pause`, `simulation.resume`, `simulation.update`) by managing simulation state and emitting canonical signals to synchronize the frontend with backend lifecycle events.

## Context & Motivation
- Problem solved
  - Centralizes all simulation control commands behind a unified handler ensuring consistent state transitions and signal emissions.
  - Provides a canonical domain for simulation configuration updates (e.g., tick rate changes).
- Requirements and constraints
  - Must ensure proper state transitions (e.g., can only pause when running, can only resume when paused).
  - Tick rate updates must validate input parameters and apply clamping limits.
  - All state changes must emit corresponding signals for frontend synchronization.
- Dependencies and assumptions
  - Relies on `HandlerContext` for access to `SimulationState`, `SignalQueue`, and logger.
  - Uses helper factories from `world.sim.queues` to emit canonical signals.

## Responsibilities & Boundaries
- In-scope
  - Starting and stopping simulation execution.
  - Pausing and resuming the simulation loop.
  - Updating simulation configuration (tick rate).
  - Emitting lifecycle signals: `simulation.started`, `simulation.stopped`, `simulation.paused`, `simulation.resumed`, `simulation.updated`.
  - Validating action parameters before applying state changes.
- Out-of-scope
  - World stepping logic (delegated to `SimulationController` and `World`).
  - WebSocket routing or action parsing (handled by controller and `ActionRegistry`).
  - Agent or map management (handled by dedicated handlers).

## Architecture & Design
- Key functions, classes, or modules
  - `SimulationActionHandler.handle_start`: Initializes simulation with optional tick rate parameter.
  - `SimulationActionHandler.handle_stop`: Halts simulation execution.
  - `SimulationActionHandler.handle_pause`: Suspends simulation loop while maintaining running state.
  - `SimulationActionHandler.handle_resume`: Continues simulation from paused state.
  - `SimulationActionHandler.handle_update`: Updates simulation configuration (currently supports tick rate).
  - `_emit_signal`: Internal helper for thread-safe signal emission with error handling.
- Data flow and interactions
  - Handlers read parameters from action envelopes, modify `SimulationState`, and emit signals via `SignalQueue`.
  - State transitions are atomic within handler methods.
  - Signal emission failures are logged but don't block state transitions.
- State management or concurrency
  - Thread-safe signal queue operations with timeout handling.
  - State changes are synchronized through `SimulationState` methods.
- Resource handling
  - Signal queue operations use 1.0s timeout to prevent indefinite blocking.
  - No external resources beyond in-memory state and queue structures.

## Algorithms & Complexity
- State transitions: O(1) - simple flag updates
- Signal emission: O(1) - queue put operation with timeout
- Tick rate validation: O(1) - type check and bounds clamping in `SimulationState.set_tick_rate`

## Public API / Usage

### Start Simulation
```python
handler.handle_start({"tick_rate": 30}, context)
# Emits: {"signal": "simulation.started", "data": {"tick_rate": 30}}
```

### Stop Simulation
```python
handler.handle_stop({}, context)
# Emits: {"signal": "simulation.stopped", "data": {}}
```

### Pause/Resume
```python
handler.handle_pause({}, context)
# Emits: {"signal": "simulation.paused", "data": {}}

handler.handle_resume({}, context)
# Emits: {"signal": "simulation.resumed", "data": {}}
```

### Update Configuration
```python
handler.handle_update({"tick_rate": 50}, context)
# Emits: {"signal": "simulation.updated", "data": {"tick_rate": 50}}
```

## Implementation Notes
- `handle_start` accepts optional `tick_rate` parameter; if omitted, uses current state value.
- `handle_update` requires `tick_rate` parameter and emits confirmation signal with the applied value.
- Tick rate values are converted to integers for signal emission to match API specification.
- Pause/resume only take effect when simulation is in appropriate state (running for pause, running+paused for resume).
- Signal emission failures are logged but don't propagate exceptions to maintain handler reliability.

## Tests (If Applicable)
- See `tests/world/test_sim_controller.py` for integration scenarios covering:
  - Start simulation with custom tick rate
  - Stop simulation state transition
  - Pause and resume state management
  - Update simulation configuration
  - Signal emission verification

## Performance
- All operations complete in constant time O(1)
- Signal queue operations use 1.0s timeout to prevent blocking
- No memory allocations beyond transient signal objects

## Security & Reliability
- Parameter validation prevents invalid tick rate values
- Type checking ensures numeric tick rate parameters
- Error handling prevents signal queue failures from corrupting state
- Logging provides audit trail for all state transitions

## References
- [SimulationState](../state.md) - State management
- [Action Registry](../actions/action-registry.md) - Handler registration
- [Queues](../queues.md) - Signal emission helpers
- [Simulation Controller](../controller.md) - Integration point
