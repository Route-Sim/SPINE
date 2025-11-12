---
title: "Parking Building"
summary: "Captures capacity-limited parking facilities that track staged trucks and round-trip through graph serialization."
source_paths:
  - "core/buildings/parking.py"
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "building", "sim"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["base.md", "site.md"]
---

# Parking Building

> **Purpose:** Represents dedicated parking facilities on graph nodes with explicit capacity and occupancy tracking. These buildings provide staging areas for transport agents without requiring agent behaviour.

## Context & Motivation
- Problem solved: model heavy-vehicle parking lots attached to road nodes.
- Requirements and constraints:
  - Respect declared capacity limits and reject overflows.
  - Provide deterministic serialization for map exports and WebSocket responses.
  - Remain interoperable with the base `Building` factory (`Building.from_dict`).
- Dependencies and assumptions:
  - Parked truck identifiers use the `AgentID` alias.
  - The world generator and runtime handlers create empty parkings; occupancy is managed by future routing logic.

## Responsibilities & Boundaries
- In-scope:
  - Capacity validation at construction time.
  - Simple set-backed operations for tracking parked agents.
  - Serialization helpers with stable ordering of occupants.
- Out-of-scope:
  - Movement logic that sends trucks to or from parking (handled by agents/controllers).
  - Persistence beyond the in-memory graph.

## Architecture & Design
- Class: `Parking(Building)` extends the base dataclass with:
  - `capacity: int`
  - `current_agents: set[AgentID]`
  - Convenience methods `has_space()`, `park()`, `release()`, `assign_occupants()`.
- Data flow:
  - Generator attaches `Parking` instances when road heuristics recommend rest areas.
  - `building.create` actions provision additional slots at runtime; occupancy starts empty.
- State management: occupancy uses a `set[AgentID]` to avoid duplicates; serialization sorts occupants for deterministic payloads.

```python
from core.buildings.parking import Parking
from core.types import AgentID, BuildingID

parking = Parking(id=BuildingID("parking-node42"), capacity=40)
parking.park(AgentID("truck-99"))
payload = parking.to_dict()
# {'id': 'parking-node42', 'type': 'parking', 'capacity': 40, 'current_agents': ['truck-99']}
```

## Algorithms & Complexity
- Parking operations (`park`, `release`, `has_space`) are `O(1)` on average.
- Serialization sorts occupants (`O(n log n)`) to guarantee deterministic ordering where `n` equals the number of parked agents.

## Public API / Usage
- Instantiate via constructor or `Parking.from_dict`.
- Use `park`/`release` for incremental updates; `assign_occupants` replaces the occupancy set after validation.
- When serialized, payloads include `"type": "parking"` so `Building.from_dict` can reconstruct instances.

## Implementation Notes
- Validation ensures capacity is positive and occupancy never exceeds the limit.
- `assign_occupants` coerces incoming iterables to `AgentID`.
- The module intentionally avoids agent behaviour; future integrations may pair parkings with orchestration logic that places trucks in these facilities.

## Tests
- Round-trip serialization through `Parking.to_dict()` / `Parking.from_dict()`.
- Capacity validation and duplicate parking rejection.
- Integration via world generation and WebSocket action handler tests.

## References
- [Building Base Class](base.md) — core serializer and factory.
- [World Generator](../../world/generation/generator.md) — automatic parking placement.
- [Building Action Handler](../../world/sim/handlers/building.md) — runtime provisioning via `building.create`.
