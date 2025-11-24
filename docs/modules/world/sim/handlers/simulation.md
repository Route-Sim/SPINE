---
title: "Simulation Control Action Handler"
summary: "Orchestrates simulation lifecycle commands (start, stop, pause, resume, update) with consistent state management and signal emission. Handles speed and tick_rate parameters with automatic dt_s calculation."
source_paths:
  - "world/sim/handlers/simulation.py"
last_updated: "2025-01-27"
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
  - `SimulationActionHandler.handle_start`: Initializes simulation with optional tick rate and speed parameters. Calculates `dt_s = speed / tick_rate`.
  - `SimulationActionHandler.handle_stop`: Halts simulation execution.
  - `SimulationActionHandler.handle_pause`: Suspends simulation loop while maintaining running state.
  - `SimulationActionHandler.handle_resume`: Continues simulation from paused state.
  - `SimulationActionHandler.handle_update`: Updates simulation configuration (supports tick rate and/or speed). Recalculates `dt_s` when either parameter changes.
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
- Parameter validation: O(1) - type check and bounds clamping in `SimulationState.set_tick_rate` and `set_dt_s`
- DTO creation/conversion: O(1) - fixed field access

## Public API / Usage

### Start Simulation
```python
# With both parameters
handler.handle_start({"tick_rate": 30, "speed": 2.0}, context)
# Calculates: dt_s = 2.0 / 30 = 0.0667
# Emits: {"signal": "simulation.started", "data": {"tick_rate": 30, "speed": 2.0}}

# With tick_rate only
handler.handle_start({"tick_rate": 30}, context)
# Uses current speed (default 1.0), calculates: dt_s = 1.0 / 30 = 0.0333
# Emits: {"signal": "simulation.started", "data": {"tick_rate": 30, "speed": 1.0}}

# With speed only
handler.handle_start({"speed": 2.0}, context)
# Uses current tick_rate (default 20.0), calculates: dt_s = 2.0 / 20.0 = 0.1
# Emits: {"signal": "simulation.started", "data": {"tick_rate": 20, "speed": 2.0}}

# With no parameters (uses defaults)
handler.handle_start({}, context)
# Uses defaults: tick_rate=20.0, speed=1.0, calculates: dt_s = 1.0 / 20.0 = 0.05
# Emits: {"signal": "simulation.started", "data": {"tick_rate": 20, "speed": 1.0}}
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
# Update both parameters
handler.handle_update({"tick_rate": 50, "speed": 2.0}, context)
# Calculates: dt_s = 2.0 / 50 = 0.04
# Emits: {"signal": "simulation.updated", "data": {"tick_rate": 50, "speed": 2.0}}

# Update tick_rate only (recalculates dt_s based on current speed)
handler.handle_update({"tick_rate": 50}, context)
# If current speed is 1.0, calculates: dt_s = 1.0 / 50 = 0.02
# Emits: {"signal": "simulation.updated", "data": {"tick_rate": 50, "speed": 1.0}}

# Update speed only (recalculates dt_s based on current tick_rate)
handler.handle_update({"speed": 2.0}, context)
# If current tick_rate is 20.0, calculates: dt_s = 2.0 / 20.0 = 0.1
# Emits: {"signal": "simulation.updated", "data": {"tick_rate": 20, "speed": 2.0}}
```

## Implementation Notes
- `handle_start` accepts optional `tick_rate` and `speed` parameters; if omitted, uses current state values.
- `handle_update` requires at least one parameter (`tick_rate` or `speed`) and emits confirmation signal with both current values.
- Parameters are validated using `SimulationParamsDTO` for consistent validation logic.
- **Speed and dt_s Calculation**: The `speed` parameter represents simulation seconds per real second. The actual `dt_s` (simulation time step per tick) is calculated as `dt_s = speed / tick_rate`. This ensures that setting `speed=2.0` with `tick_rate=10` results in `dt_s=0.2`, meaning 2 simulation seconds pass per real second.
- When `speed` is set, `dt_s` is automatically recalculated based on the current `tick_rate`.
- When `tick_rate` is set, `dt_s` is automatically recalculated based on the current `speed`.
- Both `context.state.set_speed()` and `context.world.dt_s` are updated to maintain consistency.
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
- Parameter validation prevents invalid tick rate (1-100 Hz) and speed (0.01-10.0s) values
- Type checking via `SimulationParamsDTO` ensures correct parameter types
- Bounds clamping in `SimulationState` provides defense-in-depth validation
- Error handling prevents signal queue failures from corrupting state
- Logging provides audit trail for all state transitions

## References
- [SimulationState](../state.md) - State management
- [Action Registry](../actions/action-registry.md) - Handler registration
- [Queues](../queues.md) - Signal emission helpers
- [Simulation Controller](../controller.md) - Integration point
