from __future__ import annotations

import pytest

from agents.transports.truck import (
    BASE_FUEL_CONSUMPTION_L_PER_100KM,
    BASE_TRUCK_WEIGHT_TONNES,
    CO2_KG_PER_LITER_DIESEL,
    Truck,
)
from core.buildings.gas_station import GasStation
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

    # Entering a building triggers diff (current_building_id is a watch field)
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_building_id"] == str(parking_id)

    # Verify that full serialization includes building
    full = truck.serialize_full()
    assert full["current_building_id"] == str(parking_id)


def test_truck_leave_parking_releases_building() -> None:
    node_id = NodeID(2)
    parking_id = BuildingID("parking-2")
    world, parking = _build_world_with_parking(node_id, parking_id)
    truck = _make_truck(node_id)

    truck.serialize_diff()  # Initial state
    truck.park_in_building(world, parking_id)
    truck.serialize_diff()  # Clear the park diff

    truck.leave_parking(world)
    assert truck.current_building_id is None
    assert AgentID("truck-1") not in parking.current_agents

    # Leaving a building triggers diff (current_building_id is a watch field)
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_building_id"] is None

    # Verify that full serialization reflects the change
    full = truck.serialize_full()
    assert full["current_building_id"] is None


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

    # Fuel fields should also be present
    assert "fuel_tank_capacity_l" in diff
    assert "current_fuel_l" in diff
    assert "co2_emitted_kg" in diff
    assert "is_seeking_gas_station" in diff
    assert "is_fueling" in diff


def test_serialize_diff_only_on_watch_field_changes() -> None:
    """Test that serialize_diff only triggers on watch field changes."""
    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
        driving_time_s=0.0,
        balance_ducats=0.0,
    )

    # First call should return full state
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_node"] == NodeID(1)
    assert diff["driving_time_s"] == 0.0

    # Change only non-watch field (driving_time_s)
    truck.driving_time_s = 3600.0
    diff = truck.serialize_diff()
    assert diff is None  # Should not trigger serialization

    # Change watch field (current_node)
    truck.current_node = NodeID(2)
    diff = truck.serialize_diff()
    assert diff is not None  # Should trigger serialization
    assert diff["current_node"] == NodeID(2)
    assert diff["driving_time_s"] == 3600.0  # Non-watch field included in payload


def test_serialize_diff_includes_all_fields() -> None:
    """Test that serialize_diff payload includes all fields (watch + non-watch)."""
    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
        max_speed_kph=120.0,
        driving_time_s=7200.0,
        resting_time_s=1800.0,
        is_resting=False,
        balance_ducats=500.0,
        risk_factor=0.6,
        is_seeking_parking=True,
        original_destination=NodeID(5),
        fuel_tank_capacity_l=600.0,
        current_fuel_l=300.0,
        co2_emitted_kg=50.0,
    )

    # Trigger serialization by calling for first time
    diff = truck.serialize_diff()
    assert diff is not None

    # Verify all fields are present
    # Watch fields
    assert "current_node" in diff
    assert "current_edge" in diff
    assert "current_speed_kph" in diff
    assert "route" in diff
    assert "route_start_node" in diff
    assert "route_end_node" in diff

    # Non-watch fields
    assert "id" in diff
    assert "kind" in diff
    assert "max_speed_kph" in diff
    assert "current_building_id" in diff

    # Tachograph fields
    assert "driving_time_s" in diff
    assert "resting_time_s" in diff
    assert "is_resting" in diff
    assert "balance_ducats" in diff
    assert "risk_factor" in diff
    assert "is_seeking_parking" in diff
    assert "original_destination" in diff

    # Fuel system fields
    assert "fuel_tank_capacity_l" in diff
    assert "current_fuel_l" in diff
    assert "co2_emitted_kg" in diff
    assert "is_seeking_gas_station" in diff
    assert "is_fueling" in diff

    # Verify values
    assert diff["driving_time_s"] == 7200.0
    assert diff["balance_ducats"] == 500.0
    assert diff["risk_factor"] == 0.6
    assert diff["fuel_tank_capacity_l"] == 600.0
    assert diff["current_fuel_l"] == 300.0
    assert diff["co2_emitted_kg"] == 50.0


def test_serialize_diff_route_changes_trigger_serialization() -> None:
    """Test that route modifications trigger serialization."""
    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
        route=[NodeID(2), NodeID(3)],
        route_start_node=NodeID(1),
        route_end_node=NodeID(3),
    )

    # First call
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["route"] == [NodeID(2), NodeID(3)]

    # No changes - should return None
    diff = truck.serialize_diff()
    assert diff is None

    # Modify route (pop)
    truck.route.pop(0)
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["route"] == [NodeID(3)]

    # No changes - should return None
    diff = truck.serialize_diff()
    assert diff is None

    # Modify route (append)
    truck.route.append(NodeID(4))
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["route"] == [NodeID(3), NodeID(4)]

    # Clear route
    truck.route.clear()
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["route"] == []


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


