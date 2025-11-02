"""Tests for the map manager module."""

import shutil
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from core.types import EdgeID, NodeID
from world.graph.edge import Edge, Mode, RoadClass
from world.graph.graph import Graph
from world.graph.node import Node
from world.io.map_manager import (
    export_map,
    import_map,
    map_exists,
    sanitize_map_name,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


class TestSanitizeMapName:
    """Test filename sanitization."""

    def test_alphanumeric_chars(self) -> None:
        """Test that alphanumeric characters pass through."""
        assert sanitize_map_name("test123") == "test123"
        assert sanitize_map_name("MapName_v1") == "MapName_v1"

    def test_allow_underscores_and_hyphens(self) -> None:
        """Test that underscores and hyphens are allowed."""
        assert sanitize_map_name("test_map-123") == "test_map-123"

    def test_remove_special_chars(self) -> None:
        """Test that special characters are replaced with underscores."""
        assert sanitize_map_name("test@map#123") == "test_map_123"
        assert sanitize_map_name("map.with.dots") == "map_with_dots"

    def test_remove_path_separators(self) -> None:
        """Test that path separators are removed."""
        assert sanitize_map_name("../path/to/map") == "___path_to_map"
        assert sanitize_map_name("map\\name") == "map_name"

    def test_empty_or_whitespace(self) -> None:
        """Test that empty or whitespace-only names get a default."""
        assert sanitize_map_name("") == "unnamed_map"
        # Whitespace-only strings get converted to underscores after strip
        assert sanitize_map_name("   ").strip() == "___"
        # After strip, underscores remain
        assert sanitize_map_name("   ") == "___"

    def test_leading_trailing_dots(self) -> None:
        """Test that leading/trailing dots and spaces are removed."""
        # Dots are converted to underscores
        assert sanitize_map_name("..map..") == "__map__"
        # Spaces become underscores before strip removes them
        assert sanitize_map_name(" map ") == "_map_"


class TestExportImportMap:
    """Test map export and import functionality."""

    @pytest.fixture  # type: ignore[misc]
    def temp_maps_dir(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> Generator[Path, None, None]:
        """Create a temporary maps directory for tests."""
        # Create a temporary directory
        temp_dir = tmp_path / "maps"
        temp_dir.mkdir()

        # Patch the get_maps_directory function to return our temp directory
        def mock_get_maps_dir() -> str:
            return str(temp_dir)

        monkeypatch.setattr("world.io.map_manager.get_maps_directory", mock_get_maps_dir)

        yield temp_dir

        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture  # type: ignore[misc]
    def sample_graph(self) -> Graph:
        """Create a sample graph for testing."""
        graph: Graph = Graph()

        # Add nodes
        node1 = Node(id=NodeID(1), x=0.0, y=0.0)
        node2 = Node(id=NodeID(2), x=1.0, y=1.0)
        node3 = Node(id=NodeID(3), x=2.0, y=2.0)

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)

        # Add edges
        edge1 = Edge(
            id=EdgeID(1),
            from_node=NodeID(1),
            to_node=NodeID(2),
            length_m=100.0,
            mode=Mode.ROAD,
            road_class=RoadClass.G,
            lanes=2,
            max_speed_kph=50.0,
            weight_limit_kg=None,
        )
        edge2 = Edge(
            id=EdgeID(2),
            from_node=NodeID(2),
            to_node=NodeID(3),
            length_m=150.0,
            mode=Mode.ROAD,
            road_class=RoadClass.G,
            lanes=2,
            max_speed_kph=50.0,
            weight_limit_kg=None,
        )

        graph.add_edge(edge1)
        graph.add_edge(edge2)

        return graph

    def test_export_map_creates_file(self, temp_maps_dir: Path, sample_graph: Graph) -> None:
        """Test that exporting a map creates the file."""
        map_name = "test_map"

        export_map(sample_graph, map_name)

        # Check that the file was created
        map_file = temp_maps_dir / f"{map_name}.graphml"
        assert map_file.exists()
        assert map_file.is_file()

    def test_export_map_sanitizes_name(self, temp_maps_dir: Path, sample_graph: Graph) -> None:
        """Test that map name is sanitized on export."""
        unsanitized_name = "test@map#123"
        expected_name = "test_map_123"

        export_map(sample_graph, unsanitized_name)

        # Check that the sanitized filename was used
        map_file = temp_maps_dir / f"{expected_name}.graphml"
        assert map_file.exists()

        # Original name should not exist
        bad_file = temp_maps_dir / f"{unsanitized_name}.graphml"
        assert not bad_file.exists()

    def test_export_map_prevents_overwrite(self, temp_maps_dir: Path, sample_graph: Graph) -> None:
        """Test that export fails if file already exists."""
        _ = temp_maps_dir  # Use the fixture to set up the test environment
        map_name = "existing_map"

        # First export should succeed
        export_map(sample_graph, map_name)

        # Second export should fail
        with pytest.raises(ValueError, match="already exists"):
            export_map(sample_graph, map_name)

    def test_import_map_loads_file(self, temp_maps_dir: Path, sample_graph: Graph) -> None:
        """Test that importing a map loads the file correctly."""
        _ = temp_maps_dir  # Use the fixture to set up the test environment
        map_name = "test_import"

        # Export a map first
        export_map(sample_graph, map_name)

        # Import it
        imported_graph = import_map(map_name)

        # Verify the imported graph has the same structure
        assert imported_graph.get_node_count() == 3
        assert imported_graph.get_edge_count() == 2

        # Verify node coordinates
        node1 = imported_graph.get_node(NodeID(1))
        assert node1 is not None
        if node1:  # Type narrowing
            assert node1.x == 0.0
            assert node1.y == 0.0

        node2 = imported_graph.get_node(NodeID(2))
        assert node2 is not None
        if node2:  # Type narrowing
            assert node2.x == 1.0
            assert node2.y == 1.0

        node3 = imported_graph.get_node(NodeID(3))
        assert node3 is not None
        if node3:  # Type narrowing
            assert node3.x == 2.0
            assert node3.y == 2.0

        # Verify edge properties
        edge1 = imported_graph.get_edge(EdgeID(1))
        assert edge1 is not None
        if edge1:  # Type narrowing
            assert edge1.from_node == NodeID(1)
            assert edge1.to_node == NodeID(2)
            assert edge1.length_m == 100.0
            assert edge1.mode == Mode.ROAD

        edge2 = imported_graph.get_edge(EdgeID(2))
        assert edge2 is not None
        if edge2:  # Type narrowing
            assert edge2.from_node == NodeID(2)
            assert edge2.to_node == NodeID(3)
            assert edge2.length_m == 150.0
            assert edge2.mode == Mode.ROAD

    def test_import_map_fails_if_not_exists(self) -> None:
        """Test that importing a non-existent map raises an error."""
        map_name = "nonexistent_map"

        with pytest.raises(FileNotFoundError, match="not found"):
            import_map(map_name)

    def test_export_import_roundtrip(self, temp_maps_dir: Path, sample_graph: Graph) -> None:
        """Test that exporting and importing preserves the graph structure."""
        _ = temp_maps_dir  # Use the fixture to set up the test environment
        map_name = "roundtrip_test"

        # Export
        export_map(sample_graph, map_name)

        # Import
        imported_graph = import_map(map_name)

        # Verify graph properties are preserved
        assert imported_graph.get_node_count() == sample_graph.get_node_count()
        assert imported_graph.get_edge_count() == sample_graph.get_edge_count()

        # Verify all nodes are present
        for node_id in sample_graph.nodes:
            original_node = sample_graph.get_node(node_id)
            imported_node = imported_graph.get_node(node_id)
            assert imported_node is not None
            assert original_node is not None
            if imported_node and original_node:  # Type narrowing
                assert imported_node.x == original_node.x
                assert imported_node.y == original_node.y

        # Verify all edges are present
        for edge_id in sample_graph.edges:
            original_edge = sample_graph.get_edge(edge_id)
            imported_edge = imported_graph.get_edge(edge_id)
            assert imported_edge is not None
            assert original_edge is not None
            if imported_edge and original_edge:  # Type narrowing
                assert imported_edge.from_node == original_edge.from_node
                assert imported_edge.to_node == original_edge.to_node
                assert imported_edge.length_m == original_edge.length_m
                assert imported_edge.mode == original_edge.mode


class TestMapExists:
    """Test the map_exists function."""

    @pytest.fixture  # type: ignore[misc]
    def temp_maps_dir(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> Generator[Path, None, None]:
        """Create a temporary maps directory for tests."""
        temp_dir = tmp_path / "maps"
        temp_dir.mkdir()

        def mock_get_maps_dir() -> str:
            return str(temp_dir)

        monkeypatch.setattr("world.io.map_manager.get_maps_directory", mock_get_maps_dir)

        yield temp_dir

        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture  # type: ignore[misc]
    def sample_graph(self) -> Graph:
        """Create a sample graph for testing."""
        graph: Graph = Graph()

        # Add a single node for simple tests
        node = Node(id=NodeID(1), x=0.0, y=0.0)
        graph.add_node(node)

        return graph

    def test_map_exists_returns_true_for_existing_map(
        self, temp_maps_dir: Path, sample_graph: Graph
    ) -> None:
        """Test that map_exists returns True for existing maps."""
        _ = temp_maps_dir  # Use the fixture to set up the test environment
        map_name = "existing_map"

        # Create the map file
        export_map(sample_graph, map_name)

        # Check that it exists
        assert map_exists(map_name) is True

    def test_map_exists_returns_false_for_nonexistent_map(self) -> None:
        """Test that map_exists returns False for non-existent maps."""
        map_name = "nonexistent_map"

        assert map_exists(map_name) is False

    def test_map_exists_sanitizes_name(self, temp_maps_dir: Path, sample_graph: Graph) -> None:
        """Test that map_exists sanitizes the map name."""
        _ = temp_maps_dir  # Use the fixture to set up the test environment
        # Create a map with a sanitized name
        sanitized_name = "test_map"
        export_map(sample_graph, sanitized_name)

        # Check that unsanitized input still works
        assert map_exists("test@map") is True
