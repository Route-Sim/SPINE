---
title: "Navigator - A* Pathfinding Service"
summary: "A* pathfinding service for computing optimal time-based routes through the graph network, respecting both edge and agent speed constraints."
source_paths:
  - "world/routing/navigator.py"
last_updated: "2025-11-08"
owner: "Mateusz Polis"
tags: ["module", "algorithm", "routing", "pathfinding"]
links:
  parent: "../../../SUMMARY.md"
  siblings: []
---

# Navigator - A* Pathfinding Service

> **Purpose:** Provides efficient A* pathfinding for agents navigating the graph network, computing optimal routes based on travel time while respecting both road speed limits and agent capabilities.

## Context & Motivation

In a logistics simulation, transport agents need to navigate efficiently through a road network to deliver packages. The Navigator service solves the shortest path problem using the A* algorithm, which balances optimality with computational efficiency.

### Problem Solved
- Compute optimal routes between any two nodes in the graph
- Account for varying road speeds and agent capabilities
- Provide time-based routing (fastest path, not shortest distance)
- Handle dynamic agent speed constraints

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
- Time-based cost calculation
- Euclidean distance heuristic
- Speed constraint handling (min of edge and agent speed)
- Path reconstruction from goal to start

### Out-of-scope
- Graph modification or validation
- Traffic simulation or dynamic edge costs
- Multi-agent coordination or collision avoidance
- Route caching or optimization
- Edge-based route representation (returns nodes only)

## Architecture & Design

### Key Classes and Functions

**`Navigator` class:**
- Stateless service (no instance variables)
- Single public method: `find_route`

**`find_route` method signature:**
```python
def find_route(
    self,
    start: NodeID,
    goal: NodeID,
    graph: Graph,
    max_speed_kph: float
) -> list[NodeID]
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

### State Management
- No persistent state (stateless service)
- All state is local to `find_route` call
- Thread-safe (no shared mutable state)

### Resource Handling
- Memory: O(V) for g_scores and came_from dictionaries
- No file I/O, network, or external resources

## Algorithms & Complexity

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

3. **No route caching:**
   - Repeated queries recompute from scratch
   - Future: add LRU cache for common routes

### Optimization Opportunities

1. **Bidirectional A*:** Search from both start and goal
2. **Hierarchical pathfinding:** Precompute shortcuts for long routes
3. **Route caching:** Cache recent routes with invalidation on graph changes
4. **Parallel search:** For multi-agent scenarios

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