# Capacity and Package Loading Tests


def _create_world_with_packages() -> World:
    """Create a test world with packages for loading tests."""
    from core.packages.package import Package
    from core.types import DeliveryUrgency, PackageID, Priority, SiteID

    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)

    # Add some test packages with various sizes
    pkg1 = Package(
        id=PackageID("pkg-1"),
        origin_site=SiteID("site-1"),
        destination_site=SiteID("site-2"),
        size=5.0,
        value_currency=100.0,
        priority=Priority.MEDIUM,
        urgency=DeliveryUrgency.STANDARD,
        spawn_tick=0,
        pickup_deadline_tick=3600,
        delivery_deadline_tick=7200,
    )
    pkg2 = Package(
        id=PackageID("pkg-2"),
        origin_site=SiteID("site-1"),
        destination_site=SiteID("site-2"),
        size=10.0,
        value_currency=200.0,
        priority=Priority.HIGH,
        urgency=DeliveryUrgency.EXPRESS,
        spawn_tick=0,
        pickup_deadline_tick=3600,
        delivery_deadline_tick=7200,
    )
    pkg3 = Package(
        id=PackageID("pkg-3"),
        origin_site=SiteID("site-1"),
        destination_site=SiteID("site-2"),
        size=15.0,
        value_currency=300.0,
        priority=Priority.LOW,
        urgency=DeliveryUrgency.STANDARD,
        spawn_tick=0,
        pickup_deadline_tick=3600,
        delivery_deadline_tick=7200,
    )

    world.add_package(pkg1)
    world.add_package(pkg2)
    world.add_package(pkg3)

    return world


def test_truck_default_capacity() -> None:
    """Test that truck has default capacity of 24."""
    truck = Truck(id=AgentID("truck-1"), kind="truck")
    assert truck.capacity == 24.0


def test_truck_custom_capacity() -> None:
    """Test that truck can be created with custom capacity."""
    truck = Truck(id=AgentID("truck-1"), kind="truck", capacity=30.0)
    assert truck.capacity == 30.0


def test_truck_load_package() -> None:
    """Test loading a package onto a truck."""
    from core.types import PackageID

    truck = Truck(id=AgentID("truck-1"), kind="truck")
    pkg_id = PackageID("pkg-1")

    truck.load_package(pkg_id)
    assert pkg_id in truck.loaded_packages
    assert len(truck.loaded_packages) == 1


def test_truck_load_package_duplicate_raises() -> None:
    """Test that loading the same package twice raises an error."""
    from core.types import PackageID

    truck = Truck(id=AgentID("truck-1"), kind="truck")
    pkg_id = PackageID("pkg-1")

    truck.load_package(pkg_id)
    with pytest.raises(ValueError, match="already loaded"):
        truck.load_package(pkg_id)


def test_truck_unload_package() -> None:
    """Test unloading a package from a truck."""
    from core.types import PackageID

    truck = Truck(id=AgentID("truck-1"), kind="truck")
    pkg_id = PackageID("pkg-1")

    truck.load_package(pkg_id)
    truck.unload_package(pkg_id)
    assert pkg_id not in truck.loaded_packages
    assert len(truck.loaded_packages) == 0


def test_truck_unload_package_not_loaded_raises() -> None:
    """Test that unloading a package not on the truck raises an error."""
    from core.types import PackageID

    truck = Truck(id=AgentID("truck-1"), kind="truck")
    pkg_id = PackageID("pkg-1")

    with pytest.raises(ValueError, match="not loaded"):
        truck.unload_package(pkg_id)


def test_truck_get_total_loaded_size() -> None:
    """Test calculating total loaded size."""
    from core.types import PackageID

    world = _create_world_with_packages()
    truck = Truck(id=AgentID("truck-1"), kind="truck", current_node=NodeID(1))

    # Initially empty
    assert truck.get_total_loaded_size(world) == 0.0

    # Load packages
    truck.load_package(PackageID("pkg-1"))  # size=5.0
    assert truck.get_total_loaded_size(world) == 5.0

    truck.load_package(PackageID("pkg-2"))  # size=10.0
    assert truck.get_total_loaded_size(world) == 15.0

    truck.load_package(PackageID("pkg-3"))  # size=15.0
    assert truck.get_total_loaded_size(world) == 30.0


