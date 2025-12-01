---
title: "Occupiable Building Base Class"
summary: "Abstract base class for buildings that can hold agents with capacity limits. Provides common occupancy tracking functionality for Parking, GasStation, and similar facilities."
source_paths:
  - "core/buildings/occupancy.py"
last_updated: "2025-12-01"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "building", "sim", "base-class"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["base.md", "parking.md", "gas-station.md", "site.md"]
---

# Occupiable Building Base Class

> **Purpose:** Provides a shared foundation for buildings that can hold agents up to a capacity limit. This superclass extracts common occupancy tracking functionality from Parking and makes it available to other building types like GasStation.

## Context & Motivation
- Problem solved: avoid code duplication for buildings that need to track which agents are currently inside them.
- Requirements and constraints:
  - Respect declared capacity limits and reject overflows.
  - Provide generic method names (`enter`, `leave`) that can be aliased by subclasses for domain-specific terminology.
  - Maintain compatibility with the existing `Building` serialization framework.
- Dependencies and assumptions:
  - Agent identifiers use the `AgentID` type alias.
  - Subclasses are responsible for adding their own type-specific fields and serialization.

## Responsibilities & Boundaries
- In-scope:
  - Capacity validation at construction time.
  - Set-backed operations for tracking occupants.
  - Generic `enter()`, `leave()`, `has_space()`, and `assign_occupants()` methods.
  - Base serialization helpers with stable ordering of occupants.
- Out-of-scope:
  - Type-specific logic (e.g., fuel pricing for gas stations).
  - Agent behavior that determines when to enter/leave facilities.

## Architecture & Design
- Class: `OccupiableBuilding(Building)` extends the base dataclass with:
  - `capacity: int`
  - `current_agents: set[AgentID]`
  - Methods: `has_space()`, `enter()`, `leave()`, `assign_occupants()`.
- Subclasses (Parking, GasStation) inherit this functionality and may add domain-specific aliases or additional fields.
- State management: occupancy uses a `set[AgentID]` to avoid duplicates.

```python
from core.buildings.occupancy import OccupiableBuilding
from core.types import AgentID, BuildingID

# Direct use (typically through subclasses)
building = OccupiableBuilding(id=BuildingID("facility-1"), capacity=10)
building.enter(AgentID("agent-1"))
assert building.has_space()
building.leave(AgentID("agent-1"))
```

## Algorithms & Complexity
- Occupancy operations (`enter`, `leave`, `has_space`) are `O(1)` on average.
- Serialization sorts occupants (`O(n log n)`) to guarantee deterministic ordering.

## Public API / Usage
- `has_space() -> bool`: Check if additional agents can enter.
- `enter(agent_id: AgentID) -> None`: Register an agent as occupying the facility.
- `leave(agent_id: AgentID) -> None`: Remove an agent from occupancy.
- `assign_occupants(agents: Iterable[AgentID]) -> None`: Replace the occupancy set.
- `to_dict() -> dict[str, Any]`: Serialize with capacity and sorted occupant list.

## Implementation Notes
- Validation ensures capacity is positive and occupancy never exceeds the limit.
- Error messages include the class name dynamically for better debugging.
- Subclasses should call `super().__post_init__()` if they override `__post_init__`.

## Tests
- Capacity validation and overflow rejection.
- Duplicate entry rejection.
- Round-trip serialization through subclasses.

## References
- [Building Base Class](base.md) — core serializer and factory.
- [Parking Building](parking.md) — uses OccupiableBuilding for parking lots.
- [Gas Station Building](gas-station.md) — uses OccupiableBuilding for fuel services.
