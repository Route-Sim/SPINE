from __future__ import annotations

import pytest

from agents.transports.truck import Truck
from core.buildings.parking import Parking
from core.types import AgentID, BuildingID, EdgeID, NodeID
from world.graph.edge import Edge, Mode, RoadClass
from world.graph.graph import Graph
from world.graph.node import Node
from world.routing.navigator import Navigator
from world.world import World


def _build_world_with_parking(
    node_id: NodeID, parking_id: BuildingID, capacity: int = 2
) -> tuple[World, Parking]:
    graph = Graph()
    node = Node(id=node_id, x=0.0, y=0.0)
    parking = Parking(id=parking_id, capacity=capacity)
    node.add_building(parking)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)
    return world, parking


def _make_truck(node_id: NodeID | None) -> Truck:
    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
    )
    truck.current_node = node_id
    return truck


def test_truck_parking_registers_building_and_updates_state() -> None:
    node_id = NodeID(1)
    parking_id = BuildingID("parking-1")
    world, parking = _build_world_with_parking(node_id, parking_id)
    truck = _make_truck(node_id)

    initial_state = truck.serialize_diff()
    assert initial_state is not None
    assert initial_state["current_building_id"] is None

    truck.park_in_building(world, parking_id)
    assert truck.current_building_id == parking_id
    assert AgentID("truck-1") in parking.current_agents

    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_building_id"] == str(parking_id)


def test_truck_leave_parking_releases_building() -> None:
    node_id = NodeID(2)
    parking_id = BuildingID("parking-2")
    world, parking = _build_world_with_parking(node_id, parking_id)
    truck = _make_truck(node_id)

    truck.serialize_diff()
    truck.park_in_building(world, parking_id)
    truck.serialize_diff()

    truck.leave_parking(world)
    assert truck.current_building_id is None
    assert AgentID("truck-1") not in parking.current_agents

    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_building_id"] is None


def test_truck_parking_requires_same_node() -> None:
    parking_node = NodeID(3)
    other_node = NodeID(4)
    parking_id = BuildingID("parking-3")
    world, _ = _build_world_with_parking(parking_node, parking_id)

    other = Node(id=other_node, x=1.0, y=1.0)
    world.graph.add_node(other)

    truck = _make_truck(other_node)

    with pytest.raises(ValueError):
        truck.park_in_building(world, parking_id)


def test_truck_parking_respects_capacity() -> None:
    node_id = NodeID(5)
    parking_id = BuildingID("parking-5")
    world, parking = _build_world_with_parking(node_id, parking_id, capacity=1)
    parking.park(AgentID("other-truck"))

    truck = _make_truck(node_id)

    with pytest.raises(ValueError):
        truck.park_in_building(world, parking_id)


# Tachograph System Tests


def test_truck_accumulates_driving_time() -> None:
    """Test that driving time accumulates while truck is on an edge."""
    # Setup world with two connected nodes
    graph = Graph()
    node1 = Node(id=NodeID(1), x=0.0, y=0.0)
    node2 = Node(id=NodeID(2), x=1000.0, y=0.0)
    graph.add_node(node1)
    graph.add_node(node2)
    edge = Edge(
        id=EdgeID(1),
        from_node=NodeID(1),
        to_node=NodeID(2),
        length_m=1000.0,
        mode=Mode.ROAD,
        road_class=RoadClass.G,
        lanes=2,
        max_speed_kph=50.0,
        weight_limit_kg=None,
    )
    graph.add_edge(edge)

    world = World(graph=graph, router=Navigator(), traffic=None, dt_s=1.0)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_edge=EdgeID(1),
        edge_progress_m=0.0,
        current_speed_kph=50.0,
    )

    initial_driving_time = truck.driving_time_s
    truck._move_along_edge(world)
    assert truck.driving_time_s == initial_driving_time + 1.0


def test_calculate_required_rest() -> None:
    """Test rest requirement calculation for different driving times."""
    truck = Truck(id=AgentID("truck-1"), kind="truck")

    # 6 hours driving → 6 hours rest
    truck.driving_time_s = 6.0 * 3600
    required = truck._calculate_required_rest()
    assert abs(required - 6.0 * 3600) < 1.0  # Allow small floating point error

    # 8 hours driving → 10 hours rest
    truck.driving_time_s = 8.0 * 3600
    required = truck._calculate_required_rest()
    assert abs(required - 10.0 * 3600) < 1.0

    # 7 hours driving → 8 hours rest (linear interpolation)
    truck.driving_time_s = 7.0 * 3600
    required = truck._calculate_required_rest()
    assert abs(required - 8.0 * 3600) < 1.0


