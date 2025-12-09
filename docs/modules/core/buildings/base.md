---
title: "Building Base Class"
summary: "Defines the lightweight Building dataclass that anchors identification, serialization, and change tracking for facilities stored on graph nodes."
source_paths:
  - "core/buildings/base.py"
last_updated: "2025-12-09"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "building", "facility", "sim"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["parking.md", "site.md", "gas_station.md"]
---

# Building Base Class

> **Purpose:** Supplies the canonical, minimal representation for physical facilities embedded in the world graph. Includes change tracking via dirty flags for efficient signal emission. Subclasses add behaviour or metadata while reusing the base serialization and diff contracts.

## Context & Motivation
- Problem solved: represent facilities on graph nodes with efficient update tracking.
- Requirements and constraints:
  - Buildings must round-trip through `Graph.to_dict()` / GraphML export.
  - Buildings should only emit update signals when state explicitly changes.
- Type hints must remain stable for downstream subclassing (e.g., Sites, Parking, GasStation).
- Dependencies and assumptions: building IDs map to `BuildingID`; subclasses declare their own metadata while reusing the base serializer.

## Responsibilities & Boundaries
- In-scope:
  - Base building identification and type tagging.
  - Serialization helpers that annotate payloads with building type hints.
  - Change tracking via dirty flag mechanism.
  - Diff serialization for UI update signals.
- Out-of-scope:
  - Behavioural logic (delegated to agent wrappers).

## Architecture & Design
- Core type:
  - `Building`: dataclass with `id: BuildingID` and `TYPE="building"`. Adds `to_dict`/`from_dict` helpers emitting `{"id": "...", "type": "building"}` payloads.
- Change tracking:
  - `_dirty: bool` flag tracks whether building state has changed since last serialization.
  - `mark_dirty()` / `is_dirty()` / `clear_dirty()` methods for explicit state management.
  - `serialize_diff()` returns full state if dirty, `None` otherwise.
- Type dispatch:
  - `Building.from_dict` inspects the `"type"` field and lazily imports known subclasses (e.g., Parking) to rebuild specialised instances.
- Resource handling: purely in-memory; no external handles.

```python
from core.buildings.base import Building
from core.buildings.parking import Parking
from core.types import BuildingID, AgentID

# Basic building serialization
warehouse = Building(id=BuildingID("warehouse-1"))
payload = warehouse.to_dict()
# {'id': 'warehouse-1', 'type': 'building'}

# Change tracking example
parking = Parking(id=BuildingID("park-1"), capacity=5)
print(parking.is_dirty())  # False

parking.enter(AgentID("truck-1"))
print(parking.is_dirty())  # True

diff = parking.serialize_diff()  # Returns full state, clears dirty
print(parking.is_dirty())  # False
print(parking.serialize_diff())  # None (no changes)
```

## Algorithms & Complexity
- Serialization is `O(1)` for basic buildings.
- Type dispatch costs `O(1)` assuming finite subclass catalogue.
- Dirty tracking is `O(1)` flag check/set.

## Public API / Usage
- `Building.to_dict()` / `Building.from_dict()` round-trip basic facilities.
- `Building.serialize_full()` returns complete state for snapshots.
- `Building.serialize_diff()` returns full state if dirty, `None` otherwise.
- `Building.mark_dirty()` / `is_dirty()` / `clear_dirty()` for explicit change tracking.

## Implementation Notes
- Type tagging: all payloads now include a `"type"` attribute so GraphML import can rehydrate specialized buildings.
- `Building.from_dict` uses lazy imports to avoid circular dependencies with subclasses module layouts.
- Internal tracking fields (`_dirty`, `_last_serialized_state`) are excluded from serialization.
- Buildings emit `building.updated` signals only when dirty, unlike agents which update every tick.

## Tests
- Round-trip serialization of base buildings through dict payloads.
- Dirty flag tracking and diff serialization.
- Integration coverage through `Graph.to_dict()` and generator placement tests.

## References
- Related modules:
  - [Parking Building](parking.md) for capacity-constrained staging areas.
  - [Site Building](site.md) for package-generating facilities.
  - [Gas Station Building](gas_station.md) for fuel services.
  - [World Generator](../../world/generation/generator.md) for automatic parking placement.
  - [Queues](../../world/sim/queues.md) for `building.updated` signal.
