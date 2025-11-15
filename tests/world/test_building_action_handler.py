"""Tests for building action handler."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from core.types import BuildingID, NodeID
from world.graph.graph import Graph
from world.graph.node import Node
from world.sim.handlers.base import HandlerContext
from world.sim.handlers.building import BuildingActionHandler
from world.sim.queues import SignalQueue, SignalType
from world.sim.state import SimulationState
from world.world import World


def _build_context() -> HandlerContext:
    """Create a handler context with a test graph."""
    state = SimulationState()
    state.start()

    # Create a graph with a test node
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    graph.add_node(node)

    world = World(graph=graph, router=None, traffic=None)
    signal_queue = SignalQueue()
    logger = logging.getLogger(__name__)
    return HandlerContext(state=state, world=world, signal_queue=signal_queue, logger=logger)


def test_handle_create_missing_building_type() -> None:
    """Test that missing building_type raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_id": "parking-1",
        "node_id": 1,
        "capacity": 10,
    }

    with pytest.raises(ValueError, match="building_type is required"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_invalid_building_type() -> None:
    """Test that invalid building_type raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "warehouse",
        "building_id": "parking-1",
        "node_id": 1,
        "capacity": 10,
    }

    with pytest.raises(ValueError, match="Unsupported building type"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_building_type_not_string() -> None:
    """Test that non-string building_type raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": 123,
        "building_id": "parking-1",
        "node_id": 1,
        "capacity": 10,
    }

    with pytest.raises(ValueError, match="building_type must be a string"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_missing_capacity() -> None:
    """Test that missing capacity for parking raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-1",
        "node_id": 1,
    }

    with pytest.raises(ValueError, match="capacity is required for parking buildings"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_invalid_capacity_type() -> None:
    """Test that non-integer capacity raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-1",
        "node_id": 1,
        "capacity": "10",
    }

    with pytest.raises(ValueError, match="capacity must be an integer"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_missing_building_id() -> None:
    """Test that missing building_id raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "parking",
        "node_id": 1,
        "capacity": 10,
    }

    with pytest.raises(ValueError, match="building_id is required"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_missing_node_id() -> None:
    """Test that missing node_id raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-1",
        "capacity": 10,
    }

    with pytest.raises(ValueError, match="node_id is required"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_nonexistent_node() -> None:
    """Test that creating building on nonexistent node raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-1",
        "node_id": 999,
        "capacity": 10,
    }

    with pytest.raises(ValueError, match="Node 999 does not exist"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_duplicate_building_id() -> None:
    """Test that duplicate building_id raises ValueError."""
    context = _build_context()

    # Create first building
    params1: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-1",
        "node_id": 1,
        "capacity": 10,
    }
    BuildingActionHandler.handle_create(params1, context)

    # Try to create duplicate
    params2: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-1",
        "node_id": 1,
        "capacity": 20,
    }

    with pytest.raises(ValueError, match="Building parking-1 already exists"):
        BuildingActionHandler.handle_create(params2, context)


def test_handle_create_valid_parking() -> None:
    """Test successful creation of parking building."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-1",
        "node_id": 1,
        "capacity": 10,
    }

    BuildingActionHandler.handle_create(params, context)

    # Verify building was added to node
    node = context.world.graph.nodes[NodeID(1)]
    assert len(node.buildings) == 1
    building = node.buildings[0]
    assert building.id == BuildingID("parking-1")
    assert building.TYPE == "parking"
    assert hasattr(building, "capacity")
    assert building.capacity == 10

    # Verify signal was emitted
    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.BUILDING_CREATED.value
    assert signal.data["node_id"] == 1
    assert signal.data["building"]["id"] == "parking-1"
    assert signal.data["building"]["type"] == "parking"
    assert signal.data["building"]["capacity"] == 10
    assert signal.data["tick"] == context.state.current_tick


def test_handle_create_multiple_buildings_different_nodes() -> None:
    """Test creating multiple buildings on different nodes."""
    context = _build_context()

    # Add another node
    node2 = Node(id=NodeID(2), x=10.0, y=10.0)
    context.world.graph.add_node(node2)

    # Create building on node 1
    params1: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-1",
        "node_id": 1,
        "capacity": 10,
    }
    BuildingActionHandler.handle_create(params1, context)

    # Create building on node 2
    params2: dict[str, Any] = {
        "building_type": "parking",
        "building_id": "parking-2",
        "node_id": 2,
        "capacity": 20,
    }
    BuildingActionHandler.handle_create(params2, context)

    # Verify both buildings exist
    node1 = context.world.graph.nodes[NodeID(1)]
    node2 = context.world.graph.nodes[NodeID(2)]
    assert len(node1.buildings) == 1
    assert len(node2.buildings) == 1
    assert node1.buildings[0].id == BuildingID("parking-1")
    assert node2.buildings[0].id == BuildingID("parking-2")
