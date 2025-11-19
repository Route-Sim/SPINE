"""Node matching criteria for generalized graph search."""

from enum import Enum
from typing import Any, Protocol

from core.buildings.base import Building
from core.types import BuildingID
from world.graph.graph import Graph
from world.graph.node import Node


class NodeCriteria(Protocol):
    """Protocol for node matching criteria in graph searches.

    Implementations define conditions that nodes must satisfy and provide
    caching support for efficient repeated searches.
    """

    def matches(self, node: Node, graph: Graph) -> tuple[bool, Any | None]:
        """Check if a node satisfies the criteria.

        Args:
            node: The node to check
            graph: The graph context (for accessing edges, etc.)

        Returns:
            Tuple of (matches, matched_item) where:
            - matches: True if node satisfies criteria
            - matched_item: The object that satisfied the criteria
              (e.g., Building instance, or the node itself)
        """
        ...

    def cache_key(self) -> str:
        """Generate a unique cache key for this criteria.

        Returns:
            String key that uniquely identifies this criteria configuration
        """
        ...


class LogicalOperator(Enum):
    """Logical operators for combining criteria."""

    AND = "and"
    OR = "or"


class BuildingTypeCriteria:
    """Criteria that matches nodes with buildings of a specific type.

    Returns the first matching building that is not in the exclusion set.
    """

    def __init__(
        self, building_type: type[Building], exclude_buildings: set[BuildingID] | None = None
    ) -> None:
        """Initialize building type criteria.

        Args:
            building_type: Type of building to search for (e.g., Parking, Site)
            exclude_buildings: Set of building IDs to exclude from matches
        """
        self.building_type = building_type
        self.exclude_buildings = exclude_buildings or set()

    def matches(self, node: Node, _graph: Graph) -> tuple[bool, Any | None]:
        """Check if node has a building of the specified type.

        Args:
            node: The node to check
            _graph: The graph context (unused for building checks)

        Returns:
            (True, building) if match found, (False, None) otherwise
        """
        # O(1) lookup by type
        for building in node.get_buildings_by_type(self.building_type):
            if building.id not in self.exclude_buildings:
                return True, building
        return False, None

    def cache_key(self) -> str:
        """Generate cache key from building type.

        Note: Excludes the exclude_buildings set from the key since
        that changes dynamically. Cache lookups will need to filter
        cached results by exclusion set.
        """
        return f"building_type:{self.building_type.__name__}"


class EdgeCountCriteria:
    """Criteria that matches nodes based on their edge count.

    Returns the node itself as the matched item.
    """

    def __init__(self, min_edges: int | None = None, max_edges: int | None = None) -> None:
        """Initialize edge count criteria.

        Args:
            min_edges: Minimum number of edges (inclusive), None for no minimum
            max_edges: Maximum number of edges (inclusive), None for no maximum
        """
        self.min_edges = min_edges
        self.max_edges = max_edges

    def matches(self, node: Node, graph: Graph) -> tuple[bool, Any | None]:
        """Check if node has edge count within specified range.

        Args:
            node: The node to check
            graph: The graph context (for counting edges)

        Returns:
            (True, node) if match found, (False, None) otherwise
        """
        outgoing = len(graph.get_outgoing_edges(node.id))
        incoming = len(graph.get_incoming_edges(node.id))
        total_edges = outgoing + incoming

        if self.min_edges is not None and total_edges < self.min_edges:
            return False, None
        if self.max_edges is not None and total_edges > self.max_edges:
            return False, None

        return True, node

    def cache_key(self) -> str:
        """Generate cache key from edge count constraints."""
        return f"edge_count:min={self.min_edges},max={self.max_edges}"


class CompositeCriteria:
    """Criteria that combines multiple criteria with logical operators.

    Returns the matched items from all criteria as a tuple.
    """

    def __init__(
        self, criteria_list: list[NodeCriteria], operator: LogicalOperator = LogicalOperator.AND
    ) -> None:
        """Initialize composite criteria.

        Args:
            criteria_list: List of criteria to combine
            operator: Logical operator (AND or OR) for combining criteria
        """
        self.criteria_list = criteria_list
        self.operator = operator

    def matches(self, node: Node, graph: Graph) -> tuple[bool, Any | None]:
        """Check if node satisfies the composite criteria.

        Args:
            node: The node to check
            graph: The graph context

        Returns:
            (True, tuple_of_matched_items) if criteria satisfied, (False, None) otherwise
        """
        matched_items = []

        if self.operator == LogicalOperator.AND:
            # All criteria must match
            for criteria in self.criteria_list:
                matches, item = criteria.matches(node, graph)
                if not matches:
                    return False, None
                matched_items.append(item)
            return True, tuple(matched_items)

        else:  # OR
            # At least one criteria must match
            for criteria in self.criteria_list:
                matches, item = criteria.matches(node, graph)
                if matches:
                    matched_items.append(item)

            if matched_items:
                return True, tuple(matched_items)
            return False, None

    def cache_key(self) -> str:
        """Generate cache key from combined criteria keys."""
        sub_keys = [c.cache_key() for c in self.criteria_list]
        return f"composite:{self.operator.value}:({','.join(sub_keys)})"
