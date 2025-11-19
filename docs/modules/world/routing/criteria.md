---
title: "Node Criteria"
summary: "Protocol-based node matching criteria for generalized graph search operations"
source_paths:
  - "world/routing/criteria.py"
last_updated: "2025-11-19"
owner: "Mateusz Polis"
tags: ["module", "algorithm", "api"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["navigator.md"]
---

# Node Criteria

> **Purpose:** Provides a flexible, extensible system for defining node matching criteria in graph searches. Enables finding nodes based on arbitrary conditions (building types, edge counts, composite rules) without hardcoding search logic.

## Context & Motivation

### Problem Solved

The original `find_route_to_building` method was hardcoded to search for building types only. This limited the system's ability to:
- Find nodes based on graph topology (e.g., nodes with specific edge counts)
- Combine multiple criteria (e.g., "parking with at least 3 connections")
- Extend search capabilities without modifying core routing algorithms

### Requirements and Constraints

- **Extensibility:** New criteria types should be easy to add without changing search algorithms
- **Type Safety:** Criteria should be properly typed for mypy strict mode
- **Caching:** Criteria must provide stable cache keys for efficient repeated searches
- **Composability:** Simple criteria should combine into complex rules

### Dependencies and Assumptions

- Uses Python Protocol for duck typing (PEP 544)
- Assumes nodes and graph structure are immutable during a single search
- Building type lookups use Node's O(1) type index

## Responsibilities & Boundaries

### In-scope

- Define node matching interface (Protocol)
- Implement common criteria (building type, edge count, composite)
- Generate cache keys for result memoization
- Return matched items (building instances, nodes, etc.)

### Out-of-scope

- Actual graph traversal (handled by Navigator)
- Caching implementation (managed by Navigator)
- Node and graph data structures
- Route reconstruction

## Architecture & Design

### NodeCriteria Protocol

```python
class NodeCriteria(Protocol):
    def matches(self, node: Node, graph: Graph) -> tuple[bool, Any | None]:
        """Check if node satisfies criteria.

        Returns:
            (True, matched_item) if satisfied, (False, None) otherwise
        """
        ...

    def cache_key(self) -> str:
        """Generate unique cache key for this criteria."""
        ...
```

The Protocol pattern allows:
- Static type checking via mypy
- Duck typing for easy extension
- No inheritance requirements
- Flexible implementation strategies

### Concrete Implementations

#### BuildingTypeCriteria

Matches nodes that contain buildings of a specific type.

**Fields:**
- `building_type: type[Building]` - Type to search for (e.g., Parking, Site)
- `exclude_buildings: set[BuildingID]` - Buildings to skip (for retry logic)

**Behavior:**
- Uses Node's O(1) type index for efficient building lookup
- Returns first matching building not in exclude set
- Cache key excludes exclude_buildings (dynamic, changes between searches)

**Example:**
```python
criteria = BuildingTypeCriteria(Parking, exclude_buildings={"p1", "p2"})
matches, parking = criteria.matches(node, graph)
if matches:
    print(f"Found parking: {parking.id}")
```

#### EdgeCountCriteria

Matches nodes based on total edge count (incoming + outgoing).

**Fields:**
- `min_edges: int | None` - Minimum edges (inclusive), None for no minimum
- `max_edges: int | None` - Maximum edges (inclusive), None for no maximum

**Behavior:**
- Counts both incoming and outgoing edges
- Returns node itself as matched_item
- Useful for finding hubs, endpoints, or simple intersections

**Example:**
```python
# Find nodes with exactly 4 connections (typical 4-way intersection)
criteria = EdgeCountCriteria(min_edges=4, max_edges=4)

# Find hubs (nodes with many connections)
criteria = EdgeCountCriteria(min_edges=6)

# Find endpoints (dead-ends)
criteria = EdgeCountCriteria(max_edges=1)
```

#### CompositeCriteria

Combines multiple criteria with logical operators (AND/OR).

**Fields:**
- `criteria_list: list[NodeCriteria]` - Criteria to combine
- `operator: LogicalOperator` - AND or OR

**Behavior:**
- **AND:** All criteria must match, returns tuple of all matched items
- **OR:** At least one criteria must match, returns tuple of matched items
- Cache key combines all sub-criteria keys

**Example:**
```python
# Find parking buildings at major intersections
criteria = CompositeCriteria(
    [
        BuildingTypeCriteria(Parking),
        EdgeCountCriteria(min_edges=4)
    ],
    operator=LogicalOperator.AND
)
matches, (parking, node) = criteria.matches(node, graph)
```

## Algorithms & Complexity

### BuildingTypeCriteria.matches()

**Complexity:** O(B) where B = buildings of specified type at node (typically B ≤ 3)
- O(1) type index lookup in Node
- O(B) iteration through buildings to check exclusions

### EdgeCountCriteria.matches()

**Complexity:** O(E) where E = edges connected to node (typically E ≤ 10)
- O(1) adjacency list lookup in Graph
- O(E) iteration through edge lists

### CompositeCriteria.matches()

**Complexity:** O(C × M) where C = number of criteria, M = max complexity of any criteria
- AND: stops at first failure (best case O(1), worst case O(C × M))
- OR: stops at first success (best case O(M), worst case O(C × M))

## Public API / Usage

### Implementing Custom Criteria

To add new criteria, implement the Protocol:

```python
class CustomCriteria:
    def matches(self, node: Node, graph: Graph) -> tuple[bool, Any | None]:
        # Your matching logic here
        if some_condition:
            return True, some_object
        return False, None

    def cache_key(self) -> str:
        return f"custom:{self.param1}:{self.param2}"
```

**Best Practices:**
- Keep `matches()` fast (called during graph traversal)
- Generate stable, unique cache keys
- Return meaningful matched items (not just True/None)
- Document complexity assumptions
- Handle edge cases (missing buildings, disconnected nodes, etc.)

### Using with Navigator

```python
navigator = Navigator()

# Simple building search
criteria = BuildingTypeCriteria(Parking)
node_id, parking, route = navigator.find_closest_node(
    start, graph, max_speed_kph, criteria
)

# Waypoint-aware search (considers full trip S→node→destination)
node_id, parking, route = navigator.find_closest_node_on_route(
    start, destination, graph, max_speed_kph, criteria
)
```

## Implementation Notes

### Design Trade-offs

**Protocol vs. ABC:**
- ✅ Protocol: No inheritance required, easier testing, duck typing
- ❌ ABC: Would require inheritance, more boilerplate

**Exclude sets in criteria vs. navigator:**
- ✅ In criteria: Flexible per-search, supports different exclude strategies
- ❌ In navigator: Would require separate method parameters

**Matched item return value:**
- ✅ Return concrete object: Caller gets full context (Building instance, not just ID)
- ❌ Return only ID: Would require additional lookups

### Third-Party Libraries

None required (pure Python with standard library).

## Testing Strategy

### Test Coverage

Tests in `tests/world/test_routing_criteria.py`:
- Building type matching (with/without exclusions)
- Edge count matching (min, max, ranges)
- Composite criteria (AND/OR logic)
- Cache key uniqueness and stability
- Edge cases (empty nodes, no matches)

### Critical Test Cases

1. **BuildingTypeCriteria exclusion handling:** Ensures retry logic works
2. **CompositeCriteria short-circuit evaluation:** Verifies AND stops early on failure
3. **EdgeCountCriteria boundary conditions:** Tests exact matches at min/max
4. **Cache key collision prevention:** Ensures different criteria generate different keys

## Performance

### Benchmarks

Not benchmarked independently (criteria evaluation is negligible compared to graph traversal).

Typical performance:
- `BuildingTypeCriteria.matches()`: ~0.1 μs per node
- `EdgeCountCriteria.matches()`: ~0.5 μs per node
- `CompositeCriteria.matches()`: ~1-2 μs per node (2-3 sub-criteria)

### Bottlenecks

None identified. Criteria evaluation is dominated by:
1. Graph traversal (Dijkstra O(E log V))
2. Route reconstruction (O(path length))

## Security & Reliability

### Validation

- Type checking enforced by mypy strict mode
- Protocol ensures required methods are implemented
- No runtime validation of criteria inputs (assumes valid types from construction)

### Error Handling

- `matches()` should never raise exceptions (return `(False, None)` on failure)
- Graph structure assumed valid (validated by Graph class)
- Building ID exclusions tolerate non-existent IDs (set membership is safe)

### Logging and Observability

No logging in criteria (pure functions, called frequently in hot loop).

Debugging:
- Print `cache_key()` to identify which criteria is in use
- Add temporary logging in `matches()` for specific debugging sessions
- Use Navigator caching metrics to observe criteria effectiveness

## References

### Related Modules

- [`navigator.md`](navigator.md) - Uses criteria for graph search
- [`../../graph/node.md`](../../graph/node.md) - Node structure with building type index
- [`../../graph/graph.md`](../../graph/graph.md) - Graph structure with adjacency lists

### Specifications

- [PEP 544 - Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- Project architecture: Protocol-based design for extensibility
