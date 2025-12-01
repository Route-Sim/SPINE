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


# Site creation tests
def test_handle_create_valid_site() -> None:
    """Test successful creation of site building with required parameters."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "name": "Test Warehouse",
        "activity_rate": 5.0,
    }

    BuildingActionHandler.handle_create(params, context)

    # Verify building was added to node
    node = context.world.graph.nodes[NodeID(1)]
    assert len(node.buildings) == 1
    building = node.buildings[0]
    assert building.id == BuildingID("site-1")
    assert hasattr(building, "name")
    assert building.name == "Test Warehouse"
    assert hasattr(building, "activity_rate")
    assert building.activity_rate == 5.0

    # Verify signal was emitted
    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.BUILDING_CREATED.value
    assert signal.data["node_id"] == 1
    assert signal.data["building"]["id"] == "site-1"
    assert signal.data["building"]["name"] == "Test Warehouse"
    assert signal.data["building"]["activity_rate"] == 5.0
    assert signal.data["tick"] == context.state.current_tick


def test_handle_create_site_with_destination_weights() -> None:
    """Test successful creation of site building with optional destination_weights."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "name": "Test Warehouse",
        "activity_rate": 5.0,
        "destination_weights": {
            "site-2": 0.6,
            "site-3": 0.4,
        },
    }

    BuildingActionHandler.handle_create(params, context)

    # Verify building was added to node
    node = context.world.graph.nodes[NodeID(1)]
    assert len(node.buildings) == 1
    building = node.buildings[0]
    assert building.id == BuildingID("site-1")
    assert hasattr(building, "destination_weights")
    assert len(building.destination_weights) == 2
    # Check that destination_weights were properly converted
    from core.types import SiteID

    assert SiteID("site-2") in building.destination_weights
    assert SiteID("site-3") in building.destination_weights
    assert building.destination_weights[SiteID("site-2")] == 0.6
    assert building.destination_weights[SiteID("site-3")] == 0.4


def test_handle_create_site_missing_name() -> None:
    """Test that missing name for site raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "activity_rate": 5.0,
    }

    with pytest.raises(ValueError, match="name is required for site buildings"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_site_missing_activity_rate() -> None:
    """Test that missing activity_rate for site raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "name": "Test Warehouse",
    }

    with pytest.raises(ValueError, match="activity_rate is required for site buildings"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_site_invalid_activity_rate_type() -> None:
    """Test that non-float activity_rate raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "name": "Test Warehouse",
        "activity_rate": "5.0",
    }

    with pytest.raises(ValueError, match="activity_rate must be a float"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_site_invalid_activity_rate_zero() -> None:
    """Test that zero activity_rate raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "name": "Test Warehouse",
        "activity_rate": 0.0,
    }

    with pytest.raises(ValueError, match="activity_rate must be greater than 0"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_site_invalid_activity_rate_negative() -> None:
    """Test that negative activity_rate raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "name": "Test Warehouse",
        "activity_rate": -5.0,
    }

    with pytest.raises(ValueError, match="activity_rate must be greater than 0"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_site_invalid_name_type() -> None:
    """Test that non-string name raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "name": 123,
        "activity_rate": 5.0,
    }

    with pytest.raises(ValueError, match="name must be a string"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_site_invalid_destination_weights_type() -> None:
    """Test that non-dict destination_weights raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "site",
        "building_id": "site-1",
        "node_id": 1,
        "name": "Test Warehouse",
        "activity_rate": 5.0,
        "destination_weights": "invalid",
    }

    with pytest.raises(ValueError, match="destination_weights must be a dictionary"):
        BuildingActionHandler.handle_create(params, context)


# Gas station creation tests
def test_handle_create_valid_gas_station() -> None:
    """Test successful creation of gas station building."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "capacity": 4,
        "cost_factor": 1.15,
    }

    BuildingActionHandler.handle_create(params, context)

    # Verify building was added to node
    node = context.world.graph.nodes[NodeID(1)]
    assert len(node.buildings) == 1
    building = node.buildings[0]
    assert building.id == BuildingID("gas-station-1")
    assert building.TYPE == "gas_station"
    assert hasattr(building, "capacity")
    assert building.capacity == 4
    assert hasattr(building, "cost_factor")
    assert building.cost_factor == 1.15

    # Verify signal was emitted
    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.BUILDING_CREATED.value
    assert signal.data["node_id"] == 1
    assert signal.data["building"]["id"] == "gas-station-1"
    assert signal.data["building"]["type"] == "gas_station"
    assert signal.data["building"]["capacity"] == 4
    assert signal.data["building"]["cost_factor"] == 1.15
    assert signal.data["tick"] == context.state.current_tick


def test_handle_create_gas_station_missing_capacity() -> None:
    """Test that missing capacity for gas_station raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "cost_factor": 1.15,
    }

    with pytest.raises(ValueError, match="capacity is required for gas_station buildings"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_gas_station_missing_cost_factor() -> None:
    """Test that missing cost_factor for gas_station raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "capacity": 4,
    }

    with pytest.raises(ValueError, match="cost_factor is required for gas_station buildings"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_gas_station_invalid_capacity_type() -> None:
    """Test that non-integer capacity raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "capacity": "4",
        "cost_factor": 1.15,
    }

    with pytest.raises(ValueError, match="capacity must be an integer"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_gas_station_invalid_cost_factor_type() -> None:
    """Test that non-float cost_factor raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "capacity": 4,
        "cost_factor": "1.15",
    }

    with pytest.raises(ValueError, match="cost_factor must be a float"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_gas_station_invalid_cost_factor_zero() -> None:
    """Test that zero cost_factor raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "capacity": 4,
        "cost_factor": 0.0,
    }

    with pytest.raises(ValueError, match="cost_factor must be greater than 0"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_gas_station_invalid_cost_factor_negative() -> None:
    """Test that negative cost_factor raises ValueError."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "capacity": 4,
        "cost_factor": -0.5,
    }

    with pytest.raises(ValueError, match="cost_factor must be greater than 0"):
        BuildingActionHandler.handle_create(params, context)


def test_handle_create_gas_station_price_calculation() -> None:
    """Test gas station fuel price calculation."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "capacity": 4,
        "cost_factor": 1.2,  # 20% above base price
    }

    BuildingActionHandler.handle_create(params, context)

    # Verify price calculation
    node = context.world.graph.nodes[NodeID(1)]
    building = node.buildings[0]

    # Test price calculation with global price of 5.0
    global_price = 5.0
    expected_price = 5.0 * 1.2  # 6.0
    actual_price = building.get_fuel_price(global_price)
    assert abs(actual_price - expected_price) < 0.001


def test_handle_create_gas_station_occupancy() -> None:
    """Test gas station agent occupancy functions."""
    context = _build_context()

    params: dict[str, Any] = {
        "building_type": "gas_station",
        "building_id": "gas-station-1",
        "node_id": 1,
        "capacity": 2,
        "cost_factor": 1.0,
    }

    BuildingActionHandler.handle_create(params, context)

    # Verify building was created
    node = context.world.graph.nodes[NodeID(1)]
    building = node.buildings[0]

    # Test occupancy methods
    from core.types import AgentID

    assert building.has_space() is True
    building.enter(AgentID("truck-1"))
    assert building.has_space() is True
    building.enter(AgentID("truck-2"))
    assert building.has_space() is False  # At capacity

    # Test leaving
    building.leave(AgentID("truck-1"))
    assert building.has_space() is True
