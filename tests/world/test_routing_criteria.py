"""Tests for node matching criteria."""

from core.buildings.parking import Parking
from core.buildings.site import Site
from core.types import BuildingID, EdgeID, NodeID
from world.graph.edge import Edge, Mode, RoadClass
from world.graph.graph import Graph
from world.graph.node import Node
from world.routing.criteria import (
    BuildingTypeCriteria,
    CompositeCriteria,
    EdgeCountCriteria,
    LogicalOperator,
)


def test_building_type_criteria_matches() -> None:
    """Test BuildingTypeCriteria matches nodes with correct building type."""
    # Create graph with node
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    parking = Parking(id=BuildingID("p1"), capacity=10)
    node.add_building(parking)
    graph.add_node(node)

    # Create criteria
    criteria = BuildingTypeCriteria(Parking)

    # Test match
    matches, matched_item = criteria.matches(node, graph)
    assert matches is True
    assert matched_item == parking


def test_building_type_criteria_no_match() -> None:
    """Test BuildingTypeCriteria returns False for non-matching buildings."""
    # Create graph with node containing different building type
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    site = Site(id=BuildingID("s1"), name="Site 1", activity_rate=1.0)
    node.add_building(site)
    graph.add_node(node)

    # Create criteria for parking
    criteria = BuildingTypeCriteria(Parking)

    # Test no match
    matches, matched_item = criteria.matches(node, graph)
    assert matches is False
    assert matched_item is None


def test_building_type_criteria_exclude() -> None:
    """Test BuildingTypeCriteria excludes buildings in exclude set."""
    # Create graph with node
    graph = Graph()
    node = Node(id=NodeID(1), x=0.0, y=0.0)
    parking1 = Parking(id=BuildingID("p1"), capacity=10)
    parking2 = Parking(id=BuildingID("p2"), capacity=10)
    node.add_building(parking1)
    node.add_building(parking2)
    graph.add_node(node)

    # Create criteria excluding p1
    criteria = BuildingTypeCriteria(Parking, exclude_buildings={BuildingID("p1")})

    # Test match returns p2
    matches, matched_item = criteria.matches(node, graph)
    assert matches is True
    assert matched_item == parking2


def test_building_type_criteria_cache_key() -> None:
    """Test BuildingTypeCriteria generates consistent cache keys."""
    criteria1 = BuildingTypeCriteria(Parking)
    criteria2 = BuildingTypeCriteria(Parking)
    criteria3 = BuildingTypeCriteria(Site)

    assert criteria1.cache_key() == criteria2.cache_key()
    assert criteria1.cache_key() != criteria3.cache_key()
    assert criteria1.cache_key() == "building_type:Parking"