def test_truck_can_load_package_within_capacity() -> None:
    """Test that can_load_package returns True when package fits."""
    from core.types import PackageID

    world = _create_world_with_packages()
    truck = Truck(id=AgentID("truck-1"), kind="truck", capacity=24.0, current_node=NodeID(1))

    # pkg-1 (size=5.0) fits in capacity of 24
    assert truck.can_load_package(world, PackageID("pkg-1")) is True

    # Load pkg-1 and pkg-2 (total 15.0)
    truck.load_package(PackageID("pkg-1"))
    truck.load_package(PackageID("pkg-2"))

    # pkg-3 (size=15.0) would exceed capacity (15 + 15 = 30 > 24)
    assert truck.can_load_package(world, PackageID("pkg-3")) is False


def test_truck_can_load_package_nonexistent_returns_false() -> None:
    """Test that can_load_package returns False for nonexistent package."""
    from core.types import PackageID

    world = _create_world_with_packages()
    truck = Truck(id=AgentID("truck-1"), kind="truck", current_node=NodeID(1))

    assert truck.can_load_package(world, PackageID("nonexistent")) is False


def test_truck_serialize_includes_capacity_and_loaded_packages() -> None:
    """Test that serialization includes capacity and loaded_packages."""
    from core.types import PackageID

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        capacity=30.0,
        current_node=NodeID(1),
    )
    truck.load_package(PackageID("pkg-1"))
    truck.load_package(PackageID("pkg-2"))

    # Test serialize_full
    full = truck.serialize_full()
    assert full["capacity"] == 30.0
    assert full["loaded_packages"] == [PackageID("pkg-1"), PackageID("pkg-2")]

    # Test serialize_diff (first call returns state)
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["capacity"] == 30.0
    assert diff["loaded_packages"] == [PackageID("pkg-1"), PackageID("pkg-2")]


def test_truck_loading_triggers_serialization() -> None:
    """Test that loading or unloading packages triggers serialize_diff."""
    from core.types import PackageID

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
    )

    # First call - establishes baseline
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["loaded_packages"] == []

    # No changes - should return None
    diff = truck.serialize_diff()
    assert diff is None

    # Load a package - should trigger update
    truck.load_package(PackageID("pkg-1"))
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["loaded_packages"] == [PackageID("pkg-1")]

    # No changes - should return None
    diff = truck.serialize_diff()
    assert diff is None

    # Load another package - should trigger update
    truck.load_package(PackageID("pkg-2"))
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["loaded_packages"] == [PackageID("pkg-1"), PackageID("pkg-2")]

    # Unload a package - should trigger update
    truck.unload_package(PackageID("pkg-1"))
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["loaded_packages"] == [PackageID("pkg-2")]


# Fuel System Tests


def _build_world_with_gas_station(
    node_id: NodeID, gas_station_id: BuildingID, capacity: int = 2, cost_factor: float = 1.0
) -> tuple[World, GasStation]:
    """Create a world with a gas station at the specified node."""
    graph = Graph()
    node = Node(id=node_id, x=0.0, y=0.0)
    gas_station = GasStation(id=gas_station_id, capacity=capacity, cost_factor=cost_factor)
    node.add_building(gas_station)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)
    return world, gas_station


def test_truck_default_fuel_values() -> None:
    """Test that truck has default fuel tank capacity and starts full."""
    truck = Truck(id=AgentID("truck-1"), kind="truck")
    assert truck.fuel_tank_capacity_l == 500.0
    assert truck.current_fuel_l == 500.0
    assert truck.co2_emitted_kg == 0.0
    assert truck.is_seeking_gas_station is False
    assert truck.is_fueling is False


def test_truck_get_current_weight_empty() -> None:
    """Test that empty truck weight equals base weight."""
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)

    truck = Truck(id=AgentID("truck-1"), kind="truck", current_node=NodeID(1))
    weight = truck.get_current_weight_tonnes(world)
    assert weight == BASE_TRUCK_WEIGHT_TONNES


def test_truck_fuel_consumption_rate_calculation() -> None:
    """Test fuel consumption rate calculation based on weight."""
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)

    truck = Truck(id=AgentID("truck-1"), kind="truck", current_node=NodeID(1))

    # Empty truck: base consumption
    rate = truck._calculate_fuel_consumption_l_per_km(world)
    expected_rate = BASE_FUEL_CONSUMPTION_L_PER_100KM / 100.0
    assert abs(rate - expected_rate) < 0.001