def test_should_seek_parking_probability() -> None:
    """Test parking search decision probability increases with driving time."""
    truck = Truck(id=AgentID("truck-1"), kind="truck", risk_factor=0.5)

    # Before threshold (7.5 hours with risk 0.5) - should not seek
    truck.driving_time_s = 7.0 * 3600
    decisions = [truck._should_seek_parking() for _ in range(100)]
    assert not any(decisions)  # Should always be False before threshold

    # At 8 hours - should always seek (at or past limit)
    truck.driving_time_s = 8.0 * 3600
    assert truck._should_seek_parking()


def test_apply_tachograph_penalty() -> None:
    """Test penalty amounts for different overtime durations."""
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)

    truck = Truck(id=AgentID("truck-1"), kind="truck", balance_ducats=0.0)

    # 0.5 hours overtime → 100 ducats penalty
    truck.driving_time_s = 8.5 * 3600
    truck._apply_tachograph_penalty(world)
    assert truck.balance_ducats == -100.0

    # 1.5 hours overtime → 200 ducats penalty
    truck.balance_ducats = 0.0
    truck.driving_time_s = 9.5 * 3600
    truck._apply_tachograph_penalty(world)
    assert truck.balance_ducats == -200.0

    # 2.5 hours overtime → 500 ducats penalty
    truck.balance_ducats = 0.0
    truck.driving_time_s = 10.5 * 3600
    truck._apply_tachograph_penalty(world)
    assert truck.balance_ducats == -500.0


def test_risk_adjustment_after_penalty() -> None:
    """Test that risk factor decreases after penalty."""
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)

    truck = Truck(id=AgentID("truck-1"), kind="truck", risk_factor=0.8)
    initial_risk = truck.risk_factor

    # Apply penalty which triggers risk adjustment
    truck.driving_time_s = 9.0 * 3600
    truck._apply_tachograph_penalty(world)

    # Risk should decrease (be more cautious)
    assert truck.risk_factor < initial_risk
    assert 0.0 <= truck.risk_factor <= 1.0


def test_rest_management_workflow() -> None:
    """Test full rest workflow: calculate requirement, rest, and recovery."""
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    parking = Parking(id=BuildingID("parking-1"), capacity=5)
    node.add_building(parking)
    graph.add_node(node)
    world = World(graph=graph, router=Navigator(), traffic=None, dt_s=1.0)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
        driving_time_s=6.0 * 3600,
    )

    # Start resting
    required_rest = truck._calculate_required_rest()
    truck.park_in_building(world, BuildingID("parking-1"))
    truck.is_resting = True
    truck.required_rest_s = required_rest
    truck.resting_time_s = 0.0

    # Rest for required duration
    for _ in range(int(required_rest)):
        truck._handle_resting(world)

    # After required rest, truck should reset
    assert not truck.is_resting
    assert truck.driving_time_s == 0.0
    assert truck.resting_time_s == 0.0


def test_parking_full_scenario() -> None:
    """Test that truck tries alternative parking when first one is full."""
    graph = Graph()
    node1 = Node(id=NodeID(1), x=0.0, y=0.0)
    node2 = Node(id=NodeID(2), x=1000.0, y=0.0)

    # Add full parking at node1
    parking1 = Parking(id=BuildingID("parking-1"), capacity=1)
    parking1.park(AgentID("other-truck"))
    node1.add_building(parking1)

    # Add available parking at node2
    parking2 = Parking(id=BuildingID("parking-2"), capacity=5)
    node2.add_building(parking2)

    graph.add_node(node1)
    graph.add_node(node2)
    edge = Edge(
        id=EdgeID(1),
        from_node=NodeID(1),
        to_node=NodeID(2),
        length_m=1000.0,
        mode=Mode.ROAD,
        road_class=RoadClass.G,
        lanes=2,
        max_speed_kph=50.0,
        weight_limit_kg=None,
    )
    graph.add_edge(edge)

    world = World(graph=graph, router=Navigator(), traffic=None, dt_s=1.0)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
        is_seeking_parking=True,
    )

    # Mark parking1 as tried (full)
    truck._tried_parkings.add(BuildingID("parking-1"))

    # Try to find parking (should skip excluded parking1)
    parking_id, route = truck._find_closest_parking(world)

    # Should find parking2
    assert parking_id == BuildingID("parking-2")
    assert route is not None


