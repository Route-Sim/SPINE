"""A* pathfinding service for agent navigation through the graph network."""

import heapq
import math
from typing import Any

from core.buildings.base import Building
from core.types import BuildingID, NodeID
from world.graph.edge import Edge
from world.graph.graph import Graph
from world.routing.criteria import NodeCriteria


class Navigator:
    """Provides A* pathfinding for agents navigating the graph network."""

    def __init__(self) -> None:
        """Initialize navigator with building route cache."""
        # Cache: (building_type, NodeID) -> list of (BuildingID, NodeID, route) sorted by cost
        self._building_cache: dict[
            tuple[type[Building], NodeID], list[tuple[BuildingID, NodeID, list[NodeID]]]
        ] = {}
        # Cache: (criteria_key, NodeID) -> list of (NodeID, matched_item, route, cost) sorted by cost
        self._node_cache: dict[
            tuple[str, NodeID], list[tuple[NodeID, Any, list[NodeID], float]]
        ] = {}

    def find_route(
        self, start: NodeID, goal: NodeID, graph: Graph, max_speed_kph: float
    ) -> list[NodeID]:
        """Find optimal route from start to goal using A* algorithm.

        Args:
            start: Starting node ID
            goal: Destination node ID
            graph: Graph to navigate
            max_speed_kph: Maximum speed of the agent (used for cost calculation)

        Returns:
            List of NodeIDs forming the path from start to goal (inclusive).
            Empty list if no path exists.

        Notes:
            - Cost function: edge.length_m / min(edge.max_speed_kph, max_speed_kph)
            - Heuristic: Euclidean distance / max_speed_kph
            - Time-based routing that respects both edge and agent speed limits
        """
        # Edge case: start equals goal
        if start == goal:
            return [start]

        # Validate nodes exist
        if start not in graph.nodes or goal not in graph.nodes:
            return []

        # Get goal node for heuristic calculation
        goal_node = graph.nodes[goal]

        def heuristic(node_id: NodeID) -> float:
            """Euclidean distance heuristic divided by max speed (time estimate)."""
            node = graph.nodes[node_id]
            dx = node.x - goal_node.x
            dy = node.y - goal_node.y
            distance = math.sqrt(dx * dx + dy * dy)
            # Convert to time estimate (hours)
            return distance / (max_speed_kph * 1000.0)

        # A* data structures
        # Priority queue: (f_score, counter, node_id)
        counter = 0  # Tie-breaker for equal f_scores
        open_set: list[tuple[float, int, NodeID]] = [(heuristic(start), counter, start)]
        counter += 1

        # Track best known cost to reach each node
        g_score: dict[NodeID, float] = {start: 0.0}

        # Track path
        came_from: dict[NodeID, NodeID] = {}

        # Track nodes in open set for efficient membership testing
        open_set_members: set[NodeID] = {start}

        while open_set:
            # Get node with lowest f_score
            current_f, _, current = heapq.heappop(open_set)
            open_set_members.discard(current)

            # Goal reached
            if current == goal:
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            # Explore neighbors
            current_g = g_score[current]
            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.to_node

                # Calculate cost to reach neighbor through current
                edge_cost = self._calculate_edge_cost(edge, max_speed_kph)
                tentative_g = current_g + edge_cost

                # If this path to neighbor is better than any previous one
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    # Update best path to neighbor
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor)

                    # Add to open set if not already there
                    if neighbor not in open_set_members:
                        heapq.heappush(open_set, (f_score, counter, neighbor))
                        counter += 1
                        open_set_members.add(neighbor)

        # No path found
        return []

    def find_route_to_building(
        self,
        start: NodeID,
        graph: Graph,
        max_speed_kph: float,
        building_type: type[Building],
        exclude_buildings: set[BuildingID],
    ) -> tuple[BuildingID | None, list[NodeID] | None]:
        """Find route to the closest building of a specific type.

        Uses optimized single-Dijkstra search with criteria matching.
        Uses cached results for efficiency. Filters out buildings in exclude set.

        Args:
            start: Starting node ID
            graph: Graph to navigate
            max_speed_kph: Maximum speed of the agent
            building_type: Type of building to search for (e.g., Parking, Site)
            exclude_buildings: Set of building IDs to exclude (already tried)

        Returns:
            Tuple of (building_id, route) or (None, None) if no building found
        """
        # Import here to avoid circular dependency
        from world.routing.criteria import BuildingTypeCriteria

        # Create criteria for building type search
        criteria = BuildingTypeCriteria(building_type, exclude_buildings)

        # Use optimized single-Dijkstra search
        node_id, matched_item, route = self.find_closest_node(start, graph, max_speed_kph, criteria)

        if node_id is None or matched_item is None or route is None:
            return None, None

        # Extract building ID from matched item (which is the Building instance)
        building = matched_item
        return building.id, route

    def _calculate_route_cost(
        self, route: list[NodeID], graph: Graph, max_speed_kph: float
    ) -> float:
        """Calculate the time cost of a route in hours.

        Args:
            route: List of node IDs forming the route
            graph: Graph containing the nodes and edges
            max_speed_kph: Maximum speed of the agent

        Returns:
            Total time cost in hours
        """
        total_cost = 0.0
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]

            # Find the edge
            for edge in graph.get_outgoing_edges(from_node):
                if edge.to_node == to_node:
                    edge_cost = self._calculate_edge_cost(edge, max_speed_kph)
                    total_cost += edge_cost
                    break

        return total_cost

    def estimate_travel_time_s(
        self, start: NodeID, goal: NodeID, graph: Graph, max_speed_kph: float
    ) -> float:
        """Estimate travel time from start to goal in seconds.

        Computes the A* route and calculates the total travel time.

        Args:
            start: Starting node ID
            goal: Destination node ID
            graph: Graph to navigate
            max_speed_kph: Maximum speed of the agent

        Returns:
            Estimated travel time in seconds. Returns float('inf') if no route exists.
        """
        route = self.find_route(start, goal, graph, max_speed_kph)
        if not route:
            return float("inf")

        # _calculate_route_cost returns time in hours, convert to seconds
        time_hours = self._calculate_route_cost(route, graph, max_speed_kph)
        return time_hours * 3600.0

    def estimate_route_travel_time_s(
        self, route: list[NodeID], graph: Graph, max_speed_kph: float
    ) -> float:
        """Calculate travel time for an existing route in seconds.

        Useful when the route is already computed and just needs time estimation.

        Args:
            route: List of node IDs forming the route
            graph: Graph containing the nodes and edges
            max_speed_kph: Maximum speed of the agent

        Returns:
            Total travel time in seconds
        """
        time_hours = self._calculate_route_cost(route, graph, max_speed_kph)
        return time_hours * 3600.0

    def find_closest_node(
        self,
        start: NodeID,
        graph: Graph,
        max_speed_kph: float,
        criteria: NodeCriteria,
    ) -> tuple[NodeID | None, Any | None, list[NodeID] | None]:
        """Find the closest node that satisfies the given criteria using Dijkstra.

        Performs single shortest-path tree expansion from start, stopping at the
        first node that matches the criteria.

        Args:
            start: Starting node ID
            graph: Graph to navigate
            max_speed_kph: Maximum speed of the agent
            criteria: Node matching criteria

        Returns:
            Tuple of (node_id, matched_item, route) or (None, None, None) if no match found
            - node_id: The closest matching node
            - matched_item: The object that satisfied the criteria (e.g., Building instance)
            - route: List of NodeIDs from start to node_id (inclusive)

        Complexity:
            O(E log V) in worst case, typically much faster as it stops at first match
        """
        # Validate start node exists
        if start not in graph.nodes:
            return None, None, None

        # Check if start itself matches
        matches, matched_item = criteria.matches(graph.nodes[start], graph)
        if matches:
            return start, matched_item, [start]

        # Check cache first
        cache_key = (criteria.cache_key(), start)
        if cache_key in self._node_cache:
            # Try cached nodes in order of cost
            for node_id, _cached_item, route, _ in self._node_cache[cache_key]:
                # Re-validate the match (criteria might have changed exclude sets)
                matches, matched_item = criteria.matches(graph.nodes[node_id], graph)
                if matches:
                    return node_id, matched_item, route

        # Dijkstra data structures
        # Priority queue: (cost_from_start, counter, node_id)
        counter = 0
        open_set: list[tuple[float, int, NodeID]] = [(0.0, counter, start)]
        counter += 1

        # Track best known cost to reach each node
        cost_from_start: dict[NodeID, float] = {start: 0.0}

        # Track path for reconstruction
        prev: dict[NodeID, NodeID] = {}

        # Track visited nodes
        visited: set[NodeID] = set()

        while open_set:
            # Get node with lowest cost
            current_cost, _, current = heapq.heappop(open_set)

            # Skip if already visited
            if current in visited:
                continue
            visited.add(current)

            # Check if current node matches criteria
            current_node = graph.nodes[current]
            matches, matched_item = criteria.matches(current_node, graph)
            if matches:
                # Found match! Reconstruct path
                path = [current]
                node = current
                while node in prev:
                    node = prev[node]
                    path.append(node)
                path.reverse()

                # Cache this result
                if cache_key not in self._node_cache:
                    self._node_cache[cache_key] = []
                self._node_cache[cache_key].append((current, matched_item, path, current_cost))
                # Sort cache by cost
                self._node_cache[cache_key].sort(key=lambda x: x[3])

                return current, matched_item, path

            # Explore neighbors
            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.to_node

                if neighbor in visited:
                    continue

                # Calculate cost to reach neighbor
                edge_cost = self._calculate_edge_cost(edge, max_speed_kph)
                tentative_cost = current_cost + edge_cost

                # If this path is better than any previous one
                if neighbor not in cost_from_start or tentative_cost < cost_from_start[neighbor]:
                    cost_from_start[neighbor] = tentative_cost
                    prev[neighbor] = current
                    heapq.heappush(open_set, (tentative_cost, counter, neighbor))
                    counter += 1

        # No matching node found
        return None, None, None

    def find_closest_node_on_route(
        self,
        start: NodeID,
        destination: NodeID,
        graph: Graph,
        max_speed_kph: float,
        criteria: NodeCriteria,
    ) -> tuple[NodeID | None, Any | None, list[NodeID] | None]:
        """Find the closest node satisfying criteria that minimizes S→node→destination cost.

        Uses two-phase Dijkstra to find nodes "on the way" from start to destination,
        minimizing total trip cost rather than just distance from start.

        Args:
            start: Starting node ID
            destination: Final destination node ID
            graph: Graph to navigate
            max_speed_kph: Maximum speed of the agent
            criteria: Node matching criteria

        Returns:
            Tuple of (node_id, matched_item, route) or (None, None, None) if no match found
            - node_id: The node minimizing total S→node→dest cost
            - matched_item: The object that satisfied the criteria
            - route: List of NodeIDs from start to node_id (inclusive)

        Complexity:
            O(E log V) for two Dijkstra runs (forward + backward)
        """
        # Validate nodes exist
        if start not in graph.nodes or destination not in graph.nodes:
            return None, None, None

        # Phase A: Reverse Dijkstra from destination
        # Build dist_to_dest[v] = optimal cost from node v to destination
        dist_to_dest = self._reverse_dijkstra(destination, graph, max_speed_kph)

        # Phase B: Forward Dijkstra from start, evaluating total cost S→node→dest
        # Priority queue: (cost_from_start, counter, node_id)
        counter = 0
        open_set: list[tuple[float, int, NodeID]] = [(0.0, counter, start)]
        counter += 1

        # Track best known cost from start
        g_score: dict[NodeID, float] = {start: 0.0}

        # Track path for reconstruction
        prev: dict[NodeID, NodeID] = {}

        # Track visited nodes
        visited: set[NodeID] = set()

        # Track best match found so far
        best_node: NodeID | None = None
        best_matched_item: Any | None = None
        best_total_cost = float("inf")

        # Check if start node matches
        if start in dist_to_dest:
            matches, matched_item = criteria.matches(graph.nodes[start], graph)
            if matches:
                total_cost = g_score[start] + dist_to_dest[start]
                if total_cost < best_total_cost:
                    best_node = start
                    best_matched_item = matched_item
                    best_total_cost = total_cost

        while open_set:
            # Get node with lowest g_score
            current_g, _, current = heapq.heappop(open_set)

            # Early stopping: if current g_score >= best total cost found,
            # remaining nodes can't improve the solution
            if current_g >= best_total_cost:
                break

            # Skip if already visited
            if current in visited:
                continue
            visited.add(current)

            # Check if current node matches criteria and has path to destination
            if current in dist_to_dest:
                current_node = graph.nodes[current]
                matches, matched_item = criteria.matches(current_node, graph)
                if matches:
                    total_cost = current_g + dist_to_dest[current]
                    if total_cost < best_total_cost:
                        best_node = current
                        best_matched_item = matched_item
                        best_total_cost = total_cost

            # Explore neighbors
            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.to_node

                if neighbor in visited:
                    continue

                # Calculate cost from start to neighbor
                edge_cost = self._calculate_edge_cost(edge, max_speed_kph)
                tentative_g = current_g + edge_cost

                # If this path is better than any previous one
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    prev[neighbor] = current
                    heapq.heappush(open_set, (tentative_g, counter, neighbor))
                    counter += 1

        # If no match found, return None
        if best_node is None:
            return None, None, None

        # Reconstruct path from start to best_node
        path = [best_node]
        node = best_node
        while node in prev:
            node = prev[node]
            path.append(node)
        path.reverse()

        return best_node, best_matched_item, path

    def _reverse_dijkstra(
        self, destination: NodeID, graph: Graph, max_speed_kph: float
    ) -> dict[NodeID, float]:
        """Run Dijkstra from destination on reverse graph.

        Computes optimal cost from every reachable node to the destination.

        Args:
            destination: Destination node ID
            graph: Graph to navigate
            max_speed_kph: Maximum speed of the agent

        Returns:
            Dictionary mapping node_id -> cost to reach destination
        """
        # Priority queue: (cost, counter, node_id)
        counter = 0
        open_set: list[tuple[float, int, NodeID]] = [(0.0, counter, destination)]
        counter += 1

        # Track best known cost from each node to destination
        dist_to_dest: dict[NodeID, float] = {destination: 0.0}

        # Track visited nodes
        visited: set[NodeID] = set()

        while open_set:
            current_cost, _, current = heapq.heappop(open_set)

            # Skip if already visited
            if current in visited:
                continue
            visited.add(current)

            # Explore incoming edges (reverse direction)
            for edge in graph.get_incoming_edges(current):
                neighbor = edge.from_node

                if neighbor in visited:
                    continue

                # Calculate cost from neighbor to destination (through current)
                edge_cost = self._calculate_edge_cost(edge, max_speed_kph)
                tentative_cost = current_cost + edge_cost

                # If this path is better than any previous one
                if neighbor not in dist_to_dest or tentative_cost < dist_to_dest[neighbor]:
                    dist_to_dest[neighbor] = tentative_cost
                    heapq.heappush(open_set, (tentative_cost, counter, neighbor))
                    counter += 1

        return dist_to_dest

    def _calculate_edge_cost(self, edge: Edge, max_speed_kph: float) -> float:
        """Calculate the time cost to traverse an edge.

        Args:
            edge: The edge to traverse
            max_speed_kph: Maximum speed of the agent

        Returns:
            Time cost in hours
        """
        effective_speed_kph = min(edge.max_speed_kph, max_speed_kph)
        return edge.length_m / (effective_speed_kph * 1000.0)
