"""Tests for Node building type lookups and Navigator building search."""

from core.buildings.parking import Parking
from core.buildings.site import Site
from core.types import BuildingID, EdgeID, NodeID, SiteID
from world.graph.edge import Edge, Mode, RoadClass
from world.graph.graph import Graph
from world.graph.node import Node
from world.routing.navigator import Navigator


def test_node_get_buildings_by_type_parking() -> None:
    """Test Node can retrieve Parking buildings by type."""
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    parking1 = Parking(id=BuildingID("parking-1"), capacity=5)
    parking2 = Parking(id=BuildingID("parking-2"), capacity=3)
    site = Site(id=SiteID("site-1"), name="Test Site", activity_rate=10.0)

    node.add_building(parking1)
    node.add_building(site)
    node.add_building(parking2)

    # Get parkings by type
    parkings = node.get_buildings_by_type(Parking)
    assert len(parkings) == 2
    assert parking1 in parkings
    assert parking2 in parkings
    assert site not in parkings


def test_node_get_buildings_by_type_site() -> None:
    """Test Node can retrieve Site buildings by type."""
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    parking = Parking(id=BuildingID("parking-1"), capacity=5)
    site1 = Site(id=SiteID("site-1"), name="Site 1", activity_rate=10.0)
    site2 = Site(id=SiteID("site-2"), name="Site 2", activity_rate=15.0)

    node.add_building(parking)
    node.add_building(site1)
    node.add_building(site2)

    # Get sites by type
    sites = node.get_buildings_by_type(Site)
    assert len(sites) == 2
    assert site1 in sites
    assert site2 in sites
    assert parking not in sites


def test_node_has_building_type_parking() -> None:
    """Test Node can check for Parking type existence."""
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    site = Site(id=SiteID("site-1"), name="Test Site", activity_rate=10.0)

    node.add_building(site)
    assert not node.has_building_type(Parking)
    assert node.has_building_type(Site)

    parking = Parking(id=BuildingID("parking-1"), capacity=5)
    node.add_building(parking)
    assert node.has_building_type(Parking)
    assert node.has_building_type(Site)


def test_node_has_building_type_site() -> None:
    """Test Node can check for Site type existence."""
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    parking = Parking(id=BuildingID("parking-1"), capacity=5)

    node.add_building(parking)
    assert node.has_building_type(Parking)
    assert not node.has_building_type(Site)

    site = Site(id=SiteID("site-1"), name="Test Site", activity_rate=10.0)
    node.add_building(site)
    assert node.has_building_type(Parking)
    assert node.has_building_type(Site)


def test_node_remove_building_updates_type_index() -> None:
    """Test that removing a building updates the type index."""
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    parking1 = Parking(id=BuildingID("parking-1"), capacity=5)
    parking2 = Parking(id=BuildingID("parking-2"), capacity=3)
    site = Site(id=SiteID("site-1"), name="Test Site", activity_rate=10.0)

    node.add_building(parking1)
    node.add_building(parking2)
    node.add_building(site)

    assert len(node.get_buildings_by_type(Parking)) == 2
    assert len(node.get_buildings_by_type(Site)) == 1

    # Remove one parking
    node.remove_building(BuildingID("parking-1"))
    assert len(node.get_buildings_by_type(Parking)) == 1
    assert parking2 in node.get_buildings_by_type(Parking)

    # Remove last parking - type should be cleaned up
    node.remove_building(BuildingID("parking-2"))
    assert len(node.get_buildings_by_type(Parking)) == 0
    assert not node.has_building_type(Parking)
    assert node.has_building_type(Site)


