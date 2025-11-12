---
title: "Building Base Class"
summary: "Defines the lightweight Building dataclass that anchors identification and serialization for facilities stored on graph nodes."
source_paths:
  - "core/buildings/base.py"
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "building", "facility", "sim"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["parking.md", "site.md"]
---

# Building Base Class

> **Purpose:** Supplies the canonical, minimal representation for physical facilities embedded in the world graph. Subclasses add behaviour or metadata while reusing the base serialization contract.

## Context & Motivation
- Problem solved: represent facilities on graph nodes without forcing agent behaviour.
- Requirements and constraints:
  - Buildings must round-trip through `Graph.to_dict()` / GraphML export.
- Type hints must remain stable for downstream subclassing (e.g., Sites, Parking).
- Dependencies and assumptions: building IDs map to `BuildingID`; subclasses declare their own metadata while reusing the base serializer.

## Responsibilities & Boundaries
- In-scope:
  - Base building identification and type tagging.
  - Serialization helpers that annotate payloads with building type hints.
- Out-of-scope:
  - Behavioural logic (delegated to agent wrappers).

## Architecture & Design
- Core type:
  - `Building`: dataclass with `id: BuildingID` and `TYPE="building"`. Adds `to_dict`/`from_dict` helpers emitting `{"id": "...", "type": "building"}` payloads.
- Type dispatch:
  - `Building.from_dict` inspects the `"type"` field and lazily imports known subclasses (e.g., Parking) to rebuild specialised instances.
- Resource handling: purely in-memory; no external handles.

```python
from core.buildings.base import Building
from core.types import BuildingID

warehouse = Building(id=BuildingID("warehouse-1"))
payload = warehouse.to_dict()
# {'id': 'warehouse-1', 'type': 'building'}
```

## Algorithms & Complexity
- Serialization is `O(1)` for basic buildings.
- Type dispatch costs `O(1)` assuming finite subclass catalogue.

## Public API / Usage
- `Building.to_dict()` / `Building.from_dict()` round-trip basic facilities; the dispatcher in `from_dict` instantiates `Parking` when `type == "parking"`.

## Implementation Notes
- Type tagging: all payloads now include a `"type"` attribute so GraphML import can rehydrate specialized buildings.
- `Building.from_dict` uses lazy imports to avoid circular dependencies with subclasses module layouts.

## Tests
- Round-trip serialization of base buildings through dict payloads.
- Integration coverage through `Graph.to_dict()` and generator placement tests (see `docs/modules/world/generation/generator.md`).

## References
- Related modules:
  - [Parking Building](parking.md) for capacity-constrained staging areas.
  - [Site Building](site.md) for package-generating facilities.
  - [World Generator](../../world/generation/generator.md) for automatic parking placement.
