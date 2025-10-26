---
title: "Building"
summary: "Base data structure representing physical facilities in the logistics network, stored as data separate from agent functionality."
source_paths:
  - "core/buildings/base.py"
last_updated: "2025-10-26"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "building", "facility"]
links:
  parent: "../../SUMMARY.md"
  siblings: []
---

# Building

> **Purpose:** Building represents a physical facility in the logistics network as a pure data structure. It contains building-specific information but does not inherit agent capabilities. Buildings can be stored in nodes and serialized to GraphML format.

## Context & Motivation

Building serves as the base data structure for physical facilities:
- **Pure data structure** without agent behavior
- **Graph storage** as part of node data in the logistics network
- **Serialization** for GraphML export/import
- **Extension point** for specialized building types (warehouses, depots, etc.)

Unlike the old Building class that inherited from AgentBase, the new Building is focused solely on data representation. This separation allows buildings to exist in the graph without necessarily being active agents in the simulation.

## Responsibilities & Boundaries

### In-scope
- Building identification (unique ID)
- Data serialization (to_dict/from_dict)
- Future building-specific attributes (capacity, type, etc.)

### Out-of-scope
- Agent behavior (handled by BuildingAgent wrapper)
- Message handling (handled by agent system)
- Simulation logic (handled by agents and world)

## Architecture & Design

### Core Data Structure
```python
@dataclass
class Building:
    id: BuildingID  # Unique identifier

    def to_dict(self) -> dict[str, Any]:
        """Serialize building to dictionary."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Building":
        """Deserialize building from dictionary."""
```

### Agent Wrapper Pattern
When a Building needs to act as an agent in the simulation, it can be wrapped by BuildingAgent:

```python
from agents.buildings.building_agent import BuildingAgent
from core.buildings.base import Building
from core.types import BuildingID, AgentID

# Create building data
building = Building(id=BuildingID("warehouse1"))

# Wrap as agent when needed (BuildingID is converted to AgentID automatically)
agent = BuildingAgent(building=building, id=AgentID("warehouse1"), kind="building")
```

## Public API / Usage

### Building Creation
```python
from core.buildings.base import Building
from core.types import BuildingID

# Create building
warehouse = Building(id=BuildingID("warehouse1"))

# Serialize to dictionary
data = warehouse.to_dict()

# Deserialize from dictionary
restored = Building.from_dict(data)
```

### Storing in Graph Nodes
```python
from world.graph.node import Node
from core.types import BuildingID, NodeID

# Add building to node
node = Node(id=NodeID(1), x=10.0, y=20.0)
building = Building(id=BuildingID("b1"))
node.add_building(building)

# Buildings are automatically serialized when exporting to GraphML
graph.to_graphml("graph.graphml")
```

## Implementation Notes

### Serialization
- Uses Python's `dataclasses.asdict()` for serialization
- JSON-safe for GraphML storage
- Extensible for future attributes

### GraphML Integration
- Buildings are stored as JSON strings in node attributes
- Automatically serialized/deserialized during export/import
- Preserves all building data without agent-specific fields

### Future Extensions
Subclasses can be created for specific building types:
- `Warehouse` in `core/buildings/warehouse.py`
- `Depot` in `core/buildings/depot.py`
- etc.

Each can add specific attributes while maintaining serialization compatibility.

## Tests

### Coverage
- Building creation and serialization
- GraphML export/import with buildings
- Round-trip serialization (to_dict/from_dict)

## References

### Related Modules
- [BuildingAgent](../agents/buildings/building-agent.md) - Agent wrapper for Building
- [Node](../../world/graph/node.md) - Container for buildings in graph
- [Graph GraphML](../../world/graph/graph.md#graphml-export-import) - Export/import functionality
