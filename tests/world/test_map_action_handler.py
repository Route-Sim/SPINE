"""Tests for map action handler."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from world.graph.graph import Graph
from world.sim.handlers.base import HandlerContext
from world.sim.handlers.map import MapActionHandler
from world.sim.queues import SignalQueue, SignalType
from world.sim.state import SimulationState
from world.world import World


def _build_context() -> HandlerContext:
    """Create a handler context with a test graph."""
    state = SimulationState()
    # Don't start the simulation - map creation should fail if running

    # Create an empty graph initially
    graph = Graph()

    world = World(graph=graph, router=None, traffic=None)
    signal_queue = SignalQueue()
    logger = logging.getLogger(__name__)
    return HandlerContext(state=state, world=world, signal_queue=signal_queue, logger=logger)


def test_handle_create_includes_buildings_in_signal() -> None:
    """Test that map.created signal includes buildings in graph.nodes."""
    context = _build_context()

    # Create minimal valid parameters for map generation
    params: dict[str, Any] = {
        "map_width": 1000.0,
        "map_height": 1000.0,
        "num_major_centers": 1,
        "minor_per_major": 0.0,
        "center_separation": 500.0,
        "urban_sprawl": 200.0,
        "local_density": 10.0,
        "rural_density": 1.0,
        "intra_connectivity": 0.3,
        "inter_connectivity": 1,
        "arterial_ratio": 0.2,
        "gridness": 0.0,
        "ring_road_prob": 0.0,
        "highway_curviness": 0.0,
        "rural_settlement_prob": 0.0,
        "urban_sites_per_km2": 5.0,
        "rural_sites_per_km2": 1.0,
        "urban_activity_rate_range": [5.0, 10.0],
        "rural_activity_rate_range": [1.0, 5.0],
        "seed": 42,
    }

    # Call handle_create
    MapActionHandler.handle_create(params, context)

    # Verify signal was emitted
    assert not context.signal_queue.empty()
    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.MAP_CREATED.value

    # Verify signal data structure
    # Note: data is now a MapCreatedSignalData DTO (Pydantic model), not a dict
    data = signal.data

    # Convert to dict for easier testing (Pydantic uses model_dump)
    data_dict = data.model_dump() if hasattr(data, "model_dump") else data

    # Verify building statistics fields exist
    assert "generated_sites" in data_dict
    assert "generated_parkings" in data_dict
    assert isinstance(data_dict["generated_sites"], int)
    assert isinstance(data_dict["generated_parkings"], int)
    assert data_dict["generated_sites"] >= 0
    assert data_dict["generated_parkings"] >= 0

    assert "graph" in data_dict
    assert "nodes" in data_dict["graph"]
    assert "edges" in data_dict["graph"]

    # Verify that nodes include buildings array
    nodes = data_dict["graph"]["nodes"]
    assert isinstance(nodes, list)
    assert len(nodes) > 0

    # Check that at least one node has the buildings field
    # (some nodes may have empty buildings arrays, but the field should exist)
    for node in nodes:
        assert "id" in node
        assert "x" in node
        assert "y" in node
        assert "buildings" in node, f"Node {node.get('id')} missing buildings field"
        assert isinstance(node["buildings"], list), f"Node {node.get('id')} buildings is not a list"

    # Verify that if there are sites generated, they appear in buildings
    # Find nodes with buildings
    nodes_with_buildings = [n for n in nodes if len(n["buildings"]) > 0]
    if nodes_with_buildings:
        # Check that buildings have required fields
        for node in nodes_with_buildings:
            for building in node["buildings"]:
                assert "id" in building
                assert "type" in building


def test_handle_create_fails_when_simulation_running() -> None:
    """Test that map creation fails when simulation is running."""
    context = _build_context()
    context.state.start()  # Start simulation

    params: dict[str, Any] = {
        "map_width": 1000.0,
        "map_height": 1000.0,
        "num_major_centers": 1,
        "minor_per_major": 0.0,
        "center_separation": 500.0,
        "urban_sprawl": 200.0,
        "local_density": 10.0,
        "rural_density": 1.0,
        "intra_connectivity": 0.3,
        "inter_connectivity": 1,
        "arterial_ratio": 0.2,
        "gridness": 0.0,
        "ring_road_prob": 0.0,
        "highway_curviness": 0.0,
        "rural_settlement_prob": 0.0,
        "urban_sites_per_km2": 5.0,
        "rural_sites_per_km2": 1.0,
        "urban_activity_rate_range": [5.0, 10.0],
        "rural_activity_rate_range": [1.0, 5.0],
        "seed": 42,
    }

    with pytest.raises(ValueError, match="Cannot create map while simulation is running"):
        MapActionHandler.handle_create(params, context)
