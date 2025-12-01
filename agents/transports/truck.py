"""Truck transport agent for autonomous navigation through the graph network."""

import random
from dataclasses import dataclass, field
from typing import Any

from core.buildings.parking import Parking
from core.messages import Msg
from core.types import AgentID, BuildingID, EdgeID, NodeID, PackageID
from world.sim.dto.truck_dto import TruckStateDTO, TruckWatchFieldsDTO
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
    _last_serialized_watch_state: TruckWatchFieldsDTO | None = field(default=None, init=False)

    # Truck-specific fields
    max_speed_kph: float = 100.0  # Maximum speed capability
    capacity: float = 24.0  # Cargo capacity (unitless, 4-45)
    loaded_packages: list[PackageID] = field(default_factory=list)  # Currently loaded packages
    current_speed_kph: float = 0.0  # Actual current speed (limited by edge max_speed)
    current_node: NodeID | None = None  # If at a node
    current_edge: EdgeID | None = None  # If on an edge
    edge_progress_m: float = 0.0  # Distance traveled on current edge
    route: list[NodeID] = field(default_factory=list)  # Remaining nodes to visit
    destination: NodeID | None = None  # Current target node
    route_start_node: NodeID | None = None  # Origin node for current route
    route_end_node: NodeID | None = None  # Destination node for current route
    current_building_id: BuildingID | None = None  # Parking building the truck occupies
    _parking_node_id: NodeID | None = field(default=None, init=False, repr=False)

    # Tachograph fields
    driving_time_s: float = 0.0  # Accumulated driving time in seconds
    resting_time_s: float = 0.0  # Accumulated rest time in seconds
    is_resting: bool = False  # Whether currently in mandatory rest
    required_rest_s: float = 0.0  # Required rest duration when resting
    balance_ducats: float = 0.0  # Financial balance for penalties
    risk_factor: float = 0.5  # Risk tolerance (0.0-1.0, affects parking search timing)
    is_seeking_parking: bool = False  # Flag for active parking search
    original_destination: NodeID | None = None  # Preserved destination when diverting to parking
    _tried_parkings: set[BuildingID] = field(default_factory=set, init=False, repr=False)

    def perceive(self, world: World) -> None:
        """Optional: pull local info into cached fields.

        Currently a no-op as truck uses world state directly in decide().
        """
        pass

    def decide(self, world: World) -> None:
        """Update truck state: route planning and movement with tachograph management.

        Behavior:
        - Track driving time and enforce rest periods
        - Apply penalties for overtime driving
        - Seek parking when approaching time limits
        - Handle parking full scenarios
        - If route is empty: pick random destination and compute route
        - If at node with route: enter next edge in route
        - If on edge: update position along edge, transition to node when complete
        """
        # Handle resting state (highest priority)
        if self.is_resting:
            self._handle_resting(world)
            return

        # Check for overtime penalties (apply once per violation)
        if self.driving_time_s > 8 * 3600:
            self._apply_tachograph_penalty(world)

        # Decide if should seek parking based on driving time
        if not self.is_seeking_parking and self._should_seek_parking():
            self.is_seeking_parking = True
            self.original_destination = self.destination
            parking_id, route = self._find_closest_parking(world)
            if parking_id and route:
                # Set route to parking
                self.destination = route[-1] if route else None
                self.route_end_node = self.destination
                # Remove first node if it's current position
                if route and self.current_node and route[0] == self.current_node:
                    self.route = route[1:]
                else:
                    self.route = route
            else:
                # No parking found - clear seeking flag and continue
                self.is_seeking_parking = False
                self.original_destination = None

        # Case 1: At a node
        if self.current_node is not None:
            # Handle parking arrival when seeking parking
            if self.is_seeking_parking and not self.route:
                # Try to find parking at current node
                node = world.graph.get_node(self.current_node)
                if node:
                    parked = False
                    # O(1) lookup for parking buildings by type
                    for building in node.get_buildings_by_type(Parking):
                        if building.has_space():
                            try:
                                self.park_in_building(world, building.id)
                                # Successfully parked - start resting
                                self.required_rest_s = self._calculate_required_rest()
                                self.is_resting = True
                                self.resting_time_s = 0.0
                                parked = True
                                break
                            except ValueError:
                                # Parking full, add to tried list
                                self._tried_parkings.add(building.id)

                    if not parked:
                        # Parking full or not found - try next parking
                        parking_id, route = self._find_closest_parking(world)
                        if parking_id and route:
                            self.destination = route[-1] if route else None
                            self.route_end_node = self.destination
                            if route and route[0] == self.current_node:
                                self.route = route[1:]
                            else:
                                self.route = route
                        else:
                            # No more parkings available - give up seeking
                            self.is_seeking_parking = False
                            self.destination = self.original_destination
                            self.original_destination = None
                            self._tried_parkings.clear()
                return

            # Normal behavior: enter next edge or plan route
            if not self.route:
                if not self.is_seeking_parking:
                    self._plan_new_route(world)
                return
            else:
                self._enter_next_edge(world)
                return

        # Case 2: On an edge, continue moving
        if self.current_edge is not None:
            self._move_along_edge(world)
            return

    def _plan_new_route(self, world: World) -> None:
        """Pick random destination and compute route using A* navigator."""
        # Get all available nodes except current position
        available_nodes = [node_id for node_id in world.graph.nodes if node_id != self.current_node]

        if not available_nodes:
            # Only one node in graph, nowhere to go
            self.destination = None
            self.route_start_node = None
            self.route_end_node = None
            return

        # Pick random destination
        self.destination = random.choice(available_nodes)

        self._set_route(world)

    def _set_route(self, world: World) -> None:
        """Compute and persist the current route along with its endpoints."""
        start_node = self.current_node
        destination = self.destination

        self.route_start_node = start_node
        self.route_end_node = destination

        if start_node is None or destination is None:
            self.route = []
            return

        route = world.router.find_route(start_node, destination, world.graph, self.max_speed_kph)

        if route and route[0] == start_node:
            route = route[1:]

        self.route = route

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
            self.route_start_node = None
            self.route_end_node = None
            return

        # Leave parking before departing the node
        if self.current_building_id is not None:
            self.leave_parking(world)

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
            self.route_start_node = None
            self.route_end_node = None
            return

        # Calculate distance traveled this tick
        # Convert kph to m/s: kph * 1000 / 3600
        distance_traveled_m = self.current_speed_kph * (1000.0 / 3600.0) * world.dt_s
        self.edge_progress_m += distance_traveled_m

        # Track driving time (tachograph)
        if not self.is_resting:
            self.driving_time_s += world.dt_s

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
                self.route_start_node = None
                self.route_end_node = None

    def park_in_building(self, world: World, building_id: BuildingID) -> None:
        """Park the truck in the specified parking building on its current node."""
        if self.current_node is None:
            raise ValueError("Truck must be located at a node to park")
        if self.current_building_id is not None:
            raise ValueError(f"Truck is already parked in building {self.current_building_id}")

        parking = self._resolve_parking(world, building_id, self.current_node)
        parking.park(self.id)
        self.current_building_id = building_id
        self._parking_node_id = self.current_node

    def leave_parking(self, world: World) -> None:
        """Release the truck from its currently assigned parking building."""
        if self.current_building_id is None:
            return

        try:
            parking = self._resolve_parking(
                world, self.current_building_id, self.current_node or self._parking_node_id
            )
        except ValueError:
            # Building no longer exists; clear parked state for consistency.
            self.current_building_id = None
            self._parking_node_id = None
            return

        if self.id in parking.current_agents:
            parking.release(self.id)
        self.current_building_id = None
        self._parking_node_id = None

    def _resolve_parking(
        self, world: World, building_id: BuildingID, node_id: NodeID | None
    ) -> Parking:
        """Return the parking instance for the building id scoped to a specific node."""
        target_node_id = node_id or self._parking_node_id
        if target_node_id is None:
            raise ValueError("Unable to resolve parking without node context")

        node = world.graph.get_node(target_node_id)
        if node is None:
            raise ValueError(f"Node {target_node_id} not found in the world graph")

        for building in node.get_buildings():
            if building.id == building_id:
                if isinstance(building, Parking):
                    return building
                raise ValueError(f"Building {building_id} is not a parking facility")

        raise ValueError(f"Parking {building_id} not found on node {target_node_id}")

    def get_total_loaded_size(self, world: World) -> float:
        """Calculate total size of all loaded packages.

        Args:
            world: World instance to look up package sizes

        Returns:
            Total size of loaded packages
        """
        total = 0.0
        for pkg_id in self.loaded_packages:
            package = world.packages.get(pkg_id)
            if package is not None:
                total += package.size
        return total

    def can_load_package(self, world: World, package_id: PackageID) -> bool:
        """Check if a package can be loaded without exceeding capacity.

        Args:
            world: World instance to look up package sizes
            package_id: ID of the package to check

        Returns:
            True if package can be loaded, False otherwise
        """
        package = world.packages.get(package_id)
        if package is None:
            return False

        current_load = self.get_total_loaded_size(world)
        return current_load + package.size <= self.capacity

    def load_package(self, package_id: PackageID) -> None:
        """Add a package to the loaded packages list.

        Note: This does not check capacity - use can_load_package first.

        Args:
            package_id: ID of the package to load

        Raises:
            ValueError: If package is already loaded
        """
        if package_id in self.loaded_packages:
            raise ValueError(f"Package {package_id} is already loaded")
        self.loaded_packages.append(package_id)

    def unload_package(self, package_id: PackageID) -> None:
        """Remove a package from the loaded packages list.

        Args:
            package_id: ID of the package to unload

        Raises:
            ValueError: If package is not loaded
        """
        if package_id not in self.loaded_packages:
            raise ValueError(f"Package {package_id} is not loaded")
        self.loaded_packages.remove(package_id)

    def _calculate_required_rest(self) -> float:
        """Calculate required rest time based on driving time.

        Formula: 6h drive → 6h rest, 8h drive → 10h rest (linear interpolation).
        Mathematically: required_rest = driving_time * (2/3) + (driving_time / (8*3600)) * 4 * 3600

        Returns:
            Required rest time in seconds
        """
        driving_hours = self.driving_time_s / 3600.0
        # Linear interpolation: at 6h need 6h, at 8h need 10h
        # Slope = (10 - 6) / (8 - 6) = 2
        # required_hours = driving_hours + (driving_hours - 6) * 2 if driving_hours >= 6
        # Simplified: required_hours = 2 * driving_hours - 6 for driving_hours >= 6
        # For driving_hours < 6: proportional (1:1 ratio)
        if driving_hours <= 6.0:
            required_hours = driving_hours
        else:
            # Between 6 and 8 hours: linear from 6h rest to 10h rest
            required_hours = 6.0 + (driving_hours - 6.0) * 2.0

        return required_hours * 3600.0

    def _should_seek_parking(self) -> bool:
        """Determine if truck should start seeking parking based on driving time and risk.

        Uses probability-based decision that increases linearly as driving time approaches 8h.
        Higher risk_factor means truck starts looking later.

        Returns:
            True if truck should start seeking parking
        """
        if self.is_resting or self.is_seeking_parking:
            return False

        hours_driven = self.driving_time_s / 3600.0
        # Threshold: 7.0 to 8.0 hours based on risk_factor
        start_threshold = 7.0 + self.risk_factor * 1.0

        if hours_driven < start_threshold:
            return False

        # Linear probability increase from start_threshold to 8.0 hours
        max_hours = 8.0
        if hours_driven >= max_hours:
            # Must seek parking if at or past 8 hours
            return True

        # Probability increases linearly
        probability = (hours_driven - start_threshold) / (max_hours - start_threshold)
        return random.random() < probability

    def _find_closest_parking(self, world: World) -> tuple[BuildingID | None, list[NodeID] | None]:
        """Find the closest available parking using the navigator.

        Uses waypoint-aware search if truck has an active destination, preferring
        parkings "on the way" to minimize total trip cost. Falls back to simple
        closest search if no destination.

        Returns:
            Tuple of (parking_building_id, route) or (None, None) if no parking found
        """
        if self.current_node is None:
            return None, None

        # Import here to avoid circular dependency
        from world.routing.criteria import BuildingTypeCriteria

        # Create criteria for parking search
        criteria = BuildingTypeCriteria(Parking, self._tried_parkings)

        # If truck has a destination, use waypoint-aware search to find parking "on the way"
        if self.destination is not None:
            node_id, matched_item, route = world.router.find_closest_node_on_route(
                self.current_node,
                self.destination,
                world.graph,
                self.max_speed_kph,
                criteria,
            )
        else:
            # No destination - use simple closest search
            node_id, matched_item, route = world.router.find_closest_node(
                self.current_node, world.graph, self.max_speed_kph, criteria
            )

        if node_id is None or matched_item is None or route is None:
            return None, None

        # Extract building ID from matched item (which is the Parking instance)
        parking = matched_item
        return parking.id, route

    def _handle_resting(self, world: World) -> None:
        """Handle truck resting state and recovery.

        While resting:
        - Increment rest time
        - Can plan route once to original destination
        - Cannot move until rest complete
        - When rest complete: reset counters and resume operation
        """
        # Increment rest time
        self.resting_time_s += world.dt_s

        # Plan route to original destination if needed (only once)
        if not self.route and self.original_destination is not None:
            self.destination = self.original_destination
            self._set_route(world)
            # Don't clear original_destination yet, keep it until rest is complete

        # Check if rest is complete
        if self.resting_time_s >= self.required_rest_s:
            # Rest complete - reset tachograph and resume
            self.is_resting = False
            self.driving_time_s = 0.0
            self.resting_time_s = 0.0
            self.required_rest_s = 0.0
            self.is_seeking_parking = False
            self.original_destination = None
            self._tried_parkings.clear()

            # Adjust risk positively (learned to rest on time)
            if self.driving_time_s < 8.0 * 3600:  # Rested before exceeding limit
                self._adjust_risk(penalty=False)

    def _apply_tachograph_penalty(self, world: World) -> None:
        """Apply financial penalty for exceeding driving time limits.

        Penalties (ducats):
        - 0-1 hour overtime: -100
        - 1-2 hours overtime: -200
        - 2+ hours overtime: -500

        Also adjusts risk factor downward as a learning mechanism.
        """
        overtime_s = self.driving_time_s - (8.0 * 3600)
        if overtime_s <= 0:
            return

        overtime_hours = overtime_s / 3600.0

        # Determine penalty amount
        if overtime_hours <= 1.0:
            penalty = 100.0
        elif overtime_hours <= 2.0:
            penalty = 200.0
        else:
            penalty = 500.0

        # Apply penalty
        self.balance_ducats -= penalty

        # Emit penalty event through world
        world.emit_event(
            {
                "type": "agent_event",
                "event_type": "penalized",
                "agent_id": str(self.id),
                "agent_type": "truck",
                "overtime_hours": overtime_hours,
                "penalty_amount": penalty,
                "new_balance": self.balance_ducats,
            }
        )

        # Adjust risk downward (learned to be more cautious)
        self._adjust_risk(penalty=True)

    def _adjust_risk(self, penalty: bool) -> None:
        """Adjust risk factor based on experience.

        Args:
            penalty: True if adjusting after penalty (decrease risk),
                    False if adjusting after successful rest (increase risk)
        """
        if penalty:
            # Decrease risk by 0.5% to 1%
            adjustment = random.uniform(0.99, 0.995)
            self.risk_factor *= adjustment
        else:
            # Increase risk by 0.5% to 1%
            adjustment = random.uniform(1.005, 1.01)
            self.risk_factor *= adjustment

        # Clamp to [0.0, 1.0]
        self.risk_factor = max(0.0, min(1.0, self.risk_factor))

    def serialize_diff(self) -> dict[str, Any] | None:
        """Return a small dict for UI delta, or None if no changes.

        Only emits updates when watch fields change (node, edge, speed, route, route boundary,
        or loaded packages). Watch field changes are detected using TruckWatchFieldsDTO comparison.
        When changes are detected, returns complete state (TruckStateDTO) including tachograph fields.
        """
        # Create watch fields DTO from current state
        current_watch_fields = TruckWatchFieldsDTO(
            current_node=self.current_node,
            current_edge=self.current_edge,
            current_speed_kph=self.current_speed_kph,
            route=tuple(self.route),  # Convert to tuple for immutability
            route_start_node=self.route_start_node,
            route_end_node=self.route_end_node,
            loaded_packages=tuple(self.loaded_packages),  # Convert to tuple for immutability
        )

        # Compare with last watch state
        if current_watch_fields == self._last_serialized_watch_state:
            return None  # No changes to watch fields

        # Watch fields changed - update last state and return complete state
        self._last_serialized_watch_state = current_watch_fields

        # Create complete state DTO
        complete_state = TruckStateDTO(
            id=self.id,
            kind=self.kind,
            max_speed_kph=self.max_speed_kph,
            capacity=self.capacity,
            loaded_packages=list(self.loaded_packages),
            current_speed_kph=self.current_speed_kph,
            current_node=self.current_node,
            current_edge=self.current_edge,
            route=self.route.copy(),  # Return as list for frontend
            route_start_node=self.route_start_node,
            route_end_node=self.route_end_node,
            current_building_id=str(self.current_building_id) if self.current_building_id else None,
            # Tachograph fields
            driving_time_s=self.driving_time_s,
            resting_time_s=self.resting_time_s,
            is_resting=self.is_resting,
            balance_ducats=self.balance_ducats,
            risk_factor=self.risk_factor,
            is_seeking_parking=self.is_seeking_parking,
            original_destination=self.original_destination,
        )

        return complete_state.model_dump()

    def serialize_full(self) -> dict[str, Any]:
        """Return complete agent state for state snapshot."""
        return {
            "id": self.id,
            "kind": self.kind,
            "max_speed_kph": self.max_speed_kph,
            "capacity": self.capacity,
            "loaded_packages": list(self.loaded_packages),
            "current_speed_kph": self.current_speed_kph,
            "current_node": self.current_node,
            "current_edge": self.current_edge,
            "edge_progress_m": self.edge_progress_m,
            "route": self.route,
            "destination": self.destination,
            "route_start_node": self.route_start_node,
            "route_end_node": self.route_end_node,
            "current_building_id": str(self.current_building_id)
            if self.current_building_id
            else None,
            # Tachograph fields
            "driving_time_s": self.driving_time_s,
            "resting_time_s": self.resting_time_s,
            "is_resting": self.is_resting,
            "required_rest_s": self.required_rest_s,
            "balance_ducats": self.balance_ducats,
            "risk_factor": self.risk_factor,
            "is_seeking_parking": self.is_seeking_parking,
            "original_destination": self.original_destination,
            "inbox_count": len(self.inbox),
            "outbox_count": len(self.outbox),
            "tags": self.tags.copy(),
        }
