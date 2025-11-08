"""Truck transport agent for autonomous navigation through the graph network."""

import random
from dataclasses import dataclass, field
from typing import Any

from core.messages import Msg
from core.types import AgentID, EdgeID, NodeID
from world.world import World


@dataclass
class Truck:
    """Transport agent that moves through the graph following computed routes.

    The truck maintains position state (current node or edge), speed limits,
    and follows A* computed routes to randomly selected destinations.
    """

    # From AgentBase interface
    id: AgentID
    kind: str  # "truck"
    inbox: list[Msg] = field(default_factory=list)
    outbox: list[Msg] = field(default_factory=list)
    tags: dict[str, Any] = field(default_factory=dict)
    _last_serialized_state: dict[str, Any] = field(default_factory=dict, init=False)

    # Truck-specific fields
    max_speed_kph: float = 100.0  # Maximum speed capability
    current_speed_kph: float = 0.0  # Actual current speed (limited by edge max_speed)
    current_node: NodeID | None = None  # If at a node
    current_edge: EdgeID | None = None  # If on an edge
    edge_progress_m: float = 0.0  # Distance traveled on current edge
    route: list[NodeID] = field(default_factory=list)  # Remaining nodes to visit
    destination: NodeID | None = None  # Current target node

    def perceive(self, world: World) -> None:
        """Optional: pull local info into cached fields.

        Currently a no-op as truck uses world state directly in decide().
        """
        pass

    def decide(self, world: World) -> None:
        """Update truck state: route planning and movement.

        Behavior:
        - If route is empty: pick random destination and compute route
        - If at node with route: enter next edge in route
        - If on edge: update position along edge, transition to node when complete
        """
        # Case 1: Need new route
        if not self.route:
            self._plan_new_route(world)
            return

        # Case 2: At a node, need to enter next edge
        if self.current_node is not None:
            self._enter_next_edge(world)
            return

        # Case 3: On an edge, continue moving
        if self.current_edge is not None:
            self._move_along_edge(world)
            return

    def _plan_new_route(self, world: World) -> None:
        """Pick random destination and compute route using A* navigator."""
        # Get all available nodes except current position
        available_nodes = [node_id for node_id in world.graph.nodes if node_id != self.current_node]

        if not available_nodes:
            # Only one node in graph, nowhere to go
            return

        # Pick random destination
        self.destination = random.choice(available_nodes)

        # Compute route using navigator
        if self.current_node is not None:
            self.route = world.router.find_route(
                self.current_node, self.destination, world.graph, self.max_speed_kph
            )

            # Remove first node (current position) from route
            if self.route and self.route[0] == self.current_node:
                self.route.pop(0)

    def _enter_next_edge(self, world: World) -> None:
        """Transition from current node to next edge in route."""
        if not self.route or self.current_node is None:
            return

        # Get next node in route
        next_node = self.route[0]

        # Find connecting edge
        outgoing_edges = world.graph.get_outgoing_edges(self.current_node)
        connecting_edge = None
        for edge in outgoing_edges:
            if edge.to_node == next_node:
                connecting_edge = edge
                break

        if connecting_edge is None:
            # No edge found, route is invalid - clear it
            self.route = []
            self.destination = None
            return

        # Enter the edge
        self.current_edge = connecting_edge.id
        self.current_node = None
        self.edge_progress_m = 0.0
        # Set speed to minimum of truck max speed and edge max speed
        self.current_speed_kph = min(self.max_speed_kph, connecting_edge.max_speed_kph)

    def _move_along_edge(self, world: World) -> None:
        """Update position along current edge, transition to node when complete."""
        if self.current_edge is None:
            return

        # Get edge details
        edge = world.graph.get_edge(self.current_edge)
        if edge is None:
            # Edge no longer exists, reset state
            self.current_edge = None
            self.route = []
            self.destination = None
            return

        # Calculate distance traveled this tick
        # Convert kph to m/s: kph * 1000 / 3600
        distance_traveled_m = self.current_speed_kph * (1000.0 / 3600.0) * world.dt_s
        self.edge_progress_m += distance_traveled_m

        # Check if edge is complete
        if self.edge_progress_m >= edge.length_m:
            # Arrive at next node
            self.current_node = edge.to_node
            self.current_edge = None
            self.edge_progress_m = 0.0
            self.current_speed_kph = 0.0

            # Remove completed node from route
            if self.route and self.route[0] == self.current_node:
                self.route.pop(0)

            # Check if destination reached
            if self.current_node == self.destination:
                self.destination = None

    def serialize_diff(self) -> dict[str, Any] | None:
        """Return a small dict for UI delta, or None if no changes.

        Only emits updates when node, edge, speed, or route changes.
        Does NOT include edge_progress_m as frontend doesn't need it.
        """
        current_state = {
            "id": self.id,
            "kind": self.kind,
            "max_speed_kph": self.max_speed_kph,
            "current_speed_kph": self.current_speed_kph,
            "current_node": self.current_node,
            "current_edge": self.current_edge,
            "route": self.route.copy(),  # Include route for frontend
        }

        # Compare with last serialized state
        if current_state == self._last_serialized_state:
            return None  # No changes

        # Update last serialized state
        self._last_serialized_state = current_state.copy()
        return current_state

    def serialize_full(self) -> dict[str, Any]:
        """Return complete agent state for state snapshot."""
        return {
            "id": self.id,
            "kind": self.kind,
            "max_speed_kph": self.max_speed_kph,
            "current_speed_kph": self.current_speed_kph,
            "current_node": self.current_node,
            "current_edge": self.current_edge,
            "edge_progress_m": self.edge_progress_m,
            "route": self.route,
            "destination": self.destination,
            "inbox_count": len(self.inbox),
            "outbox_count": len(self.outbox),
            "tags": self.tags.copy(),
        }
