import tempfile
import unittest

from core.buildings.base import Building
from core.types import BuildingID, EdgeID, NodeID
from world.graph.edge import Edge, Mode
from world.graph.graph import Graph
from world.graph.node import Node


class TestGraphGraphML(unittest.TestCase):
    """Test GraphML export and import functionality."""

    def test_export_empty_graph(self) -> None:
        """Test exporting an empty graph."""
        graph = Graph()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".graphml", delete=False) as f:
            filepath = f.name

        try:
            graph.to_graphml(filepath)
            # Verify file was created
            with open(filepath) as f:
                content = f.read()
                self.assertIn("<graphml", content)
                self.assertIn('edgedefault="directed"', content)
        finally:
            import os

            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_import_empty_graph(self) -> None:
        """Test importing an empty graph."""
        graph = Graph()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".graphml", delete=False) as f:
            filepath = f.name

        try:
            graph.to_graphml(filepath)
            imported = Graph.from_graphml(filepath)
            self.assertEqual(imported.get_node_count(), 0)
            self.assertEqual(imported.get_edge_count(), 0)
        finally:
            import os

            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_export_import_graph_with_nodes(self) -> None:
        """Test exporting and importing a graph with nodes."""
        graph = Graph()

        # Add nodes
        node1 = Node(id=NodeID(1), x=10.0, y=20.0)
        node2 = Node(id=NodeID(2), x=30.0, y=40.0)
        graph.add_node(node1)
        graph.add_node(node2)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".graphml", delete=False) as f:
            filepath = f.name

        try:
            graph.to_graphml(filepath)
            imported = Graph.from_graphml(filepath)

            # Verify nodes
            self.assertEqual(imported.get_node_count(), 2)
            imported_node1 = imported.get_node(NodeID(1))
            self.assertIsNotNone(imported_node1)
            assert imported_node1 is not None  # Type narrowing for mypy
            self.assertEqual(imported_node1.x, 10.0)
            self.assertEqual(imported_node1.y, 20.0)

            imported_node2 = imported.get_node(NodeID(2))
            self.assertIsNotNone(imported_node2)
            assert imported_node2 is not None  # Type narrowing for mypy
            self.assertEqual(imported_node2.x, 30.0)
            self.assertEqual(imported_node2.y, 40.0)
        finally:
            import os

            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_export_import_graph_with_edges(self) -> None:
        """Test exporting and importing a graph with edges."""
        graph = Graph()

        # Add nodes
        node1 = Node(id=NodeID(1), x=10.0, y=20.0)
        node2 = Node(id=NodeID(2), x=30.0, y=40.0)
        graph.add_node(node1)
        graph.add_node(node2)

        # Add edge
        edge1 = Edge(
            id=EdgeID(1),
            from_node=NodeID(1),
            to_node=NodeID(2),
            length_m=100.0,
            mode=Mode.ROAD,
        )
        graph.add_edge(edge1)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".graphml", delete=False) as f:
            filepath = f.name

        try:
            graph.to_graphml(filepath)
            imported = Graph.from_graphml(filepath)

            # Verify edge
            self.assertEqual(imported.get_edge_count(), 1)
            imported_edge = imported.get_edge(EdgeID(1))
            self.assertIsNotNone(imported_edge)
            assert imported_edge is not None  # Type narrowing for mypy
            self.assertEqual(imported_edge.from_node, NodeID(1))
            self.assertEqual(imported_edge.to_node, NodeID(2))
            self.assertEqual(imported_edge.length_m, 100.0)
            self.assertEqual(imported_edge.mode, Mode.ROAD)
        finally:
            import os

            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_export_import_graph_with_buildings(self) -> None:
        """Test exporting and importing a graph with buildings."""
        graph = Graph()

        # Add node with buildings
        node1 = Node(id=NodeID(1), x=10.0, y=20.0)
        building1 = Building(id=BuildingID("b1"))
        building2 = Building(id=BuildingID("b2"))
        node1.add_building(building1)
        node1.add_building(building2)
        graph.add_node(node1)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".graphml", delete=False) as f:
            filepath = f.name

        try:
            graph.to_graphml(filepath)
            imported = Graph.from_graphml(filepath)

            # Verify node and buildings
            self.assertEqual(imported.get_node_count(), 1)
            imported_node = imported.get_node(NodeID(1))
            self.assertIsNotNone(imported_node)
            assert imported_node is not None  # Type narrowing for mypy
            buildings = imported_node.get_buildings()
            self.assertEqual(len(buildings), 2)

            # Verify building IDs
            building_ids = [b.id for b in buildings]
            self.assertIn(BuildingID("b1"), building_ids)
            self.assertIn(BuildingID("b2"), building_ids)
        finally:
            import os

            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_round_trip_complete_graph(self) -> None:
        """Test round-trip export and import of a complete graph."""
        graph = Graph()

        # Add nodes with buildings
        node1 = Node(id=NodeID(1), x=10.0, y=20.0)
        building1 = Building(id=BuildingID("b1"))
        node1.add_building(building1)
        graph.add_node(node1)

        node2 = Node(id=NodeID(2), x=30.0, y=40.0)
        graph.add_node(node2)

        # Add edges
        edge1 = Edge(
            id=EdgeID(1),
            from_node=NodeID(1),
            to_node=NodeID(2),
            length_m=100.0,
            mode=Mode.ROAD,
        )
        graph.add_edge(edge1)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".graphml", delete=False) as f:
            filepath = f.name

        try:
            # Export and import
            graph.to_graphml(filepath)
            imported = Graph.from_graphml(filepath)

            # Verify structure
            self.assertEqual(imported.get_node_count(), 2)
            self.assertEqual(imported.get_edge_count(), 1)

            # Verify node 1 with building
            imported_node1 = imported.get_node(NodeID(1))
            self.assertIsNotNone(imported_node1)
            assert imported_node1 is not None  # Type narrowing for mypy
            self.assertEqual(imported_node1.x, 10.0)
            self.assertEqual(imported_node1.y, 20.0)
            self.assertEqual(len(imported_node1.get_buildings()), 1)
            self.assertEqual(imported_node1.get_buildings()[0].id, BuildingID("b1"))

            # Verify node 2
            imported_node2 = imported.get_node(NodeID(2))
            self.assertIsNotNone(imported_node2)
            assert imported_node2 is not None  # Type narrowing for mypy
            self.assertEqual(imported_node2.x, 30.0)
            self.assertEqual(imported_node2.y, 40.0)
            self.assertEqual(len(imported_node2.get_buildings()), 0)

            # Verify edge
            imported_edge = imported.get_edge(EdgeID(1))
            self.assertIsNotNone(imported_edge)
            assert imported_edge is not None  # Type narrowing for mypy
            self.assertEqual(imported_edge.from_node, NodeID(1))
            self.assertEqual(imported_edge.to_node, NodeID(2))
            self.assertEqual(imported_edge.length_m, 100.0)
        finally:
            import os

            if os.path.exists(filepath):
                os.unlink(filepath)


if __name__ == "__main__":
    unittest.main()
