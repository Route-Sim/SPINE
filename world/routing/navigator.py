"""A* pathfinding service for agent navigation through the graph network."""

import heapq
import math

from core.types import NodeID
from world.graph.graph import Graph


class Navigator:
    """Provides A* pathfinding for agents navigating the graph network."""

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
                # Cost is time: distance / effective_speed
                effective_speed_kph = min(edge.max_speed_kph, max_speed_kph)
                # Convert to time in hours
                edge_cost = edge.length_m / (effective_speed_kph * 1000.0)
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