def test_truck_consumes_fuel_and_emits_co2() -> None:
    """Test that truck consumes fuel and emits CO2 when moving."""
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=NodeID(1),
        fuel_tank_capacity_l=500.0,
        current_fuel_l=500.0,
    )

    initial_fuel = truck.current_fuel_l
    initial_co2 = truck.co2_emitted_kg

    # Simulate traveling 10km
    distance_m = 10000.0
    truck._consume_fuel_and_emit_co2(world, distance_m)

    # Calculate expected values
    consumption_rate = BASE_FUEL_CONSUMPTION_L_PER_100KM / 100.0  # L/km
    expected_fuel_consumed = (distance_m / 1000.0) * consumption_rate
    expected_co2 = expected_fuel_consumed * CO2_KG_PER_LITER_DIESEL

    actual_fuel_consumed = initial_fuel - truck.current_fuel_l
    actual_co2 = truck.co2_emitted_kg - initial_co2

    assert abs(actual_fuel_consumed - expected_fuel_consumed) < 0.01
    assert abs(actual_co2 - expected_co2) < 0.01


def test_truck_should_seek_gas_station_at_low_fuel() -> None:
    """Test that truck seeks gas station when fuel is critically low."""
    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        fuel_tank_capacity_l=500.0,
        current_fuel_l=500.0,
        risk_factor=0.5,
    )

    # At full tank - should not seek
    assert not truck._should_seek_gas_station()

    # At 35% (above threshold) - should not seek
    truck.current_fuel_l = 500.0 * 0.35
    assert not truck._should_seek_gas_station()

    # At 10% (critical) - must seek
    truck.current_fuel_l = 500.0 * 0.10
    assert truck._should_seek_gas_station()

    # At 5% (very low) - must seek
    truck.current_fuel_l = 500.0 * 0.05
    assert truck._should_seek_gas_station()


def test_truck_enter_gas_station() -> None:
    """Test truck can enter a gas station."""
    node_id = NodeID(1)
    gas_station_id = BuildingID("gas-1")
    world, gas_station = _build_world_with_gas_station(node_id, gas_station_id)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=node_id,
    )

    # Get initial diff to establish baseline
    truck.serialize_diff()

    truck.enter_gas_station(world, gas_station_id)

    assert truck.current_building_id == gas_station_id
    assert AgentID("truck-1") in gas_station.current_agents

    # Entering gas station should trigger diff (watch field)
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_building_id"] == str(gas_station_id)


def test_truck_leave_gas_station() -> None:
    """Test truck can leave a gas station."""
    node_id = NodeID(1)
    gas_station_id = BuildingID("gas-1")
    world, gas_station = _build_world_with_gas_station(node_id, gas_station_id)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=node_id,
    )

    # Enter then leave
    truck.enter_gas_station(world, gas_station_id)
    truck.serialize_diff()  # Clear previous state

    truck.leave_gas_station(world)

    assert truck.current_building_id is None
    assert AgentID("truck-1") not in gas_station.current_agents

    # Leaving gas station should trigger diff (watch field)
    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_building_id"] is None


def test_truck_gas_station_respects_capacity() -> None:
    """Test that truck cannot enter full gas station."""
    node_id = NodeID(1)
    gas_station_id = BuildingID("gas-1")
    world, gas_station = _build_world_with_gas_station(node_id, gas_station_id, capacity=1)
    gas_station.enter(AgentID("other-truck"))

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=node_id,
    )

    with pytest.raises(ValueError):
        truck.enter_gas_station(world, gas_station_id)


def test_gas_station_add_revenue() -> None:
    """Test that gas station tracks revenue."""
    gas_station = GasStation(
        id=BuildingID("gas-1"),
        capacity=2,
        cost_factor=1.0,
        balance_ducats=0.0,
    )

    assert gas_station.balance_ducats == 0.0

    gas_station.add_revenue(100.0)
    assert gas_station.balance_ducats == 100.0

    gas_station.add_revenue(50.0)
    assert gas_station.balance_ducats == 150.0


def test_gas_station_serialization_includes_balance() -> None:
    """Test that gas station serialization includes balance."""
    gas_station = GasStation(
        id=BuildingID("gas-1"),
        capacity=2,
        cost_factor=1.1,
        balance_ducats=500.0,
    )

    data = gas_station.to_dict()
    assert "balance_ducats" in data
    assert data["balance_ducats"] == 500.0

    # Test deserialization
    restored = GasStation.from_dict(data)
    assert restored.balance_ducats == 500.0


