---
title: "Navigator - Pathfinding and Node Search Service"
summary: "A* pathfinding and generalized node search service for computing optimal time-based routes and finding nodes matching arbitrary criteria."
source_paths:
  - "world/routing/navigator.py"
last_updated: "2025-11-19"
owner: "Mateusz Polis"
tags: ["module", "algorithm", "routing", "pathfinding"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["criteria.md"]
---

# Navigator - Pathfinding and Node Search Service

> **Purpose:** Provides efficient pathfinding (A*) and generalized node search (Dijkstra) for agents navigating the graph network. Computes optimal routes based on travel time, finds nodes matching arbitrary criteria, and supports waypoint-aware search for detour minimization.

## Context & Motivation

In a logistics simulation, transport agents need to navigate efficiently through a road network to deliver packages. The Navigator service solves the shortest path problem using the A* algorithm, which balances optimality with computational efficiency.

### Problem Solved
- Compute optimal routes between any two nodes in the graph
- Find closest nodes matching arbitrary criteria (building types, edge counts, etc.)
- Account for varying road speeds and agent capabilities
- Provide time-based routing (fastest path, not shortest distance)
- Handle dynamic agent speed constraints
- Minimize detours when finding waypoints on planned routes

### Requirements and Constraints
- Must work with the existing `Graph` data structure
- Must respect edge speed limits (`edge.max_speed_kph`)
- Must respect agent speed limits (`max_speed_kph` parameter)
- Must return node-based routes (edges derived by caller)
- Must handle edge cases: no path exists, same start/goal, empty graph

### Dependencies and Assumptions
- Depends on `world.graph.graph.Graph` for graph structure
- Assumes edges have valid `length_m` and `max_speed_kph` attributes
- Assumes nodes have valid `x` and `y` coordinates for heuristic
- Assumes graph is directed (uses `get_outgoing_edges`)

## Responsibilities & Boundaries

### In-scope
- A* pathfinding algorithm implementation
- Dijkstra-based closest node search with criteria matching
- Waypoint-aware search for detour minimization (S→B→T optimization)
- Time-based cost calculation
- Euclidean distance heuristic (A*)
- Speed constraint handling (min of edge and agent speed)
- Path reconstruction
- Building route finding with caching (via criteria)
- Criteria-based node search results caching

### Out-of-scope
- Graph modification or validation
- Traffic simulation or dynamic edge costs
- Multi-agent coordination or collision avoidance
- Edge-based route representation (returns nodes only)

## Architecture & Design

### Key Classes and Functions

**`Navigator` class:**
- Caching service with minimal state (criteria-based cache + legacy building cache)
- Five public methods:
  - `find_route` - A* point-to-point pathfinding
  - `find_closest_node` - Single Dijkstra closest node search
  - `find_closest_node_on_route` - Waypoint-aware search (minimizes S→B→T)
  - `find_route_to_building` - Legacy building search (now uses criteria internally)
  - `_calculate_edge_cost` - Shared edge cost helper
  - `_reverse_dijkstra` - Reverse graph Dijkstra for waypoint search

**Method signatures:**
```python
def find_route(
    self,
    start: NodeID,
    goal: NodeID,
    graph: Graph,
    max_speed_kph: float
) -> list[NodeID]

def find_closest_node(
    self,
    start: NodeID,
    graph: Graph,
    max_speed_kph: float,
    criteria: NodeCriteria,
) -> tuple[NodeID | None, Any | None, list[NodeID] | None]

def find_closest_node_on_route(
    self,
    start: NodeID,
    destination: NodeID,
    graph: Graph,
    max_speed_kph: float,
    criteria: NodeCriteria,
) -> tuple[NodeID | None, Any | None, list[NodeID] | None]
```

### Data Flow

1. **Input validation:** Check if start and goal exist in graph
2. **Edge case handling:** Return `[start]` if start equals goal
3. **A* search:**
   - Initialize open set (priority queue) with start node
   - Track g_scores (actual cost from start)
   - Track came_from (parent pointers for path reconstruction)
   - Explore neighbors via outgoing edges
4. **Cost calculation:** For each edge: `edge.length_m / min(edge.max_speed_kph, max_speed_kph)`
5. **Heuristic:** Euclidean distance from node to goal divided by max_speed_kph
6. **Path reconstruction:** Follow came_from pointers from goal to start, reverse
7. **Return:** List of NodeIDs or empty list if no path

### Generalized Node Search (Criteria-Based)

The Navigator provides criteria-based node search using single Dijkstra traversal, replacing the old inefficient N×A* approach.

**Simple Closest Node Search:**

Finds the closest node matching given criteria using single Dijkstra from start.

```python
def find_closest_node(
    start: NodeID,
    graph: Graph,
    max_speed_kph: float,
    criteria: NodeCriteria,
) -> tuple[NodeID | None, Any | None, list[NodeID] | None]
```

**Features:**
- Single shortest-path tree expansion (not N separate A* runs)
- Stops at first matching node (early termination)
- Returns matched item (e.g., Building instance, not just node)
- Caches results by criteria cache key
- **Complexity:** O(E log V) worst case, typically O(k log k) where k << V

**Waypoint-Aware Search (Detour Minimization):**

Finds nodes "on the way" from start to destination, minimizing total trip cost S→B→T.

```python
def find_closest_node_on_route(
    start: NodeID,
    destination: NodeID,
    graph: Graph,
    max_speed_kph: float,
    criteria: NodeCriteria,
) -> tuple[NodeID | None, Any | None, list[NodeID] | None]
```

**Algorithm (Two-Phase Dijkstra):**

**Phase A - Reverse Dijkstra:**
1. Run Dijkstra from destination on reverse graph (incoming edges)
2. Compute `dist_to_dest[v]` for all reachable nodes
3. This creates a "distance-to-destination potential" field

**Phase B - Forward Dijkstra with S→B→T Evaluation:**
1. Run forward Dijkstra from start
2. For each node `u` popped from queue:
   - Check if `u` matches criteria
   - If match: compute `total_cost = g[u] + dist_to_dest[u]`
   - Track best match by minimum total cost
3. **Early stopping:** When `g[u] >= best_total_cost`, stop
   - Remaining nodes have `g[·] ≥ g[u]`, cannot improve solution

**Why This Works:**
- A node "behind" start has large `dist_to_dest` (must go backwards then forwards)
- A node "on the way" has small `dist_to_dest` (already pointing toward destination)
- Algorithm systematically prefers low-detour nodes

**Example:**
```
Start (S) ──→ Parking A ──→ Destination (D)
       \\
        ↘ Parking B (behind start)

Cost(S→A→D) = 2000m (A is on the way)
Cost(S→B→D) = 5000m (B requires backtracking)

Algorithm finds A, not B (even if B is closer to S)
```

**Benefits:**
- Finds parking/gas stations "on the way" automatically
- Minimizes total trip time (no unnecessary detours)
- Used by trucks seeking parking while traveling to destination
- **Complexity:** O(E log V) for two Dijkstra runs

**Legacy Building Search:**

```python
def find_route_to_building(
    start: NodeID,
    graph: Graph,
    max_speed_kph: float,
    building_type: type[Building],
    exclude_buildings: set[BuildingID],
) -> tuple[BuildingID | None, list[NodeID] | None]
```

Now implemented using `find_closest_node` internally with `BuildingTypeCriteria`.

**Cache Structure:**
```python
# Criteria-based cache (new)
_node_cache: dict[
    tuple[str, NodeID],  # (criteria_key, start)
    list[tuple[NodeID, Any, list[NodeID], float]]  # (node, item, route, cost)
]

# Legacy building cache (kept for compatibility)
_building_cache: dict[
    tuple[type[Building], NodeID],
    list[tuple[BuildingID, NodeID, list[NodeID]]]
]
```

### State Management
- Maintains parking route cache: `_parking_cache`
- All other state is local to method calls
- Thread-safe for read-only graph operations

### Resource Handling
- Memory: O(V) for g_scores and came_from dictionaries
- No file I/O, network, or external resources

## Algorithms & Complexity

### Algorithm Summary

| Method | Algorithm | Complexity | Use Case |
|--------|-----------|------------|----------|
| `find_route` | A* | O(E log V) | Point-to-point routing |
| `find_closest_node` | Dijkstra | O(E log V)* | Find nearest matching node |
| `find_closest_node_on_route` | 2× Dijkstra | O(E log V) | Minimize detour on trip |

\* Typically O(k log k) where k = nodes explored before match (k << V)

### A* Algorithm

A* is an informed search algorithm that uses a heuristic to guide exploration toward the goal.

**Cost function:**
```
f(n) = g(n) + h(n)
```
- `g(n)`: Actual cost from start to node n (time in hours)
- `h(n)`: Heuristic estimate from n to goal (Euclidean distance / max_speed_kph)

**Properties:**
- **Optimal:** Finds shortest path if heuristic is admissible (never overestimates)
- **Complete:** Always finds a path if one exists
- **Efficient:** Explores fewer nodes than Dijkstra's algorithm

### Dijkstra's Algorithm (Closest Node Search)

Single-source shortest path with early termination at first match.

**Pseudocode:**
```
closest_node(start, graph, criteria):
    pq = [(0, start)]
    cost[start] = 0
    prev[start] = None

    while pq not empty:
        (cost, u) = pq.pop()

        if criteria.matches(u):
            return (u, reconstruct_path(prev, u))

        for each edge (u → v):
            new_cost = cost[u] + edge_cost(u, v)
            if new_cost < cost[v]:
                cost[v] = new_cost
                prev[v] = u
                pq.push((new_cost, v))

    return (None, None)
```

**Key Optimization:** Stops at first match, does not explore entire graph.

**Old vs New Comparison:**

*Old approach (find_route_to_building):*
- Find all N buildings in graph: O(V)
- Run A* to each: N × O(E log V)
- Total: O(N × E log V)

*New approach (find_closest_node):*
- Single Dijkstra with early termination: O(E log V)
- Typically stops after exploring k nodes: O(k log k) where k << V
- **Speedup:** 10-100× faster for typical graphs

### Two-Phase Dijkstra (Waypoint Search)

Minimizes total trip cost S→B→T by computing distances to destination.

**Phase A - Reverse Dijkstra:**
```
reverse_dijkstra(destination, graph):
    pq = [(0, destination)]
    dist_to_dest[destination] = 0

    while pq not empty:
        (cost, u) = pq.pop()
        for each INCOMING edge (v → u):
            new_cost = cost[u] + edge_cost(v, u)
            if new_cost < dist_to_dest[v]:
                dist_to_dest[v] = new_cost
                pq.push((new_cost, v))

    return dist_to_dest
```

**Phase B - Forward Dijkstra with S→B→T Evaluation:**
```
find_on_route(start, dest, graph, criteria):
    dist_to_dest = reverse_dijkstra(dest, graph)

    pq = [(0, start)]
    g[start] = 0
    best_node = None
    best_cost = ∞

    while pq not empty:
        (current_g, u) = pq.pop()

        # Early stopping
        if current_g >= best_cost:
            break

        # Check if u matches and has path to dest
        if u in dist_to_dest and criteria.matches(u):
            total_cost = g[u] + dist_to_dest[u]
            if total_cost < best_cost:
                best_node = u
                best_cost = total_cost

        # Continue search
        for each edge (u → v):
            new_g = g[u] + edge_cost(u, v)
            if new_g < g[v]:
                g[v] = new_g
                prev[v] = u
                pq.push((new_g, v))

    return (best_node, reconstruct_path(prev, best_node))
```

**Correctness Proof:**
- `dist_to_dest[v]` is optimal cost from v to destination (Dijkstra guarantees)
- `g[v]` is optimal cost from start to v (Dijkstra guarantees)
- `total_cost = g[v] + dist_to_dest[v]` is optimal cost for S→v→T
- Early stopping valid: if `g[u] >= best_cost`, then any unexplored v has `g[v] ≥ g[u]`, so `g[v] + dist_to_dest[v] ≥ best_cost`

**Complexity:** O(E log V) for two Dijkstra runs (reverse + forward)

### Cost Function Details

**Edge cost (time-based):**
```python
effective_speed_kph = min(edge.max_speed_kph, max_speed_kph)
edge_cost_hours = edge.length_m / (effective_speed_kph * 1000.0)
```

This ensures:
- Agents cannot exceed their maximum speed
- Agents respect road speed limits
- Routes optimize for travel time, not distance

**Heuristic (admissible):**
```python
dx = node.x - goal_node.x
dy = node.y - goal_node.y
distance_m = sqrt(dx^2 + dy^2)
h(n) = distance_m / (max_speed_kph * 1000.0)
```

This is admissible because:
- Euclidean distance is the shortest possible path
- Assumes agent travels at maximum speed (optimistic)
- Never overestimates actual travel time

### Complexity Analysis

- **Time complexity:** O((V + E) log V)
  - Each node visited at most once: O(V)
  - Each edge examined at most once: O(E)
  - Priority queue operations: O(log V) per operation
  - Total: O((V + E) log V)

- **Space complexity:** O(V)
  - g_scores dictionary: O(V)
  - came_from dictionary: O(V)
  - open_set priority queue: O(V) worst case
  - open_set_members set: O(V)

### Edge Cases

1. **Start equals goal:** Return `[start]` immediately
2. **No path exists:** Return empty list `[]`
3. **Start or goal not in graph:** Return empty list `[]`
4. **Single node graph:** Returns `[node]` if start equals goal, else `[]`
5. **Zero speed edge:** Would cause division by zero; assumes all edges have positive speed

## Public API / Usage

### Method Signature

```python
def find_route(
    self,
    start: NodeID,
    goal: NodeID,
    graph: Graph,
    max_speed_kph: float
) -> list[NodeID]
```

### Parameters

- **start:** Starting node ID
- **goal:** Destination node ID
- **graph:** Graph instance to navigate
- **max_speed_kph:** Maximum speed of the agent (km/h)

### Returns

- **list[NodeID]:** Ordered list of nodes from start to goal (inclusive)
- **Empty list:** If no path exists or invalid input

### Example Usage

```python
from world.routing.navigator import Navigator
from core.types import NodeID

navigator = Navigator()

# Find route for truck with 80 kph max speed
route = navigator.find_route(
    start=NodeID(1),
    goal=NodeID(10),
    graph=world.graph,
    max_speed_kph=80.0
)

if route:
    print(f"Route found: {route}")
    # Route found: [1, 3, 7, 10]
else:
    print("No path exists")
```

### Integration with Truck Agent

```python
# In Truck.decide()
if not self.route and self.current_node:
    self.destination = random.choice(available_nodes)
    self.route = world.router.find_route(
        self.current_node,
        self.destination,
        world.graph,
        self.max_speed_kph
    )
    # Remove current node from route
    if self.route and self.route[0] == self.current_node:
        self.route.pop(0)
```

## Implementation Notes

### Key Design Trade-offs

1. **Node-based vs Edge-based routes:**
   - Returns list of nodes, not edges
   - Caller derives edges by querying graph adjacency
   - Simpler interface, more flexible for different graph representations

2. **Time-based vs Distance-based:**
   - Optimizes for travel time, not distance
   - More realistic for logistics simulation
   - Accounts for varying road speeds

3. **Stateless service:**
   - No route caching or history
   - Simpler implementation, easier to reason about
   - Future: could add caching layer for repeated queries

4. **Tie-breaking with counter:**
   - Uses counter to break ties in priority queue
   - Ensures deterministic behavior
   - Prevents comparison of NodeID objects

### Third-party Libraries

- **heapq:** Python standard library for priority queue
- **math:** Python standard library for sqrt function

### Testing Hooks

- Stateless design makes unit testing straightforward
- No mocking required for basic path tests
- Can test with small synthetic graphs

## Tests

### Test Scope and Strategy

**Unit tests** (future):
- Path correctness on known graphs
- Edge cases: no path, same start/goal, invalid nodes
- Cost calculation accuracy
- Heuristic admissibility

**Integration tests** (future):
- Integration with Truck agent
- Performance on large graphs
- Multi-agent routing scenarios

### Critical Test Cases

1. **Simple path:** 3-node linear graph, verify correct path
2. **Multiple paths:** Graph with shortcuts, verify optimal path chosen
3. **No path:** Disconnected graph, verify empty list returned
4. **Same start/goal:** Verify `[start]` returned
5. **Speed constraints:** Verify route changes based on agent max_speed
6. **Large graph:** Performance test with 1000+ nodes

## Performance

### Benchmarks

**Expected performance** (not yet measured):
- Small graphs (< 100 nodes): < 1ms
- Medium graphs (100-1000 nodes): 1-10ms
- Large graphs (1000-10000 nodes): 10-100ms

### Known Bottlenecks

1. **Priority queue operations:** O(log V) per operation
   - Dominates runtime for dense graphs
   - Python heapq is efficient but not optimal for all cases

2. **Heuristic calculation:** sqrt() called for every node
   - Could cache if nodes don't move
   - Negligible compared to priority queue overhead

3. **Limited route caching:**
   - General routes not cached (recompute from scratch)
   - Parking routes cached per start node
   - Cache invalidation not implemented (assumes static graph)

### Optimization Opportunities

1. **Bidirectional A*:** Search from both start and goal
2. **Hierarchical pathfinding:** Precompute shortcuts for long routes
3. **General route caching:** Extend caching beyond parking routes with LRU policy
4. **Cache invalidation:** Invalidate caches when graph structure changes
5. **Parallel search:** For multi-agent scenarios

## Security & Reliability

### Validation

- Checks if start and goal exist in graph
- Returns empty list for invalid input (no exceptions)
- Handles empty graphs gracefully

### Error Handling

- No exceptions raised for invalid input
- Caller must check for empty list return
- Division by zero possible if edge.max_speed_kph is 0 (assumes valid graph)

### Fault Tolerance

- Stateless design: no state corruption possible
- Thread-safe: no shared mutable state
- Deterministic: same input always produces same output

### Logging and Observability

- No logging currently implemented
- Future: could log route computation time, path length, nodes explored

## References

### Related Modules

- `world.graph.graph.Graph`: Graph data structure
- `world.graph.node.Node`: Node representation with x, y coordinates
- `world.graph.edge.Edge`: Edge representation with length and speed
- `agents.transports.truck.Truck`: Primary consumer of Navigator service

### ADRs

- None yet (consider creating ADR for time-based vs distance-based routing)

### Papers and Specifications

- **A* algorithm:** Hart, P. E.; Nilsson, N. J.; Raphael, B. (1968). "A Formal Basis for the Heuristic Determination of Minimum Cost Paths"
- **Admissible heuristics:** Russell, S.; Norvig, P. (2020). "Artificial Intelligence: A Modern Approach" (4th ed.)

### Issues and PRs

- None yet