def test_edge_count_criteria_min_edges() -> None:
    """Test EdgeCountCriteria matches nodes with minimum edge count."""
    # Create graph with 3 edges
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    n3 = Node(id=NodeID(3), x=0.0, y=1.0)
    n4 = Node(id=NodeID(4), x=1.0, y=1.0)
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    graph.add_node(n4)

    # n2 has 3 edges (2 incoming, 1 outgoing)
    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    e2 = Edge(EdgeID(2), NodeID(3), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    e3 = Edge(EdgeID(3), NodeID(2), NodeID(4), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    graph.add_edge(e1)
    graph.add_edge(e2)
    graph.add_edge(e3)

    # Test min_edges=3
    criteria = EdgeCountCriteria(min_edges=3)
    matches, matched_item = criteria.matches(n2, graph)
    assert matches is True
    assert matched_item == n2

    # Test min_edges=4 (should fail)
    criteria = EdgeCountCriteria(min_edges=4)
    matches, matched_item = criteria.matches(n2, graph)
    assert matches is False
    assert matched_item is None


def test_edge_count_criteria_max_edges() -> None:
    """Test EdgeCountCriteria matches nodes with maximum edge count."""
    # Create graph
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    graph.add_node(n1)
    graph.add_node(n2)

    # n1 has 1 outgoing edge
    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    graph.add_edge(e1)

    # Test max_edges=1
    criteria = EdgeCountCriteria(max_edges=1)
    matches, matched_item = criteria.matches(n1, graph)
    assert matches is True
    assert matched_item == n1

    # Test max_edges=0 (should fail)
    criteria = EdgeCountCriteria(max_edges=0)
    matches, matched_item = criteria.matches(n1, graph)
    assert matches is False
    assert matched_item is None


def test_edge_count_criteria_range() -> None:
    """Test EdgeCountCriteria with both min and max."""
    # Create graph
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    n3 = Node(id=NodeID(3), x=0.0, y=1.0)
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    # n2 has 2 edges (1 incoming, 1 outgoing)
    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    e2 = Edge(EdgeID(2), NodeID(2), NodeID(3), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    graph.add_edge(e1)
    graph.add_edge(e2)

    # Test range [2, 3]
    criteria = EdgeCountCriteria(min_edges=2, max_edges=3)
    matches, matched_item = criteria.matches(n2, graph)
    assert matches is True
    assert matched_item == n2


def test_edge_count_criteria_cache_key() -> None:
    """Test EdgeCountCriteria generates unique cache keys."""
    criteria1 = EdgeCountCriteria(min_edges=2)
    criteria2 = EdgeCountCriteria(min_edges=2)
    criteria3 = EdgeCountCriteria(min_edges=3)
    criteria4 = EdgeCountCriteria(max_edges=5)

    assert criteria1.cache_key() == criteria2.cache_key()
    assert criteria1.cache_key() != criteria3.cache_key()
    assert criteria1.cache_key() != criteria4.cache_key()


def test_composite_criteria_and() -> None:
    """Test CompositeCriteria with AND operator."""
    # Create graph with node that has parking and 2 edges
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    n3 = Node(id=NodeID(3), x=0.0, y=1.0)
    parking = Parking(id=BuildingID("p1"), capacity=10)
    n2.add_building(parking)
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    e2 = Edge(EdgeID(2), NodeID(2), NodeID(3), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    graph.add_edge(e1)
    graph.add_edge(e2)

    # Create composite criteria: has parking AND has 2 edges
    criteria = CompositeCriteria(
        [BuildingTypeCriteria(Parking), EdgeCountCriteria(min_edges=2, max_edges=2)],
        operator=LogicalOperator.AND,
    )

    # Test match
    matches, matched_items = criteria.matches(n2, graph)
    assert matches is True
    assert isinstance(matched_items, tuple)
    assert len(matched_items) == 2
    assert matched_items[0] == parking
    assert matched_items[1] == n2


def test_composite_criteria_and_failure() -> None:
    """Test CompositeCriteria AND fails when one criteria doesn't match."""
    # Create graph with node that has parking but only 1 edge
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    parking = Parking(id=BuildingID("p1"), capacity=10)
    n2.add_building(parking)
    graph.add_node(n1)
    graph.add_node(n2)

    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    graph.add_edge(e1)

    # Create composite criteria: has parking AND has 2 edges (n2 has only 1)
    criteria = CompositeCriteria(
        [BuildingTypeCriteria(Parking), EdgeCountCriteria(min_edges=2)],
        operator=LogicalOperator.AND,
    )

    # Test no match
    matches, matched_items = criteria.matches(n2, graph)
    assert matches is False
    assert matched_items is None


def test_composite_criteria_or() -> None:
    """Test CompositeCriteria with OR operator."""
    # Create graph with node that has parking but no edges constraint
    graph = Graph()
    n1 = Node(id=NodeID(1), x=0.0, y=0.0)
    n2 = Node(id=NodeID(2), x=1.0, y=0.0)
    parking = Parking(id=BuildingID("p1"), capacity=10)
    n2.add_building(parking)
    graph.add_node(n1)
    graph.add_node(n2)

    e1 = Edge(EdgeID(1), NodeID(1), NodeID(2), 1000.0, Mode.ROAD, RoadClass.G, 2, 50.0, None)
    graph.add_edge(e1)

    # Create composite criteria: has parking OR has 5 edges (n2 has parking but only 1 edge)
    criteria = CompositeCriteria(
        [BuildingTypeCriteria(Parking), EdgeCountCriteria(min_edges=5)],
        operator=LogicalOperator.OR,
    )

    # Test match (parking matches)
    matches, matched_items = criteria.matches(n2, graph)
    assert matches is True
    assert isinstance(matched_items, tuple)
    assert parking in matched_items


def test_composite_criteria_cache_key() -> None:
    """Test CompositeCriteria generates unique cache keys."""
    criteria1 = CompositeCriteria(
        [BuildingTypeCriteria(Parking), EdgeCountCriteria(min_edges=2)],
        operator=LogicalOperator.AND,
    )
    criteria2 = CompositeCriteria(
        [BuildingTypeCriteria(Parking), EdgeCountCriteria(min_edges=2)],
        operator=LogicalOperator.AND,
    )
    criteria3 = CompositeCriteria(
        [BuildingTypeCriteria(Parking), EdgeCountCriteria(min_edges=2)],
        operator=LogicalOperator.OR,
    )

    assert criteria1.cache_key() == criteria2.cache_key()
    assert criteria1.cache_key() != criteria3.cache_key()
