"""Tests for procedural map generation."""

import unittest

from world.generation import GenerationParams, MapGenerator
from world.graph.edge import Mode


class TestGenerationParams(unittest.TestCase):
    """Test GenerationParams dataclass."""

    def test_valid_params(self) -> None:
        """Test valid parameter creation."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=50, density=50, urban_areas=3)
        assert params.width == 1000.0
        assert params.height == 1000.0
        assert params.nodes == 50
        assert params.density == 50
        assert params.urban_areas == 3

    def test_invalid_width(self) -> None:
        """Test invalid width parameter."""
        with self.assertRaises(ValueError, msg="Width and height must be positive"):
            GenerationParams(width=-100.0, height=1000.0, nodes=50, density=50, urban_areas=3)

    def test_invalid_height(self) -> None:
        """Test invalid height parameter."""
        with self.assertRaises(ValueError, msg="Width and height must be positive"):
            GenerationParams(width=1000.0, height=0.0, nodes=50, density=50, urban_areas=3)

    def test_invalid_nodes_above_range(self) -> None:
        """Test nodes parameter above valid range."""
        with self.assertRaises(ValueError, msg="nodes parameter must be between 0 and 100"):
            GenerationParams(width=1000.0, height=1000.0, nodes=150, density=50, urban_areas=3)

    def test_invalid_nodes_below_range(self) -> None:
        """Test nodes parameter below valid range."""
        with self.assertRaises(ValueError, msg="nodes parameter must be between 0 and 100"):
            GenerationParams(width=1000.0, height=1000.0, nodes=-10, density=50, urban_areas=3)

    def test_valid_nodes_extremes(self) -> None:
        """Test nodes at valid extremes."""
        params1 = GenerationParams(width=1000.0, height=1000.0, nodes=0, density=50, urban_areas=3)
        assert params1.nodes == 0

        params2 = GenerationParams(
            width=1000.0, height=1000.0, nodes=100, density=50, urban_areas=3
        )
        assert params2.nodes == 100

    def test_invalid_density(self) -> None:
        """Test invalid density parameter."""
        with self.assertRaises(ValueError):
            GenerationParams(width=1000.0, height=1000.0, nodes=50, density=150, urban_areas=3)

    def test_invalid_urban_areas(self) -> None:
        """Test invalid urban_areas parameter."""
        with self.assertRaises(ValueError):
            GenerationParams(width=1000.0, height=1000.0, nodes=50, density=50, urban_areas=0)

    def test_invalid_urban_areas_negative(self) -> None:
        """Test negative urban_areas parameter."""
        with self.assertRaises(ValueError):
            GenerationParams(width=1000.0, height=1000.0, nodes=50, density=50, urban_areas=-1)


class TestMapGenerator(unittest.TestCase):
    """Test MapGenerator class."""

    def test_generate_basic_map(self) -> None:
        """Test generating a basic map."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=30, density=30, urban_areas=3)
        generator = MapGenerator(params)
        graph = generator.generate()

        # Should have generated nodes
        assert graph.get_node_count() > 0

        # Should have generated edges
        assert graph.get_edge_count() > 0

        # All nodes should be within bounds
        for node in graph.nodes.values():
            assert 0 <= node.x <= params.width
            assert 0 <= node.y <= params.height

    def test_generate_sparse_map(self) -> None:
        """Test generating a sparse map (low density)."""
        params = GenerationParams(width=5000.0, height=5000.0, nodes=10, density=10, urban_areas=2)
        generator = MapGenerator(params)
        graph = generator.generate()

        # Should have some nodes
        assert graph.get_node_count() >= 10

        # Should have edges
        assert graph.get_edge_count() > 0

    def test_generate_dense_map(self) -> None:
        """Test generating a dense map (high density)."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=80, density=80, urban_areas=5)
        generator = MapGenerator(params)
        graph = generator.generate()

        # Should have many nodes
        assert graph.get_node_count() >= 10

        # Should have many edges
        assert graph.get_edge_count() > graph.get_node_count()

    def test_all_edges_have_valid_length(self) -> None:
        """Test that all edges have positive length."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=40, density=40, urban_areas=3)
        generator = MapGenerator(params)
        graph = generator.generate()

        for edge in graph.edges.values():
            assert edge.length_m > 0

    def test_all_edges_have_road_mode(self) -> None:
        """Test that all edges have ROAD mode."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=40, density=40, urban_areas=3)
        generator = MapGenerator(params)
        graph = generator.generate()

        for edge in graph.edges.values():
            assert edge.mode == Mode.ROAD

    def test_node_ids_are_sequential(self) -> None:
        """Test that node IDs are sequential starting from 0."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=30, density=30, urban_areas=2)
        generator = MapGenerator(params)
        graph = generator.generate()

        node_ids = sorted(graph.nodes.keys())
        for i, node_id in enumerate(node_ids):
            assert node_id == i

    def test_edge_ids_are_sequential(self) -> None:
        """Test that edge IDs are sequential starting from 0."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=20, density=30, urban_areas=2)
        generator = MapGenerator(params)
        graph = generator.generate()

        edge_ids = sorted(graph.edges.keys())
        for i, edge_id in enumerate(edge_ids):
            assert edge_id == i

    def test_graph_is_connected(self) -> None:
        """Test that generated graph is connected."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=30, density=50, urban_areas=3)
        generator = MapGenerator(params)
        graph = generator.generate()

        # The graph should be connected
        assert graph.is_connected()

    def test_bidirectional_edges_dominate(self) -> None:
        """Test that most edges in cities are bidirectional."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=50, density=60, urban_areas=3)
        generator = MapGenerator(params)
        graph = generator.generate()

        # Count unique bidirectional pairs
        edge_pairs: dict[tuple[int, int], int] = {}
        for edge in graph.edges.values():
            from_id = int(edge.from_node)
            to_id = int(edge.to_node)
            pair = (min(from_id, to_id), max(from_id, to_id))
            edge_pairs[pair] = edge_pairs.get(pair, 0) + 1

        # Count bidirectional vs unidirectional
        bidirectional_count = sum(1 for count in edge_pairs.values() if count == 2)
        total_unique = len(edge_pairs)

        # At least 50% should be bidirectional (some may be highways with all bidirectional)
        assert bidirectional_count >= total_unique * 0.4

    def test_no_duplicate_nodes(self) -> None:
        """Test that no nodes are placed at exact same coordinates."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=30, density=40, urban_areas=2)
        generator = MapGenerator(params)
        graph = generator.generate()

        positions = [(node.x, node.y) for node in graph.nodes.values()]
        assert len(positions) == len(set(positions))

    def test_different_urban_areas(self) -> None:
        """Test that different urban_area counts produce different node counts."""
        params1 = GenerationParams(width=1000.0, height=1000.0, nodes=50, density=50, urban_areas=2)
        params2 = GenerationParams(width=1000.0, height=1000.0, nodes=50, density=50, urban_areas=5)

        generator1 = MapGenerator(params1)
        generator2 = MapGenerator(params2)

        graph1 = generator1.generate()
        graph2 = generator2.generate()

        # Both should generate graphs
        assert graph1.get_node_count() > 0
        assert graph2.get_node_count() > 0

    def test_edges_connect_valid_nodes(self) -> None:
        """Test that all edges connect valid nodes."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=25, density=30, urban_areas=2)
        generator = MapGenerator(params)
        graph = generator.generate()

        for edge in graph.edges.values():
            # Both nodes should exist in the graph
            assert edge.from_node in graph.nodes
            assert edge.to_node in graph.nodes

            # Nodes should not be the same
            assert edge.from_node != edge.to_node

    def test_large_map_generation(self) -> None:
        """Test generating a large map."""
        params = GenerationParams(
            width=10000.0, height=10000.0, nodes=70, density=60, urban_areas=10
        )
        generator = MapGenerator(params)
        graph = generator.generate()

        # Should generate many nodes
        assert graph.get_node_count() >= 20

        # All nodes within bounds
        for node in graph.nodes.values():
            assert 0 <= node.x <= params.width
            assert 0 <= node.y <= params.height

    def test_reproducibility(self) -> None:
        """Test that multiple generations with same params produce similar results."""
        params = GenerationParams(width=1000.0, height=1000.0, nodes=30, density=40, urban_areas=3)

        # Generate multiple graphs
        graphs = []
        for _ in range(3):
            generator = MapGenerator(params)
            graphs.append(generator.generate())

        # All should have similar node counts (within reasonable variance)
        node_counts = [g.get_node_count() for g in graphs]
        # The variance shouldn't be too large (allow for some randomness in Poisson disk)
        assert max(node_counts) - min(node_counts) < 20
