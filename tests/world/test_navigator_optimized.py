"""Tests for optimized navigator search methods."""

import pytest

from core.buildings.parking import Parking
from core.types import BuildingID, EdgeID, NodeID
from world.graph.edge import Edge, Mode, RoadClass
from world.graph.graph import Graph
from world.graph.node import Node
from world.routing.criteria import BuildingTypeCriteria, EdgeCountCriteria
from world.routing.navigator import Navigator


def create_linear_graph() -> Graph:
    """Create a simple linear graph: n1 -> n2 -> n3 -> n4.

    Each edge is 1000m at 50 kph.
    """
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    n3 = Node(id=NodeID(3), x=2.0, y=0.0)
    n4 = Node(id=NodeID(4), x=3.0, y=0.0)

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    graph.add_node(n4)

    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    e2 = Edge(EdgeID(2), NodeID(2), NodeID(3), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    e3 = Edge(EdgeID(3), NodeID(3), NodeID(4), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)

    graph.add_edge(e1)
    graph.add_edge(e2)
    graph.add_edge(e3)

    return graph


def test_find_closest_node_with_building() -> None:
    """Test find_closest_node finds nearest node with building."""
    graph = create_linear_graph()

    # Add parking to n3
    parking = Parking(id=BuildingID("p1"), capacity=10)
    graph.nodes[NodeID(3)].add_building(parking)

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # Search from n1 - should find n3
    node_id, matched_item, route = navigator.find_closest_node(NodeID(1), graph, 100.0, criteria)

    assert node_id == NodeID(3)
    assert matched_item == parking
    assert route == [NodeID(1), NodeID(2), NodeID(3)]


def test_find_closest_node_multiple_matches() -> None:
    """Test find_closest_node returns closest when multiple matches exist."""
    graph = create_linear_graph()

    # Add parking to n2 and n4
    parking2 = Parking(id=BuildingID("p2"), capacity=10)
    parking4 = Parking(id=BuildingID("p4"), capacity=10)
    graph.nodes[NodeID(2)].add_building(parking2)
    graph.nodes[NodeID(4)].add_building(parking4)

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # Search from n1 - should find n2 (closer than n4)
    node_id, matched_item, route = navigator.find_closest_node(NodeID(1), graph, 100.0, criteria)

    assert node_id == NodeID(2)
    assert matched_item == parking2
    assert route == [NodeID(1), NodeID(2)]


def test_find_closest_node_with_exclusion() -> None:
    """Test find_closest_node respects building exclusions."""
    graph = create_linear_graph()

    # Add parking to n2 and n3
    parking2 = Parking(id=BuildingID("p2"), capacity=10)
    parking3 = Parking(id=BuildingID("p3"), capacity=10)
    graph.nodes[NodeID(2)].add_building(parking2)
    graph.nodes[NodeID(3)].add_building(parking3)

    navigator = Navigator()
    # Exclude p2
    criteria = BuildingTypeCriteria(Parking, exclude_buildings={BuildingID("p2")})

    # Search from n1 - should skip n2 and find n3
    node_id, matched_item, route = navigator.find_closest_node(NodeID(1), graph, 100.0, criteria)

    assert node_id == NodeID(3)
    assert matched_item == parking3
    assert route == [NodeID(1), NodeID(2), NodeID(3)]


def test_find_closest_node_no_match() -> None:
    """Test find_closest_node returns None when no match found."""
    graph = create_linear_graph()

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # Search from n1 - no parking exists
    node_id, matched_item, route = navigator.find_closest_node(NodeID(1), graph, 100.0, criteria)

    assert node_id is None
    assert matched_item is None
    assert route is None


def test_find_closest_node_start_matches() -> None:
    """Test find_closest_node returns start if it matches."""
    graph = create_linear_graph()

    # Add parking to n1
    parking = Parking(id=BuildingID("p1"), capacity=10)
    graph.nodes[NodeID(1)].add_building(parking)

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # Search from n1 - should immediately return n1
    node_id, matched_item, route = navigator.find_closest_node(NodeID(1), graph, 100.0, criteria)

    assert node_id == NodeID(1)
    assert matched_item == parking
    assert route == [NodeID(1)]


def test_find_closest_node_edge_count_criteria() -> None:
    """Test find_closest_node with edge count criteria."""
    graph = create_linear_graph()

    navigator = Navigator()
    # n2 and n3 have 2 edges each (1 in, 1 out)
    criteria = EdgeCountCriteria(min_edges=2, max_edges=2)

    # Search from n1 - should find n2
    node_id, matched_item, route = navigator.find_closest_node(NodeID(1), graph, 100.0, criteria)

    assert node_id == NodeID(2)
    assert matched_item == graph.nodes[NodeID(2)]
    assert route == [NodeID(1), NodeID(2)]


def test_find_closest_node_caching() -> None:
    """Test find_closest_node caches results."""
    graph = create_linear_graph()

    # Add parking to n3
    parking = Parking(id=BuildingID("p1"), capacity=10)
    graph.nodes[NodeID(3)].add_building(parking)

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # First search - populates cache
    node_id1, _, route1 = navigator.find_closest_node(NodeID(1), graph, 100.0, criteria)

    # Verify cache was populated
    cache_key = (criteria.cache_key(), NodeID(1))
    assert cache_key in navigator._node_cache
    assert len(navigator._node_cache[cache_key]) == 1

    # Second search - should use cache
    node_id2, _, route2 = navigator.find_closest_node(NodeID(1), graph, 100.0, criteria)

    assert node_id1 == node_id2
    assert route1 == route2


def create_waypoint_graph() -> Graph:
    """Create a graph for testing waypoint routing.

    Layout:
          n2 (parking p2)
         /  \\
        n1   n4
         \\  /
          n3 (parking p3)

    Distances: n1->n2 = 1000m, n2->n4 = 1000m
                n1->n3 = 2000m, n3->n4 = 2000m
    """
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=1.0)
    n3 = Node(id=NodeID(3), x=1.0, y=-1.0)
    n4 = Node(id=NodeID(4), x=2.0, y=0.0)

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    graph.add_node(n4)

    # Upper path (shorter): n1 -> n2 -> n4
    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    e2 = Edge(EdgeID(2), NodeID(2), NodeID(4), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)

    # Lower path (longer): n1 -> n3 -> n4
    e3 = Edge(EdgeID(3), NodeID(1), NodeID(3), 2000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    e4 = Edge(EdgeID(4), NodeID(3), NodeID(4), 2000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)

    graph.add_edge(e1)
    graph.add_edge(e2)
    graph.add_edge(e3)
    graph.add_edge(e4)

    return graph


def test_find_closest_node_on_route_prefers_on_path() -> None:
    """Test waypoint search prefers parking on the optimal route."""
    graph = create_waypoint_graph()

    # Add parking to both n2 (on path) and n3 (off path)
    parking2 = Parking(id=BuildingID("p2"), capacity=10)
    parking3 = Parking(id=BuildingID("p3"), capacity=10)
    graph.nodes[NodeID(2)].add_building(parking2)
    graph.nodes[NodeID(3)].add_building(parking3)

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # Search from n1 to n4 - should prefer p2 on n2 (total: 2000m) over p3 on n3 (total: 4000m)
    node_id, matched_item, route = navigator.find_closest_node_on_route(
        NodeID(1), NodeID(4), graph, 100.0, criteria
    )

    assert node_id == NodeID(2)
    assert matched_item == parking2
    assert route == [NodeID(1), NodeID(2)]


def test_find_closest_node_on_route_minimizes_detour() -> None:
    """Test waypoint search minimizes total trip cost."""
    graph = create_waypoint_graph()

    # Add parking only to n3 (off optimal path)
    parking3 = Parking(id=BuildingID("p3"), capacity=10)
    graph.nodes[NodeID(3)].add_building(parking3)

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # Search from n1 to n4 - should find n3 even though it's not on optimal path
    # Total cost: n1->n3 (2000m) + n3->n4 (2000m) = 4000m
    node_id, matched_item, route = navigator.find_closest_node_on_route(
        NodeID(1), NodeID(4), graph, 100.0, criteria
    )

    assert node_id == NodeID(3)
    assert matched_item == parking3
    assert route == [NodeID(1), NodeID(3)]


def test_find_closest_node_on_route_no_path_to_dest() -> None:
    """Test waypoint search handles nodes with no path to destination."""
    # Create disconnected graph
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    n3 = Node(id=NodeID(3), x=2.0, y=0.0)  # Disconnected
    n4 = Node(id=NodeID(4), x=3.0, y=0.0)  # Destination

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    graph.add_node(n4)

    # n1 -> n2, but n3 and n4 are isolated
    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    graph.add_edge(e1)

    # Add parking to n2 (no path to n4)
    parking = Parking(id=BuildingID("p2"), capacity=10)
    graph.nodes[NodeID(2)].add_building(parking)

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # Search from n1 to n4 - should return None (n2 has no path to n4)
    node_id, matched_item, route = navigator.find_closest_node_on_route(
        NodeID(1), NodeID(4), graph, 100.0, criteria
    )

    assert node_id is None
    assert matched_item is None
    assert route is None


def test_find_closest_node_on_route_early_stopping() -> None:
    """Test waypoint search stops early when optimal solution found."""
    graph = create_linear_graph()

    # Add parking to n2 and n4
    parking2 = Parking(id=BuildingID("p2"), capacity=10)
    parking4 = Parking(id=BuildingID("p4"), capacity=10)
    graph.nodes[NodeID(2)].add_building(parking2)
    graph.nodes[NodeID(4)].add_building(parking4)

    navigator = Navigator()
    criteria = BuildingTypeCriteria(Parking)

    # Search from n1 to n4
    # When we find n2: total cost = cost(n1->n2) + cost(n2->n4) = 1000 + 2000 = 3000m
    # When we find n4: total cost = cost(n1->n4) + 0 = 3000 + 0 = 3000m
    # Should pick n2 as it's found first with same cost
    node_id, matched_item, route = navigator.find_closest_node_on_route(
        NodeID(1), NodeID(4), graph, 100.0, criteria
    )

    assert node_id == NodeID(2)
    assert matched_item == parking2


def test_find_closest_node_on_route_with_exclusion() -> None:
    """Test waypoint search respects building exclusions."""
    graph = create_waypoint_graph()

    # Add parking to both n2 and n3
    parking2 = Parking(id=BuildingID("p2"), capacity=10)
    parking3 = Parking(id=BuildingID("p3"), capacity=10)
    graph.nodes[NodeID(2)].add_building(parking2)
    graph.nodes[NodeID(3)].add_building(parking3)

    navigator = Navigator()
    # Exclude p2
    criteria = BuildingTypeCriteria(Parking, exclude_buildings={BuildingID("p2")})

    # Search from n1 to n4 - should skip n2 and find n3
    node_id, matched_item, route = navigator.find_closest_node_on_route(
        NodeID(1), NodeID(4), graph, 100.0, criteria
    )

    assert node_id == NodeID(3)
    assert matched_item == parking3
    assert route == [NodeID(1), NodeID(3)]


def test_reverse_dijkstra() -> None:
    """Test _reverse_dijkstra computes correct distances."""
    graph = create_linear_graph()

    navigator = Navigator()
    dist_to_dest = navigator._reverse_dijkstra(NodeID(4), graph, 100.0)

    # Check that distances are computed correctly
    assert NodeID(4) in dist_to_dest
    assert dist_to_dest[NodeID(4)] == 0.0

    assert NodeID(3) in dist_to_dest
    # n3 -> n4 = 1000m at 50kph = 0.02 hours
    assert dist_to_dest[NodeID(3)] == pytest.approx(0.02, rel=1e-6)

    assert NodeID(2) in dist_to_dest
    # n2 -> n3 -> n4 = 2000m at 50kph = 0.04 hours
    assert dist_to_dest[NodeID(2)] == pytest.approx(0.04, rel=1e-6)

    assert NodeID(1) in dist_to_dest
    # n1 -> n2 -> n3 -> n4 = 3000m at 50kph = 0.06 hours
    assert dist_to_dest[NodeID(1)] == pytest.approx(0.06, rel=1e-6)