def test_tachograph_serialization() -> None:
    """Test that tachograph fields are included in serialization."""
    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        driving_time_s=3600.0,
        resting_time_s=1800.0,
        is_resting=True,
        balance_ducats=100.0,
        risk_factor=0.7,
        is_seeking_parking=True,
    )

    # Full serialization
    full = truck.serialize_full()
    assert full["driving_time_s"] == 3600.0
    assert full["resting_time_s"] == 1800.0
    assert full["is_resting"] is True
    assert full["balance_ducats"] == 100.0
    assert full["risk_factor"] == 0.7
    assert full["is_seeking_parking"] is True

    # Differential serialization
    diff = truck.serialize_diff()
    assert diff is not None
    assert "driving_time_s" in diff
    assert "resting_time_s" in diff
    assert "is_resting" in diff
    assert "balance_ducats" in diff
    assert "risk_factor" in diff


# Waypoint-Aware Parking Search Tests


def test_truck_uses_waypoint_aware_search_with_destination() -> None:
    """Test truck uses waypoint-aware search when it has a destination."""
    # Create graph with two paths to destination
    #      p2
    #     /  \\
    #   n1    n4 (destination)
    #     \\  /
    #      n3
    #       \\
    #        p3
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=1.0)
    n3 = Node(id=NodeID(3), x=1.0, y=-1.0)
    n4 = Node(id=NodeID(4), x=2.0, y=0.0)

    # Add parkings
    parking2 = Parking(id=BuildingID("parking-2"), capacity=5)
    parking3 = Parking(id=BuildingID("parking-3"), capacity=5)
    n2.add_building(parking2)
    n3.add_building(parking3)

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    graph.add_node(n4)

    # Upper path (shorter): n1 -> n2 -> n4
    e1 = Edge(
        id=EdgeID(1),
        from_node=NodeID(1),
        to_node=NodeID(2),
        length_m=1000.0,
        mode=Mode.ROAD,
        road_class=RoadClass.G,
        lanes=2,
        max_speed_kph=50.0,
        weight_limit_kg=None,
    )
    e2 = Edge(
        id=EdgeID(2),
        from_node=NodeID(2),
        to_node=NodeID(4),
        length_m=1000.0,
        mode=Mode.ROAD,
        road_class=RoadClass.G,
        lanes=2,
        max_speed_kph=50.0,
        weight_limit_kg=None,
    )

    # Lower path (longer): n1 -> n3 -> n4
    e3 = Edge(
        id=EdgeID(3),
        from_node=NodeID(1),
        to_node=NodeID(3),
        length_m=2000.0,
        mode=Mode.ROAD,
        road_class=RoadClass.G,
        lanes=2,
        max_speed_kph=50.0,
        weight_limit_kg=None,
    )
    e4 = Edge(
        id=EdgeID(4),
        from_node=NodeID(3),
        to_node=NodeID(4),
        length_m=2000.0,
        mode=Mode.ROAD,
        road_class=RoadClass.G,
        lanes=2,
        max_speed_kph=50.0,
        weight_limit_kg=None,
    )

    graph.add_edge(e1)
    graph.add_edge(e2)
    graph.add_edge(e3)
    graph.add_edge(e4)

    world = World(graph=graph, router=Navigator(), traffic=None, dt_s=1.0)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
        destination=NodeID(4),  # Has active destination
    )

    # Find parking - should prefer parking2 on optimal route (total: 2000m)
    # over parking3 off route (total: 4000m)
    parking_id, route = truck._find_closest_parking(world)

    assert parking_id == BuildingID("parking-2")
    assert route == [NodeID(1), NodeID(2)]


def test_truck_uses_simple_search_without_destination() -> None:
    """Test truck uses simple closest search when it has no destination."""
    # Create graph with two parkings at different distances
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    n3 = Node(id=NodeID(3), x=2.0, y=0.0)

    # Add parkings
    parking2 = Parking(id=BuildingID("parking-2"), capacity=5)
    parking3 = Parking(id=BuildingID("parking-3"), capacity=5)
    n2.add_building(parking2)
    n3.add_building(parking3)

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    e1 = Edge(
        id=EdgeID(1),
        from_node=NodeID(1),
        to_node=NodeID(2),
        length_m=1000.0,
        mode=Mode.ROAD,
        road_class=RoadClass.G,
        lanes=2,
        max_speed_kph=50.0,
        weight_limit_kg=None,
    )
    e2 = Edge(
        id=EdgeID(2),
        from_node=NodeID(2),
        to_node=NodeID(3),
        length_m=2000.0,
        mode=Mode.ROAD,
        road_class=RoadClass.G,
        lanes=2,
        max_speed_kph=50.0,
        weight_limit_kg=None,
    )

    graph.add_edge(e1)
    graph.add_edge(e2)

    world = World(graph=graph, router=Navigator(), traffic=None, dt_s=1.0)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
        destination=None,  # No destination - should use simple search
    )

    # Find parking - should find closest (parking2 at n2)
    parking_id, route = truck._find_closest_parking(world)

    assert parking_id == BuildingID("parking-2")
    assert route == [NodeID(1), NodeID(2)]