def test_truck_fueling_process() -> None:
    """Test the complete fueling process including payment."""
    node_id = NodeID(1)
    gas_station_id = BuildingID("gas-1")
    world, gas_station = _build_world_with_gas_station(node_id, gas_station_id, cost_factor=1.0)

    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        current_node=node_id,
        fuel_tank_capacity_l=100.0,
        current_fuel_l=50.0,  # Half tank
        balance_ducats=1000.0,
    )

    # Enter gas station and start fueling
    truck.enter_gas_station(world, gas_station_id)
    truck.is_fueling = True
    truck.fueling_liters_needed = truck.fuel_tank_capacity_l - truck.current_fuel_l  # 50L

    initial_balance = truck.balance_ducats
    initial_station_balance = gas_station.balance_ducats

    # Simulate fueling ticks until complete (50L at ~0.833 L/s = ~60 ticks)
    while truck.is_fueling:
        truck._handle_fueling(world)

    # Verify tank is full
    assert truck.current_fuel_l == truck.fuel_tank_capacity_l

    # Verify no longer fueling
    assert not truck.is_fueling
    assert truck.current_building_id is None

    # Verify payment: truck paid and gas station received
    fuel_price = gas_station.get_fuel_price(world.global_fuel_price)
    expected_cost = 50.0 * fuel_price  # 50 liters * price
    assert truck.balance_ducats == initial_balance - expected_cost
    assert gas_station.balance_ducats == initial_station_balance + expected_cost


def test_truck_find_closest_gas_station() -> None:
    """Test truck finds closest gas station."""
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1000.0, y=0.0)
    n3 = Node(id=NodeID(3), x=2000.0, y=0.0)

    # Gas stations at n2 and n3
    gs2 = GasStation(id=BuildingID("gas-2"), capacity=2, cost_factor=1.0)
    gs3 = GasStation(id=BuildingID("gas-3"), capacity=2, cost_factor=0.9)
    n2.add_building(gs2)
    n3.add_building(gs3)

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    # Connect nodes
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
        length_m=1000.0,
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
    )

    # Find closest gas station
    gas_station_id, route = truck._find_closest_gas_station(world)

    # Should find the closest one (gs2)
    assert gas_station_id == BuildingID("gas-2")
    assert route == [NodeID(1), NodeID(2)]


def test_truck_fuel_serialization_full() -> None:
    """Test that serialize_full includes all fuel fields."""
    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
        fuel_tank_capacity_l=600.0,
        current_fuel_l=300.0,
        co2_emitted_kg=50.0,
        is_seeking_gas_station=True,
        is_fueling=True,
        current_building_id=BuildingID("gas-1"),
    )

    full = truck.serialize_full()

    assert full["fuel_tank_capacity_l"] == 600.0
    assert full["current_fuel_l"] == 300.0
    assert full["co2_emitted_kg"] == 50.0
    assert full["is_seeking_gas_station"] is True
    assert full["is_fueling"] is True
    assert full["current_building_id"] == "gas-1"


def test_truck_stops_when_out_of_fuel() -> None:
    """Test that truck stops moving when out of fuel."""
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
        current_fuel_l=0.0,  # Out of fuel
    )

    initial_progress = truck.edge_progress_m
    truck._move_along_edge(world)

    # Should not have moved
    assert truck.edge_progress_m == initial_progress
    assert truck.current_speed_kph == 0.0

    # Event should have been emitted
    assert len(world._events) == 1
    assert world._events[0]["event_type"] == "out_of_fuel"


def test_truck_estimate_delivery_times_handles_no_route() -> None:
    """Test that _estimate_delivery_times handles infinity gracefully when no route exists."""
    # Create a disconnected graph with two separate nodes
    graph = Graph()
    node1 = Node(id=NodeID(1), x=0.0, y=0.0)
    node2 = Node(id=NodeID(2), x=1000.0, y=1000.0)  # Disconnected node
    graph.add_node(node1)
    graph.add_node(node2)

    # Add sites to the nodes
    from core.buildings.site import Site
    from core.types import SiteID

    site1 = Site(id=SiteID("site-1"), name="Site 1", activity_rate=1.0)
    site2 = Site(id=SiteID("site-2"), name="Site 2", activity_rate=1.0)
    node1.add_building(site1)
    node2.add_building(site2)

    # Create world with navigator
    router = Navigator()
    world = World(graph=graph, router=router, traffic=None, dt_s=1.0)

    # Create truck at node1
    truck = Truck(id=AgentID("truck-1"), kind="truck")
    truck.current_node = NodeID(1)

    # Call _estimate_delivery_times with disconnected nodes
    # This should not raise OverflowError
    est_pickup, est_delivery = truck._estimate_delivery_times(
        world, SiteID("site-1"), SiteID("site-2")
    )

    # Should return large finite values instead of crashing
    assert est_pickup == world.tick + 99999
    assert est_delivery == world.tick + 99999
