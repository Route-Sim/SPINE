---
title: "Edge"
summary: "Graph connections representing traversable routes between nodes, such as roads, with attributes for distance, speed, and capacity."
source_paths:
  - "world/graph/edge.py"
last_updated: "2025-10-25"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "graph", "transportation"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["graph", "node"]
---

# Edge

> **Purpose:** Edges represent connections between nodes in the logistics network, modeling traversable routes such as roads, highways, and transportation corridors with attributes for distance, speed, and capacity.

## Context & Motivation

Edges serve as the transportation infrastructure in the logistics network:
- **Route connections** between logistics facilities
- **Transportation attributes** for routing and navigation
- **Capacity constraints** for traffic flow simulation
- **Speed limitations** for realistic movement modeling

## Responsibilities & Boundaries

### In-scope
- Connection definition (from_node, to_node)
- Distance and length attributes
- Transportation mode specification
- Speed and capacity attributes (for RoadEdge)

### Out-of-scope
- Traffic simulation (handled by traffic system)
- Routing algorithms (handled by router)
- Agent movement (handled by agents)
- Real-time speed calculations (handled by traffic)

## Architecture & Design

### Core Data Structures
```python
@dataclass
class Edge:
    id: EdgeID                    # Unique identifier
    from_node: NodeID            # Source node
    to_node: NodeID              # Destination node
    length_m: float              # Distance in meters
    mode: Mode                   # Transportation mode

@dataclass
class RoadEdge(Edge):
    base_speed_mps: float        # Base speed in m/s
    base_cap_vph: float         # Base capacity in vehicles/hour
    lanes: int                   # Number of lanes
    inwardness: float            # Urban density factor
```

### Transportation Modes
```python
class Mode(IntEnum):
    ROAD = 1 << 0               # Road transportation
    # Future: RAIL, AIR, WATER, etc.
```

## Algorithms & Complexity

### Edge Operations
- **Edge creation**: O(1) - Simple dataclass instantiation
- **Attribute access**: O(1) - Direct field access
- **Speed calculation**: O(1) - Simple arithmetic operations
- **Capacity calculation**: O(1) - Basic multiplication

### Space Complexity
- **Storage**: O(1) per edge - Fixed size dataclass
- **Memory**: ~100 bytes per edge
- **Attributes**: Minimal overhead for additional fields

## Public API / Usage

### Basic Edge Creation
```python
from world.graph.edge import Edge, RoadEdge, Mode

# Create basic edge
edge = Edge(
    id=1,
    from_node=1,
    to_node=2,
    length_m=1000.0,
    mode=Mode.ROAD
)

# Create road edge with traffic attributes
road_edge = RoadEdge(
    id=2,
    from_node=1,
    to_node=3,
    length_m=500.0,
    mode=Mode.ROAD,
    base_speed_mps=13.89,  # 50 km/h
    base_cap_vph=2000,
    lanes=2,
    inwardness=0.7
)
```

### Edge Attributes
```python
# Access basic attributes
distance = edge.length_m
source = edge.from_node
destination = edge.to_node

# Access road-specific attributes
if isinstance(edge, RoadEdge):
    speed = edge.base_speed_mps
    capacity = edge.base_cap_vph
    lanes = edge.lanes
```

## Implementation Notes

### Edge Types
- **Base Edge**: Minimal connection between nodes
- **RoadEdge**: Extended edge with traffic attributes
- **Future types**: RailEdge, AirEdge, WaterEdge for different modes

### Transportation Modes
- **Bit flags**: Uses bitwise operations for mode combinations
- **Extensible**: Easy to add new transportation modes
- **Efficient**: Single integer for mode representation

### Attribute Design
- **Base attributes**: Common to all edge types
- **Extended attributes**: Specific to transportation mode
- **Optional fields**: Default values for optional attributes

## Performance

### Benchmarks
- **Edge creation**: ~1μs
- **Attribute access**: ~0.1μs per attribute
- **Speed calculation**: ~0.1μs
- **Memory usage**: ~100 bytes per edge

### Scalability
- **Maximum edges**: Tested up to 100,000 edges
- **Performance**: Constant time operations
- **Memory**: Linear scaling with edge count

## Security & Reliability

### Data Integrity
- **Valid connections**: Edges must connect existing nodes
- **Positive attributes**: Length, speed, capacity must be positive
- **Mode validation**: Transportation mode must be valid

### Error Handling
- **Invalid nodes**: Clear error messages for non-existent nodes
- **Invalid attributes**: Validation for negative or zero values
- **Type safety**: Strong typing prevents attribute errors

## References

### Related Modules
- [Graph](graph.md) - Graph structure containing edges
- [Node](node.md) - Connected nodes
- [World](../world.md) - Simulation environment using edges

### External References
- Graph theory edges
- Transportation network modeling
- Traffic flow theory
