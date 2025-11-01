---
title: "Procedural Map Generation"
summary: "Procedural generation of realistic road network maps with cities, villages, and highways using Poisson disk sampling and Delaunay triangulation."
source_paths:
  - "world/generation/generator.py"
last_updated: "2025-01-27"
owner: "Mateusz Polis"
tags: ["module", "algorithm", "generation", "procedural", "network"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["world", "graph/graph"]
---

# Procedural Map Generation

> **Purpose:** Generates realistic road network maps procedurally using advanced algorithms for natural-looking distributions, clustering, and connectivity suitable for logistics simulations.

## Context & Motivation

The Map Generation module provides a fully automated way to create simulation environments without manual map design. This is essential for:

- **Rapid prototyping** of different network topologies
- **Testing scalability** with various map sizes and densities
- **Creating diverse scenarios** with realistic urban/suburban/highway distributions
- **Research applications** where controlled randomization is needed

The system uses established algorithms from computational geometry and computer graphics to ensure realistic, natural-looking results.

## Responsibilities & Boundaries

### In-scope

- Node placement using Poisson disk sampling
- Urban area clustering via K-means
- Road network topology via Delaunay triangulation
- Bidirectional/one-way road assignment based on location
- Highway identification and connection

### Out-of-scope

- Routing algorithms (handled by router module)
- Traffic simulation (handled by traffic module)
- Building placement (future enhancement)
- Agent spawning (handled by simulation)

## Architecture & Design

### Core Components

```python
@dataclass
class GenerationParams:
    width: float           # Map width in meters
    height: float          # Map height in meters
    nodes: int             # 0-100 density factor
    density: int           # 0-100 clustering factor
    urban_areas: int       # Number of cities/villages

class MapGenerator:
    def __init__(self, params: GenerationParams)
    def generate() -> Graph
```

### Generation Pipeline

1. **Node Placement (Poisson Disk Sampling)**
   - Distributes nodes evenly without clustering artifacts
   - Adjusts density based on `nodes` parameter (0 = sparse, 100 = Tokyo-dense)
   - Uses Bridson's algorithm for O(N) complexity

2. **City Clustering (K-means)**
   - Groups nodes into `urban_areas` clusters
   - Identifies cluster centers as city cores
   - Distinguishes cities (large clusters) from villages (small clusters)

3. **Edge Creation (Delaunay Triangulation)**
   - Builds natural-looking road networks
   - Connects nodes into triangles for complete coverage
   - Ensures graph connectivity

4. **Road Direction Assignment**
   - **Within cities**: 95% bidirectional, 5% one-way (realistic urban traffic)
   - **Highways (between cities)**: 100% bidirectional (main arteries)
   - Configurable for different traffic patterns

## Algorithms & Complexity

### Poisson Disk Sampling

**Algorithm**: Bridson's Poisson disk sampling with grid acceleration
- **Time Complexity**: O(N) where N = number of points
- **Space Complexity**: O(N)
- **Quality**: Guarantees minimum distance between points
- **Realism**: Avoids grid artifacts, produces natural distributions

**Implementation Details**:
```python
def _generate_node_positions(self) -> list[tuple[float, float]]:
    # Calculate target nodes based on density
    # Use grid-accelerated distance checking
    # Maintain active list until target reached
```

### K-means Clustering

**Algorithm**: Classic K-means with random centroid initialization
- **Time Complexity**: O(N * K * I) where N = points, K = clusters, I = iterations
- **Convergence**: Typically < 100 iterations
- **Quality**: Balanced clustering suitable for urban areas

**Implementation Details**:
```python
def _cluster_nodes(self, positions: list[tuple[float, float]]) -> list[list[int]]:
    # Initialize random centroids
    # Iterate: assign to nearest centroid, update centers
    # Return cluster assignments
```

### Delaunay Triangulation

**Algorithm**: SciPy's optimized Delaunay implementation
- **Time Complexity**: O(N log N) worst case, O(N) expected
- **Quality**: Optimal triangulation for given points
- **Connectivity**: Guarantees all points connect, natural angles

**Implementation Details**:
```python
from scipy.spatial import Delaunay

points = np.array(positions)
tri = Delaunay(points)
# Process simplex edges
```

## Public API / Usage

### Basic Generation

```python
from world.generation import GenerationParams, MapGenerator
from world.graph.graph import Graph

# Define parameters
params = GenerationParams(
    width=10000.0,      # 10km wide
    height=10000.0,     # 10km tall
    nodes=75,           # 75% density (Tokyo-like)
    density=50,         # 50% clustering
    urban_areas=5       # 5 cities/villages
)

# Generate map
generator = MapGenerator(params)
graph = generator.generate()

# Use the graph
print(f"Generated {graph.get_node_count()} nodes")
print(f"Generated {graph.get_edge_count()} edges")
```

### Parameter Guide

**`width` / `height`**: Map dimensions in meters
- Typical: 1000-100000m
- Affects absolute scale of the network

**`nodes`**: Density factor (0-100 scale)
- `0`: Very sparse (~10 nodes minimum)
- `50`: Medium density
- `100`: Maximum density (Tokyo-city level)

**`density`**: Node clustering (0-100 scale)
- `0`: Nodes spread out evenly
- `50`: Moderate clustering
- `100`: Tight clustering in urban centers

**`urban_areas`**: Number of distinct cities/villages
- Determines how many clusters to create
- Affects connectivity patterns
- Minimum: 1, Recommended: 2-10

### Action-Based Generation

Generation is typically triggered via WebSocket action:

```json
{
  "action": "map.create",
  "params": {
    "width": 10000,
    "height": 10000,
    "nodes": 75,
    "density": 50,
    "urban_areas": 5
  }
}
```

Response signal:

```json
{
  "signal": "map.created",
  "data": {
    "width": 10000,
    "height": 10000,
    "nodes": 75,
    "density": 50,
    "urban_areas": 5,
    "generated_nodes": 850,
    "generated_edges": 2400
  }
}
```

## Implementation Notes

### Design Trade-offs

1. **Deterministic vs Random**: Uses fixed random seeds (42) in some places for debugging, but allows variance in Poisson disk sampling for realism

2. **Connectivity**: Delaunay triangulation guarantees a connected graph, but may create unrealistic shortcuts in dense areas

3. **Bidirectional Ratio**: 95% within cities is realistic for urban networks, but configurable

4. **Highway Detection**: Currently based on inter-cluster connections; future versions may add explicit highway tagging

### Third-party Libraries

- **NumPy**: Efficient array operations for clustering
- **SciPy**: Fast Delaunay triangulation implementation
- **Standard Library**: `random`, `math`, `dataclasses`

### Testing Hooks

The generator is extensively unit tested (see `tests/world/test_generator.py`) with:
- Parameter validation
- Graph connectivity checks
- Edge distribution analysis
- Boundary condition verification

## Tests

Comprehensive test suite covers:

1. **Parameter Validation**: Invalid inputs rejected
2. **Graph Properties**: Connectivity, node/edge counts, ID sequencing
3. **Edge Distribution**: Bidirectional ratios, valid lengths, road modes
4. **Boundary Conditions**: Large maps, sparse maps, dense maps
5. **Reproducibility**: Similar results with same parameters

**Run tests**:
```bash
poetry run pytest tests/world/test_generator.py -v
```

## Performance

### Benchmarks

- **Small map** (1000x1000, 30 nodes, 3 cities): ~50ms
- **Medium map** (10000x10000, 500 nodes, 5 cities): ~200ms
- **Large map** (100000x100000, 5000 nodes, 10 cities): ~2s

### Bottlenecks

1. **Poisson Disk Sampling**: Can be slow for very high densities
2. **K-means Clustering**: Scales with cluster count
3. **Delaunay**: Very efficient, not a bottleneck

### Optimization Opportunities

- Parallelize Poisson disk sampling
- Use approximate K-means for very large datasets
- Cache triangulation results if reusing point sets

## Security & Reliability

### Validation

- All parameters validated in `GenerationParams.__post_init__()`
- Type checks for all inputs
- Range validation for 0-100 parameters
- Positive value checks for dimensions

### Error Handling

- Clear error messages for invalid parameters
- Graceful degradation for edge cases (e.g., fewer nodes than clusters)
- No file I/O, reduces attack surface

### Logging

Generation actions are logged at INFO level with:
- Generation parameters used
- Result statistics (nodes, edges)
- Any warnings during processing

## References

### Related Modules

- **`world/graph/graph.py`**: Target graph structure
- **`world/graph/node.py`**: Node types
- **`world/graph/edge.py`**: Edge types
- **`world/sim/handlers/map.py`**: Action handler integration
- **`world/sim/queues.py`**: Signal dispatch

### External Resources

- **Poisson Disk Sampling**:
  - R. Bridson, "Fast Poisson Disk Sampling in Arbitrary Dimensions", 2007
  - Provides the grid-accelerated algorithm used
- **Delaunay Triangulation**:
  - Standard computational geometry technique
  - SciPy implementation is based on Qhull
- **K-means Clustering**:
  - J. MacQueen, "Some methods for classification and analysis of multivariate observations", 1967
  - Classic unsupervised learning algorithm