def test_navigator_find_route_to_site() -> None:
    """Test Navigator can find routes to Site buildings."""
    # Create graph with two nodes
    graph = Graph()
    node1 = Node(id=NodeID(1), x=0.0, y=0.0)
    node2 = Node(id=NodeID(2), x=1000.0, y=0.0)

    # Add site to node2
    site = Site(id=SiteID("site-1"), name="Destination Site", activity_rate=10.0)
    node2.add_building(site)

    graph.add_node(node1)
    graph.add_node(node2)

    # Connect nodes
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

    # Find route to site
    navigator = Navigator()
    building_id, route = navigator.find_route_to_building(
        start=NodeID(1),
        graph=graph,
        max_speed_kph=100.0,
        building_type=Site,
        exclude_buildings=set(),
    )

    assert building_id == BuildingID("site-1")
    assert route is not None
    assert route == [NodeID(1), NodeID(2)]


def test_navigator_find_route_to_site_with_exclusion() -> None:
    """Test Navigator excludes specific sites when searching."""
    # Create graph with three nodes
    graph = Graph()
    node1 = Node(id=NodeID(1), x=0.0, y=0.0)
    node2 = Node(id=NodeID(2), x=1000.0, y=0.0)
    node3 = Node(id=NodeID(3), x=2000.0, y=0.0)

    # Add sites to node2 and node3
    site1 = Site(id=SiteID("site-1"), name="Close Site", activity_rate=10.0)
    site2 = Site(id=SiteID("site-2"), name="Far Site", activity_rate=15.0)
    node2.add_building(site1)
    node3.add_building(site2)

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)

    # Connect nodes linearly
    edge1 = Edge(
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
    edge2 = Edge(
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
    graph.add_edge(edge1)
    graph.add_edge(edge2)

    # Find route excluding site1 (should find site2)
    navigator = Navigator()
    building_id, route = navigator.find_route_to_building(
        start=NodeID(1),
        graph=graph,
        max_speed_kph=100.0,
        building_type=Site,
        exclude_buildings={BuildingID("site-1")},
    )

    assert building_id == BuildingID("site-2")
    assert route is not None
    assert route == [NodeID(1), NodeID(2), NodeID(3)]


def test_navigator_find_route_caches_by_building_type() -> None:
    """Test Navigator caches routes separately for different building types."""
    # Create graph with one node that has both parking and site
    graph = Graph()
    node1 = Node(id=NodeID(1), x=0.0, y=0.0)
    node2 = Node(id=NodeID(2), x=1000.0, y=0.0)

    parking = Parking(id=BuildingID("parking-1"), capacity=5)
    site = Site(id=SiteID("site-1"), name="Test Site", activity_rate=10.0)
    node2.add_building(parking)
    node2.add_building(site)

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

    navigator = Navigator()

    # Find parking
    parking_id, parking_route = navigator.find_route_to_building(
        start=NodeID(1),
        graph=graph,
        max_speed_kph=100.0,
        building_type=Parking,
        exclude_buildings=set(),
    )
    assert parking_id == BuildingID("parking-1")

    # Find site
    site_id, site_route = navigator.find_route_to_building(
        start=NodeID(1),
        graph=graph,
        max_speed_kph=100.0,
        building_type=Site,
        exclude_buildings=set(),
    )
    assert site_id == BuildingID("site-1")

    # Both should have same route but different building IDs
    assert parking_route == site_route
    assert parking_id != site_id


def test_navigator_no_buildings_of_type() -> None:
    """Test Navigator returns None when no buildings of requested type exist."""
    graph = Graph()
    node1 = Node(id=NodeID(1), x=0.0, y=0.0)
    node2 = Node(id=NodeID(2), x=1000.0, y=0.0)

    # Add only parking, no sites
    parking = Parking(id=BuildingID("parking-1"), capacity=5)
    node2.add_building(parking)

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

    navigator = Navigator()

    # Try to find site (should return None)
    building_id, route = navigator.find_route_to_building(
        start=NodeID(1),
        graph=graph,
        max_speed_kph=100.0,
        building_type=Site,
        exclude_buildings=set(),
    )

    assert building_id is None
    assert route is None
