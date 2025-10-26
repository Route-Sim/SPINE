---
title: "Graph GraphML Tests"
summary: "Test suite for GraphML export and import functionality of the Graph class."
source_paths:
  - "tests/world/test_graph_graphml.py"
last_updated: "2025-10-26"
owner: "Mateusz Polis"
tags: ["test", "graph", "graphml", "export", "import"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["test-sim-runner", "test-websocket-server"]
---

# Graph GraphML Tests

> **Purpose:** Comprehensive test suite for the GraphML export and import functionality, ensuring that all graph data (nodes, edges, and buildings) is correctly serialized and deserialized.

## Context & Motivation

GraphML tests validate that:
- Graph structure is preserved during export/import
- Node coordinates and buildings are correctly serialized
- Edge properties (length, mode) are maintained
- Round-trip export/import produces identical graphs
- Empty graphs and various graph structures are handled

## Test Coverage

### Test Cases

#### Empty Graph
- `test_export_empty_graph`: Verifies empty graph export creates valid GraphML file
- `test_import_empty_graph`: Verifies empty graph can be imported from GraphML

#### Nodes
- `test_export_import_graph_with_nodes`: Tests node serialization (coordinates)

#### Edges
- `test_export_import_graph_with_edges`: Tests edge serialization (from, to, length, mode)

#### Buildings
- `test_export_import_graph_with_buildings`: Tests building serialization as JSON in node attributes

#### Round-Trip
- `test_round_trip_complete_graph`: Comprehensive test with nodes, edges, and buildings

## Test Strategy

### Temporary Files
Tests use Python's `tempfile.NamedTemporaryFile` for temporary GraphML files, ensuring cleanup after each test.

### Verification Methods
- Check node count and edge count
- Verify node coordinates
- Verify edge properties
- Verify building data
- Verify building IDs and counts

### Test Data
- Simple graphs with 1-2 nodes
- Graphs with buildings (1-2 per node)
- Graphs with edges connecting nodes
- Complete graphs with all elements

## Implementation Notes

### Test Structure
```python
class TestGraphGraphML(unittest.TestCase):
    def test_export_empty_graph(self) -> None:
        graph = Graph()
        with tempfile.NamedTemporaryFile(...) as f:
            filepath = f.name
        graph.to_graphml(filepath)
        # Verify file content
```

### Edge Cases Covered
- Empty graphs (no nodes, no edges)
- Single node with no edges
- Multiple nodes with no edges
- Nodes with multiple buildings
- Complete graphs with all elements

## References

### Related Modules
- [Graph](../world/graph/graph.md) - Main graph implementation
- [Node](../world/graph/node.md) - Node with buildings
- [Building](../../core/buildings/base.md) - Building serialization
