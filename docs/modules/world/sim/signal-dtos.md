---
title: "Signal Data Transfer Objects (DTOs)"
summary: "Type-safe Pydantic DTOs for signal data structures to prevent inconsistencies and enable compile-time validation"
source_paths:
  - "world/sim/signal_dtos/"
  - "world/sim/signal_dtos/base.py"
  - "world/sim/signal_dtos/map_created.py"
last_updated: "2025-11-16"
owner: "Mateusz Polis"
tags: ["module", "api", "signal", "dto", "validation"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["queues.md"]
---

# Signal Data Transfer Objects (DTOs)

> **Purpose:** Provide type-safe Pydantic-based DTOs for signal data structures to ensure consistency, enable compile-time type checking via mypy, and provide runtime validation.

## Context & Motivation

### The Problem

Signals in the SPINE system are emitted from the backend to the frontend to communicate state changes and events. Originally, signal data was untyped, using `dict[str, Any]` throughout the codebase. This led to several issues:

1. **Inconsistencies:** Different parts of the codebase created the same signal with different data structures
2. **Runtime Errors:** Missing or incorrectly typed fields were only discovered at runtime
3. **Poor Documentation:** Signal structure was implicit and undocumented
4. **Difficult Refactoring:** Changing signal structure required manual searching through the codebase

#### Real-World Example

The `map.created` signal was emitted in two places:
- `world/sim/handlers/map.py`: Included 20+ generation parameters plus graph data
- `world/io/websocket_server.py`: Only included graph data

This inconsistency meant frontend clients received different data depending on how they connected.

### The Solution

Introduce Pydantic-based DTOs that:
- Provide **compile-time type checking** via mypy --strict
- Enable **runtime validation** via Pydantic
- **Self-document** signal structures with field descriptions
- Allow **incremental migration** from untyped dicts

## Responsibilities & Boundaries

### In-Scope
- Define typed DTOs for signal data structures
- Validate signal data at creation time
- Convert DTOs to dictionaries for JSON serialization
- Provide clear field documentation and constraints

### Out-of-Scope
- Signal routing or queue management (see `queues.md`)
- Signal serialization to JSON (handled by Signal class)
- Action DTOs (actions use a different validation pattern)

## Architecture & Design

### Directory Structure

```
world/sim/signal_dtos/
  ├── __init__.py          # Exports all DTOs
  ├── base.py              # SignalData abstract base class
  ├── map_created.py       # MapCreatedSignalData DTO
  └── [future DTOs]        # Each DTO in its own module
```

### Class Hierarchy

```
SignalData (abstract base in base.py)
  ├─ MapCreatedSignalData (in map_created.py)
  └─ [Future DTOs added incrementally in separate modules]
```

### Core Components

#### 1. SignalData Base Class (signal_dtos/base.py)

```python
class SignalData(BaseModel, ABC):
    """Abstract base for all signal data DTOs."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert DTO to dictionary for signal emission."""
        return self.model_dump()
```

All signal DTOs inherit from this base class, which:
- Extends Pydantic's `BaseModel` for validation
- Marks as abstract via `ABC` to enforce inheritance
- Configures validation behavior using Pydantic v2 ConfigDict
- Provides `to_dict()` method for serialization

#### 2. Concrete DTO Classes (separate modules)

Each signal type that benefits from type safety gets its own DTO class in a separate module:

**signal_dtos/map_created.py:**
```python
from .base import SignalData

class MapCreatedSignalData(SignalData):
    """DTO for map.created signal data."""

    map_width: float = Field(gt=0, description="Map width in kilometers")
    map_height: float = Field(gt=0, description="Map height in kilometers")
    # ... 20+ more fields
```

This modular approach:
- Keeps each DTO focused and maintainable
- Enables lazy imports for better performance
- Makes the codebase easier to navigate
- Allows DTOs to grow independently

DTOs use Pydantic's `Field` to specify:
- **Type annotations:** Compile-time checking via mypy
- **Constraints:** Runtime validation (gt, ge, le, min_length, etc.)
- **Documentation:** Field descriptions for auto-generated docs

#### 3. Custom Validators

Complex validation logic uses `@field_validator`:

```python
@field_validator("urban_activity_rate_range", "rural_activity_rate_range")
@classmethod
def validate_activity_range(cls, v: list[float]) -> list[float]:
    if v[0] > v[1]:
        raise ValueError("Activity rate min must be <= max")
    return v
```

### Integration with Signal System

The `Signal` class in `queues.py` was updated to accept DTOs:

```python
class Signal(BaseModel):
    signal: str
    data: "dict[str, Any] | SignalData"  # Union type for backward compatibility

    def model_dump(self, **_kwargs: Any) -> dict[str, Any]:
        """Converts SignalData DTOs to dicts for serialization."""
        if isinstance(self.data, SignalData):
            data_dict = self.data.to_dict()
        else:
            data_dict = self.data
        return {"signal": self.signal, "data": data_dict}
```

Factory functions require DTOs (no backward compatibility):

```python
def create_map_created_signal(data: "MapCreatedSignalData") -> Signal:
    """Create map.created signal from DTO."""
    return Signal(signal="map.created", data=data)
```

**Design Decision:** Backward compatibility was intentionally removed. When adopting DTOs, all call sites must be updated to ensure consistency across the codebase. This prevents mixed usage that could reintroduce bugs.

## Data Flow

### Signal Creation Flow

1. **Handler creates DTO:**
   ```python
   signal_data = MapCreatedSignalData(
       map_width=100.0,
       map_height=100.0,
       # ... all required fields
   )
   ```
   - Pydantic validates all fields
   - Raises `ValidationError` if invalid

2. **Handler creates signal:**
   ```python
   signal = create_map_created_signal(signal_data)
   ```
   - Factory function accepts DTO
   - Wraps in Signal object

3. **Signal serialization:**
   ```python
   signal_dict = signal.model_dump()
   ```
   - Converts DTO to dict
   - Ready for JSON serialization

### Type Safety at Compile Time

With mypy --strict enabled:

```python
# ✅ Type-safe: mypy validates all fields
signal_data = MapCreatedSignalData(
    map_width=100.0,
    map_height=100.0,
    # ...
)

# ❌ Mypy error: missing required field 'map_width'
signal_data = MapCreatedSignalData(
    map_height=100.0,
    # ...
)

# ❌ Mypy error: wrong type (expecting float, got str)
signal_data = MapCreatedSignalData(
    map_width="100",
    # ...
)
```

### Validation at Runtime

Pydantic validates constraints at runtime:

```python
# ❌ ValidationError: map_width must be > 0
signal_data = MapCreatedSignalData(
    map_width=-10.0,
    # ...
)

# ❌ ValidationError: activity range must have 2 values
signal_data = MapCreatedSignalData(
    urban_activity_rate_range=[0.5],
    # ...
)
```

## Implementation Notes

### Module Organization

Each DTO lives in its own module within the `signal_dtos/` package:

1. **base.py:** Contains only the `SignalData` abstract base class
2. **map_created.py:** Contains only `MapCreatedSignalData`
3. **[future].py:** Each new DTO gets its own module
4. **__init__.py:** Exports all DTOs for convenient imports

**Benefits:**
- Clear separation of concerns
- Easier code navigation
- Reduced merge conflicts when multiple DTOs are added in parallel
- Better IDE autocomplete and type hints
- Lazy loading potential for large codebases

### When to Create a New DTO

**Create a DTO when:**
- Signal has 5+ fields
- Signal is emitted from multiple locations
- Signal has complex validation requirements
- Signal is part of the public API contract
- You want compile-time type safety for the signal

**Continue using dict for:**
- Simple signals (1-2 fields)
- Signals emitted from a single location with no validation needs
- Temporary/experimental signals (but migrate to DTO before production)

### Adding New DTOs

To add a DTO for a new signal:

1. **Create a new module in `signal_dtos/`:**
   ```bash
   touch world/sim/signal_dtos/agent_created.py
   ```

2. **Define the DTO class in that module:**
   ```python
   # world/sim/signal_dtos/agent_created.py
   from pydantic import Field
   from .base import SignalData

   class AgentCreatedSignalData(SignalData):
       """DTO for agent.created signal."""

       agent_id: str = Field(description="Unique agent identifier")
       agent_kind: str = Field(description="Agent type")
       position: tuple[float, float] = Field(description="Agent position")
       # ... other fields
   ```

3. **Export from `__init__.py`:**
   ```python
   # world/sim/signal_dtos/__init__.py
   from .base import SignalData
   from .map_created import MapCreatedSignalData
   from .agent_created import AgentCreatedSignalData  # Add this

   __all__ = ["SignalData", "MapCreatedSignalData", "AgentCreatedSignalData"]
   ```

4. **Update factory function (accept only DTO):**
   ```python
   def create_agent_created_signal(data: "AgentCreatedSignalData") -> Signal:
       return Signal(signal="agent.created", data=data)
   ```

5. **Update ALL call sites:**
   ```python
   from world.sim.signal_dtos.agent_created import AgentCreatedSignalData

   signal_data = AgentCreatedSignalData(
       agent_id=agent.id,
       agent_kind=agent.kind,
       position=agent.position,
   )
   emit_signal(create_agent_created_signal(signal_data))
   ```

6. **Mypy will catch any inconsistencies** across the codebase

## Algorithms & Complexity

### DTO Validation

- **Time Complexity:** O(n) where n = number of fields
- **Space Complexity:** O(1) additional space
- Validation happens once at DTO creation
- Negligible performance impact compared to I/O

### Dict Conversion

- **Time Complexity:** O(n) where n = number of fields
- **Space Complexity:** O(n) for dict copy
- Performed once before JSON serialization

## Public API / Usage

### Creating a DTO

```python
from world.sim.signal_dtos.map_created import MapCreatedSignalData

# Create with all required fields
signal_data = MapCreatedSignalData(
    map_width=100.0,
    map_height=100.0,
    num_major_centers=3,
    # ... 20+ more fields
)

# Access fields
print(signal_data.map_width)  # 100.0

# Convert to dict (for serialization)
data_dict = signal_data.to_dict()

# Alternative: import from package root
from world.sim.signal_dtos import MapCreatedSignalData
```

### Using with Signals

```python
from world.sim.queues import create_map_created_signal

# Create signal with DTO
signal = create_map_created_signal(signal_data)

# Emit signal
signal_queue.put(signal)
```

### Validation Errors

```python
from pydantic import ValidationError

try:
    signal_data = MapCreatedSignalData(
        map_width=-10.0,  # Invalid: must be > 0
        # ... other fields
    )
except ValidationError as e:
    print(e.errors())
    # [{'loc': ('map_width',), 'msg': 'Input should be greater than 0', ...}]
```

## Tests

DTO validation is tested through:

1. **Unit tests:** Test DTO creation and validation
2. **Integration tests:** Test signal emission with DTOs
3. **Mypy:** Static type checking in CI/CD

Example test:

```python
def test_map_created_signal_data_validation():
    """Test MapCreatedSignalData validates constraints."""
    with pytest.raises(ValidationError) as exc_info:
        MapCreatedSignalData(
            map_width=-10.0,  # Invalid
            # ... other fields
        )
    errors = exc_info.value.errors()
    assert any(err['loc'] == ('map_width',) for err in errors)
```

## Performance

### Validation Overhead

Pydantic validation adds minimal overhead:
- ~10-50 microseconds per DTO creation
- Negligible compared to network I/O (~1-100 milliseconds)
- One-time cost at signal creation

### Memory Usage

- DTOs have similar memory footprint to dicts
- Slightly higher due to Pydantic metadata
- Insignificant for typical signal volumes (<1000/sec)

## Security & Reliability

### Input Validation

DTOs provide defense-in-depth:
- **First Layer:** API parameter validation (existing)
- **Second Layer:** DTO validation at signal creation (new)
- **Third Layer:** JSON schema validation at frontend (existing)

### Error Handling

Validation errors are caught early:
```python
try:
    signal_data = MapCreatedSignalData(...)
except ValidationError as e:
    logger.error(f"Invalid signal data: {e}")
    # Handle gracefully without emitting invalid signal
```

This prevents:
- Invalid data reaching frontend
- Silent failures from missing fields
- Type errors in downstream code

## References

### Related Modules
- [queues.md](queues.md) - Signal and action queue infrastructure
- [handlers/map.md](handlers/map.md) - Map action handler using MapCreatedSignalData

### External Documentation
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [Mypy Type Checking](https://mypy.readthedocs.io/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)

### Design Decisions
- Incremental migration strategy chosen for minimal disruption
- Union types used for backward compatibility
- Abstract base class enforces consistent DTO structure
- Field descriptions enable auto-generated API documentation
