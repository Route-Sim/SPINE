---
title: "SimulationParamsDTO"
summary: "Data Transfer Object for simulation control parameters (tick_rate and speed) used in actions and responses. Speed represents simulation seconds per real second, with dt_s calculated as speed / tick_rate."
source_paths:
  - "world/sim/dto/simulation_dto.py"
last_updated: "2025-01-27"
owner: "Mateusz Polis"
tags: ["module", "dto", "sim"]
links:
  parent: "../../../../SUMMARY.md"
  siblings: ["agent-dto.md", "truck-dto.md", "statistics-dto.md"]
---

# SimulationParamsDTO

> **Purpose:** Provides a validated, typed data transfer object for simulation control parameters (tick_rate and speed) used in both incoming actions and outgoing signal responses. Ensures consistent parameter handling across the simulation control API.

## Context & Motivation

Before introducing this DTO, simulation control parameters were handled as loosely-typed dictionaries, leading to:
- Inconsistent validation logic scattered across handlers
- Unclear contracts between clients and the simulation server
- Potential type errors and invalid parameter values

The `SimulationParamsDTO` centralizes validation and provides a single source of truth for simulation parameter constraints.

## Responsibilities & Boundaries

### In-scope
- Validating tick_rate (ticks per second, 1-100 Hz)
- Validating speed (simulation time step dt_s, 0.01-10.0 seconds per tick)
- Converting between DTO and dictionary representations
- Allowing optional parameters (both can be None)

### Out-of-scope
- Applying parameters to simulation state (handled by `SimulationActionHandler`)
- Managing simulation lifecycle (handled by `SimulationState`)
- Real-time parameter enforcement during simulation execution

## Architecture & Design

### Class Structure

```python
class SimulationParamsDTO(BaseModel):
    tick_rate: int | None = Field(default=None, ge=1, le=100)
    speed: float | None = Field(default=None, gt=0.0, le=10.0)
```

### Key Fields

1. **tick_rate**: Optional integer (1-100)
   - Represents how often the simulation computes (ticks per second)
   - Higher values = faster computation updates
   - Clamped to prevent performance issues

2. **speed**: Optional float (0.01-10.0)
   - Represents simulation seconds per real second
   - Controls how much simulated time passes per real second
   - Default: 1.0 (1 simulation second per real second)
   - The actual `dt_s` (simulation time step per tick) is calculated as `dt_s = speed / tick_rate`
   - Example: `speed=2.0` with `tick_rate=10` results in `dt_s=0.2`, meaning 2 simulation seconds pass per real second
   - Higher values = faster simulation time progression relative to real time

### Data Flow

```
Client Action → SimulationParamsDTO.from_dict()
              ↓
         Validation
              ↓
    SimulationActionHandler
              ↓
    SimulationState.set_tick_rate() / set_speed()
              ↓
    dt_s calculation: dt_s = speed / tick_rate
              ↓
    World.dt_s update
              ↓
    Response Signal ← SimulationParamsDTO.to_dict()
```

## Algorithms & Complexity

### Validation

- **Field validators**: O(1) range checks
- **from_dict**: O(1) dictionary access and construction
- **to_dict**: O(1) dictionary construction excluding None values

All operations are constant time.

## Public API / Usage

### Creating DTOs

```python
# Both parameters
dto = SimulationParamsDTO(tick_rate=30, speed=1.0)

# Single parameter
dto = SimulationParamsDTO(tick_rate=50)
dto = SimulationParamsDTO(speed=0.1)

# From dictionary (typical for incoming actions)
dto = SimulationParamsDTO.from_dict({"tick_rate": 25, "speed": 0.08})
```

### Converting to Dictionary

```python
dto = SimulationParamsDTO(tick_rate=40, speed=0.15)
data = dto.to_dict()  # {"tick_rate": 40, "speed": 0.15}

# None values are excluded
dto = SimulationParamsDTO(tick_rate=20)
data = dto.to_dict()  # {"tick_rate": 20}
```

### Validation Errors

```python
from pydantic import ValidationError

# Out of range tick_rate
try:
    SimulationParamsDTO(tick_rate=0)
except ValidationError:
    # "tick_rate must be between 1 and 100"
    pass

# Out of range speed
try:
    SimulationParamsDTO(speed=0.0)
except ValidationError:
    # "speed must be between 0.01 and 10.0"
    pass
```

## Implementation Notes

### Design Trade-offs

1. **Optional Fields**: Both parameters are optional to support partial updates
   - Allows clients to update only tick_rate or only speed
   - Requires handler-level validation that at least one is provided for update actions

2. **Range Constraints**:
   - `tick_rate`: 1-100 Hz balances responsiveness vs server load
   - `speed`: 0.01-10.0 allows both slow-motion (0.01) and fast-forward (10.0) simulation relative to real time

3. **Speed vs dt_s Relationship**:
   - `speed` represents simulation seconds per real second (intuitive for users)
   - `dt_s` is automatically calculated as `speed / tick_rate` (internal simulation parameter)
   - This separation allows independent control of simulation speed and computation frequency
   - Example: `speed=2.0, tick_rate=20` → `dt_s=0.1` means 2 simulation seconds pass per real second at 20 ticks/second

3. **Pydantic v2**: Uses modern Pydantic patterns:
   - `Field()` for constraints
   - `@field_validator` decorator
   - `model_validate` / `model_dump` (though custom to_dict/from_dict used for clarity)

### Third-party Libraries

- **pydantic**: Runtime type validation and serialization

## Tests

Test coverage in `tests/world/sim/dto/test_simulation_dto.py`:

- DTO creation with all parameter combinations
- Validation of tick_rate and speed ranges
- to_dict() excluding None values
- from_dict() with partial data
- Boundary value testing

## Performance

- DTO creation and validation: < 1ms
- Negligible overhead compared to simulation step execution
- No performance concerns for typical usage patterns

## Security & Reliability

### Validation
- Prevents invalid tick rates that could cause performance issues
- Prevents invalid speed values that could break simulation physics
- Type safety via Pydantic ensures runtime correctness

### Error Handling
- Clear validation error messages for client debugging
- Fails fast on invalid input before simulation state changes

## References

- **Related modules**:
  - `world.sim.handlers.simulation` - Uses DTO for action handling
  - `world.sim.queues` - Uses DTO for signal creation
  - `world.sim.state` - Target for parameter application
- **ADRs**: N/A
- **API Reference**: See `docs/api-reference.md` for action/signal schemas
