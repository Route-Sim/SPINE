---
title: "BuildingAgent"
summary: "Agent wrapper that combines Building data structure with agent capabilities for active participation in the simulation."
source_paths:
  - "agents/buildings/building_agent.py"
last_updated: "2025-10-26"
owner: "Mateusz Polis"
tags: ["module", "agent", "building", "wrapper"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["base", "transports/base"]
---

# BuildingAgent

> **Purpose:** BuildingAgent is an agent wrapper that combines a Building data structure with AgentBase functionality, allowing buildings to participate in the simulation as active agents while maintaining separation between data and behavior.

## Context & Motivation

BuildingAgent provides the bridge between building data and agent functionality:
- **Wraps Building** with agent capabilities (messages, behavior)
- **Separates concerns** between data (Building) and behavior (Agent)
- **Enables agent features** (perceive, decide, serialize_diff)
- **Maintains compatibility** with existing agent system

This wrapper pattern allows buildings to exist as passive data in the graph (stored in nodes) or as active agents in the simulation, depending on requirements.

## Responsibilities & Boundaries

### In-scope
- Agent lifecycle management
- Message handling (inbox/outbox)
- Building data storage and access
- Agent state serialization

### Out-of-scope
- Building data structure (handled by Building class)
- Graph storage (handled by Node)
- Export/import (handled by GraphML)

## Architecture & Design

### Wrapper Pattern
```python
@dataclass
class BuildingAgent(AgentBase):
    building: Building  # Pure data structure

    def __post_init__(self) -> None:
        """Initialize with building data."""
        self.id = self.building.id
        self.kind = self.kind or "building"
```

The BuildingAgent holds a reference to a Building instance and delegates identification to it. This allows the building data to exist independently in the graph while the agent wrapper adds simulation capabilities.

## Public API / Usage

### Creating BuildingAgent
```python
from agents.buildings.building_agent import BuildingAgent
from core.buildings.base import Building
from core.types import AgentID, BuildingID

# Create building data (uses BuildingID, not AgentID)
building = Building(id=BuildingID("warehouse1"))

# Create agent wrapper (BuildingID is converted to AgentID)
agent = BuildingAgent(
    building=building,
    id=AgentID("warehouse1"),
    kind="building"
)

# Add to world
world.add_agent(AgentID("warehouse1"), agent)
```

### Accessing Building Data
```python
# Access building from agent
building_data = agent.building

# Building data is separate from agent state
building_id = agent.building.id
```

## Implementation Notes

### Initialization
- Building ID is used as agent ID by default
- Agent kind defaults to "building" if not specified
- Building data is stored as instance variable

### Agent Methods
- `perceive(world)`: Optional perception (empty by default)
- `decide(world)`: Decision logic (empty by default, to be implemented)
- `serialize_diff()`: Inherited from AgentBase

### Integration with Graph
Buildings in the graph (stored in nodes) can be separate from BuildingAgent instances. When a building needs to become an agent, a BuildingAgent wrapper is created and registered with the world.

## Tests

### Coverage
- Agent creation with building data
- Building data access from agent
- Integration with World

## References

### Related Modules
- [Building](../../core/buildings/base.md) - Building data structure
- [AgentBase](../base.md) - Base agent interface
- [World](../../world/world.md) - Simulation environment
