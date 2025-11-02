---
title: "Hierarchical Procedural Map Generation"
summary: "Advanced hierarchical generation of realistic road networks with Polish road classification system, featuring major/minor centers, intra-city roads, inter-city highways, and optional ring roads."
source_paths:
  - "world/generation/generator.py"
last_updated: "2025-11-02"
owner: "Mateusz Polis"
tags: ["module", "algorithm", "generation", "procedural", "network", "hierarchical"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["world", "graph/graph"]
---

# Hierarchical Procedural Map Generation

> **Purpose:** Generates realistic, hierarchical road network maps using advanced algorithms that simulate real-world urban planning patterns, complete with Polish road classification, speed limits, lane counts, and weight restrictions.

## Context & Motivation

The Hierarchical Map Generation module provides a sophisticated approach to creating simulation environments that mirror real-world transportation networks. This is essential for:

- **Realistic simulations** with proper road hierarchies (motorways, expressways, local roads)
- **Urban planning research** with configurable city layouts and densities
- **Logistics optimization** testing with realistic road constraints
- **Scalability testing** across various map sizes and complexities
- **Reproducible experiments** with seed-based generation

The system uses a multi-stage hierarchical approach inspired by real urban planning principles, ensuring natural-looking networks with proper connectivity and realistic road characteristics.

## Responsibilities & Boundaries

### In-scope

- Hierarchical center generation (major cities and minor towns)
- Node placement using Poisson disk sampling with configurable density
- Intra-city road networks using Delaunay triangulation and Gabriel graphs
- Inter-city highway systems with k-nearest neighbor connectivity
- Ring roads around major centers
- Polish road classification (A, S, GP, G, Z, L, D)
- Lane assignment, speed limits, and weight restrictions
- Rural settlements and waypoint generation
- Grid-like vs organic street patterns (gridness parameter)
- Connectivity enforcement and cleanup

### Out-of-scope

- Routing algorithms (handled by router module)
- Traffic simulation (handled by simulation module)
- Building placement (future enhancement)
- Terrain elevation (future enhancement)
- Public transport networks (future enhancement)

## Architecture & Design

### Core Components

#### GenerationParams

```python
@dataclass
class GenerationParams:
    map_width: float              # Map dimensions in meters
    map_height: float
    num_major_centers: int        # Number of large cities
    minor_per_major: float        # Avg minor towns per major city
    center_separation: float      # Min distance between major centers (m)
    urban_sprawl: float           # Typical city radius (m)
    local_density: float          # Nodes per km² inside cities
    rural_density: float          # Nodes per km² outside cities
    intra_connectivity: float     # 0-1: edge density within cities
    inter_connectivity: int       # k-nearest for highway network
    arterial_ratio: float         # 0-1: share of arterial roads
    gridness: float               # 0-1: organic vs grid-like streets
    ring_road_prob: float         # Probability of ring roads
    highway_curviness: float      # 0-1: straight vs curved highways
    rural_settlement_prob: float  # Probability of rural settlements
    seed: int                     # Random seed for reproducibility
```

#### MapGenerator

The main generator class that orchestrates the hierarchical generation process.

### Generation Pipeline

The generation follows a seven-step hierarchical approach:

#### Step 0: Generate Centers

- **Major centers**: Placed using Poisson disk sampling with `center_separation` as minimum distance
- **Minor centers**: Distributed around each major center using Poisson distribution
  - Average count per major: `minor_per_major`
  - Placed in a ring at distance ~2.5 × major center radius
  - Smaller radius (~40% of `urban_sprawl`)

#### Step 1: Populate Nodes

**Urban nodes:**
- Generated within each center's radius using Poisson disk sampling
- Density controlled by `local_density` (nodes per km²)
- Optional gridness applied to snap angles to 45° increments

**Rural nodes:**
- Sparse waypoints in non-urban areas
- Density controlled by `rural_density`
- Avoid urban areas

**Rural settlements:**
- Probabilistically created around rural nodes (`rural_settlement_prob`)
- Small clusters of 3-8 nodes
- Mini road networks

#### Step 2: Intra-City Roads

For each city:
1. **Delaunay triangulation** on city nodes
2. **Gabriel graph** conversion (removes long cross-edges)
3. **MST** computation for guaranteed connectivity
4. **Edge addition** up to `intra_connectivity` ratio
5. **Arterial selection**: Longest edges marked as arterials (`arterial_ratio`)

**Road classification:**
- Arterials in major cities: **G** (Main road), 2-4 lanes, 50-70 km/h
- Arterials in minor cities: **Z** (Collector), 2-3 lanes, 40-60 km/h
- Local roads: **L** (Local), 1-2 lanes, 30-50 km/h
- Access roads: **D** (Access), 1 lane, 20-40 km/h

**Weight limits:**
- 30% of local/access roads get weight limits (3.5-7.5 tons)
- Prevents heavy trucks on small roads

**Directionality:**
- 95% bidirectional
- 5% one-way (simulating one-way streets)

#### Step 3: Inter-City Highways

1. **Centroid graph**: Connect city centers
2. **MST**: Backbone connectivity
3. **k-nearest neighbors**: Add redundancy (`inter_connectivity`)
4. **Path realization**: Direct connections between nearest city nodes

**Highway classification:**
- **A** (Motorway): Major-to-major, distance > 5km, 4-6 lanes, 120-140 km/h
- **S** (Expressway): Major-to-any, distance > 3km, 3-5 lanes, 100-120 km/h
- **GP** (Main accelerated): Other connections, 2-4 lanes, 90-110 km/h

**Properties:**
- Always bidirectional
- No weight limits
- Higher speeds and lane counts

#### Step 4: Ring Roads

With probability `ring_road_prob` for each major center:
- Create ring at ~70% of city radius
- 8+ evenly spaced nodes
- Connected in a circle
- Classification: **Z** (Collector), 2-4 lanes, 60-80 km/h

#### Step 5: Cleanup & Connectivity

1. **Outlier removal**: Remove edges > mean + 3σ length
2. **Dead-end pruning**: Remove degree-1 nodes with short edges (<50m)
3. **Connectivity enforcement**: Connect disconnected components with shortest edges

#### Step 6: Edge ID Reassignment

Ensure sequential edge IDs (0, 1, 2, ...) after cleanup.

## Algorithms & Complexity

### Poisson Disk Sampling
- **Algorithm**: Bridson's algorithm with spatial grid acceleration
- **Complexity**: O(n) where n is number of points
- **Purpose**: Natural-looking, evenly-spaced node placement

### Delaunay Triangulation
- **Library**: scipy.spatial.Delaunay
- **Complexity**: O(n log n)
- **Purpose**: Initial connectivity for intra-city roads

### Gabriel Graph
- **Complexity**: O(n²) for edge filtering
- **Purpose**: Remove unnatural long edges from Delaunay

### Minimum Spanning Tree (MST)
- **Algorithm**: Kruskal's with union-find
- **Complexity**: O(E log E) where E is edges
- **Purpose**: Guarantee connectivity

### K-Nearest Neighbors
- **Library**: scipy.spatial.cKDTree
- **Complexity**: O(log n) per query
- **Purpose**: Highway network redundancy

## Public API / Usage

### Basic Usage

```python
from world.generation import GenerationParams, MapGenerator

# Define parameters
params = GenerationParams(
    map_width=10000.0,
    map_height=10000.0,
    num_major_centers=3,
    minor_per_major=2.0,
    center_separation=2500.0,
    urban_sprawl=800.0,
    local_density=50.0,
    rural_density=5.0,
    intra_connectivity=0.3,
    inter_connectivity=2,
    arterial_ratio=0.2,
    gridness=0.3,
    ring_road_prob=0.5,
    highway_curviness=0.2,
    rural_settlement_prob=0.15,
    seed=42,
)

# Generate map
generator = MapGenerator(params)
graph = generator.generate()

# Access results
print(f"Generated {graph.get_node_count()} nodes")
print(f"Generated {graph.get_edge_count()} edges")
```

### Parameter Tuning Guide

**Dense urban map:**
```python
local_density=80.0,      # High urban density
rural_density=0.0,       # No rural areas
num_major_centers=5,     # Many cities
gridness=0.7,            # Grid-like streets
```

**Sparse rural map:**
```python
local_density=20.0,      # Sparse cities
rural_density=10.0,      # More rural nodes
num_major_centers=2,     # Few cities
gridness=0.0,            # Organic roads
```

**Highway-focused:**
```python
inter_connectivity=4,    # Many highway alternatives
arterial_ratio=0.4,      # More major roads
ring_road_prob=1.0,      # Always create rings
```

## Implementation Notes

### Design Trade-offs

1. **Cleanup non-determinism**: Edge removal in cleanup phase introduces slight randomness even with fixed seed
2. **Gabriel graph**: More expensive (O(n²)) but produces more realistic networks than pure Delaunay
3. **Direct highway paths**: Simple implementation; could be enhanced with waypoint routing through rural nodes
4. **Weight limits**: Probabilistic assignment simulates real-world variation

### Dependencies

- **numpy**: Array operations and random number generation
- **scipy**: Delaunay triangulation and k-d trees
- **dataclasses**: Parameter management
- **random**: Additional randomization

### Polish Road Classification

Based on Polish technical regulations for public roads:

- **A** (Autostrada): Motorways with controlled access
- **S** (Droga ekspresowa): Expressways
- **GP** (Droga główna ruchu przyspieszonego): Main accelerated traffic roads
- **G** (Droga główna): Main roads
- **Z** (Droga zbiorcza): Collector roads
- **L** (Droga lokalna): Local roads
- **D** (Droga dojazdowa): Access roads

## Tests

### Test Coverage

- Parameter validation (all 16 parameters)
- Hierarchical structure verification
- Road classification distribution
- Lane counts, speed limits, weight limits
- Connectivity and reachability
- Ring roads and gridness
- Rural settlements
- Reproducibility (with tolerance)
- Bounds checking

### Critical Test Cases

1. **Basic generation**: Verifies nodes and edges are created within bounds
2. **Road classification**: Ensures all edges have valid Polish road classes
3. **Highway generation**: Verifies high-class roads exist for distant cities
4. **Connectivity**: Ensures graph is fully connected
5. **Sequential IDs**: Verifies node and edge IDs are sequential after cleanup

## Performance

### Benchmarks

- **Small map** (5km × 5km, 2 cities): ~1-2 seconds
- **Medium map** (10km × 10km, 3-5 cities): ~3-10 seconds
- **Large map** (20km × 20km, 10+ cities): ~30-120 seconds

### Bottlenecks

1. **Gabriel graph computation**: O(n²) dominates for large cities
2. **Delaunay triangulation**: O(n log n) per city
3. **Cleanup phase**: Multiple graph traversals

### Optimization Opportunities

- Parallelize per-city generation
- Use approximate Gabriel graph for very large cities
- Cache k-d tree queries for highway generation

## Security & Reliability

### Validation

- All parameters validated in `__post_init__`
- Bounds checking for generated coordinates
- Edge length validation (positive values)
- Connectivity verification with fallback

### Error Handling

- Graceful handling of insufficient nodes for triangulation
- Automatic connectivity enforcement
- Fallback to linear connections for small cities (<3 nodes)

### Logging

- Generation statistics logged at INFO level
- Warnings for unusual configurations
- Error details for failures

## References

### Related Modules

- [`world/graph/graph`](graph/graph.md): Graph data structure
- [`world/graph/edge`](graph/edge.md): Edge and RoadClass definitions
- [`world/graph/node`](graph/node.md): Node structure

### External References

- Bridson, R. (2007). "Fast Poisson Disk Sampling in Arbitrary Dimensions"
- Delaunay, B. (1934). "Sur la sphère vide"
- Gabriel, K. R. & Sokal, R. R. (1969). "A New Statistical Approach to Geographic Variation Analysis"
- Polish road classification: Rozporządzenie Ministra Infrastruktury w sprawie warunków technicznych
