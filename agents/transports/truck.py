"""Truck transport agent for autonomous navigation through the graph network."""

import random
from dataclasses import dataclass, field
from typing import Any, cast

from core.buildings.gas_station import GasStation
from core.buildings.parking import Parking
from core.buildings.site import Site
from core.delivery.task import DeliveryTask
from core.messages import Msg
from core.types import (
    AgentID,
    BuildingID,
    EdgeID,
    NodeID,
    PackageID,
    PackageStatus,
    SiteID,
    TaskStatus,
    TaskType,
)
from world.sim.dto.truck_dto import TruckStateDTO, TruckWatchFieldsDTO
from world.world import World

# Fuel consumption constants
CO2_KG_PER_LITER_DIESEL: float = 2.68  # kg CO2 emitted per liter of diesel burned
BASE_FUEL_CONSUMPTION_L_PER_100KM: float = 25.0  # Base consumption for empty truck
FUEL_CONSUMPTION_FACTOR_PER_TONNE: float = 1.5  # Additional L/100km per tonne of load
FUELING_RATE_L_PER_S: float = 0.833  # ~50 liters per minute (realistic pump rate)
BASE_TRUCK_WEIGHT_TONNES: float = 5.0  # Empty truck weight in tonnes


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
    current_building_id: BuildingID | None = (
        None  # Building the truck occupies (parking or gas station)
    )
    _building_node_id: NodeID | None = field(default=None, init=False, repr=False)

    # Tachograph fields
    driving_time_s: float = 0.0  # Accumulated driving time in seconds
    resting_time_s: float = 0.0  # Accumulated rest time in seconds
    is_resting: bool = False  # Whether currently in mandatory rest
    required_rest_s: float = 0.0  # Required rest duration when resting
    balance_ducats: float = 0.0  # Financial balance for penalties
    risk_factor: float = 0.5  # Risk tolerance (0.0-1.0, affects parking search timing)
    is_seeking_parking: bool = False  # Flag for active parking search (for rest)
    is_seeking_idle_parking: bool = False  # Flag for seeking parking when idle (no tasks)
    original_destination: NodeID | None = None  # Preserved destination when diverting to parking
    _tried_parkings: set[BuildingID] = field(default_factory=set, init=False, repr=False)

    # Fuel system fields
    fuel_tank_capacity_l: float = 500.0  # Maximum fuel tank capacity in liters
    current_fuel_l: float = 500.0  # Current fuel level in liters
    co2_emitted_kg: float = 0.0  # Total CO2 emitted in kg
    is_seeking_gas_station: bool = False  # Flag for active gas station search
    is_fueling: bool = False  # Flag for when truck is at a gas station fueling
    fueling_liters_needed: float = 0.0  # Liters needed to fill tank when fueling started
    _tried_gas_stations: set[BuildingID] = field(default_factory=set, init=False, repr=False)

    # Delivery system fields
    delivery_queue: list[DeliveryTask] = field(default_factory=list)  # Ordered sites to visit
    broker_id: AgentID | None = None  # ID of the broker agent for messaging
    is_loading: bool = False  # Currently loading packages at a site
    is_unloading: bool = False  # Currently unloading packages at a site
    loading_progress_s: float = 0.0  # Time spent loading/unloading
    loading_target_s: float = 0.0  # Total time needed for current operation
    _pending_proposal: dict[str, Any] | None = field(
        default=None, init=False, repr=False
    )  # Current proposal being evaluated

    def perceive(self, world: World) -> None:
        """Optional: pull local info into cached fields.

        Currently a no-op as truck uses world state directly in decide().
        """
        pass

    def get_current_weight_tonnes(self, world: World) -> float:
        """Calculate current weight of truck including load.

        Args:
            world: World instance to look up package weights

        Returns:
            Total weight in tonnes (base weight + cargo weight)
        """
        # Base truck weight
        total_weight = BASE_TRUCK_WEIGHT_TONNES

        # Add weight from loaded packages (for now, packages don't have weight)
        # This can be extended when packages have weight attributes
        for pkg_id in self.loaded_packages:
            package = world.packages.get(pkg_id)
            if package is not None:
                # Assume package size maps to weight (1 unit size = 0.1 tonnes)
                total_weight += package.size * 0.1

        return total_weight

    def _calculate_fuel_consumption_l_per_km(self, world: World) -> float:
        """Calculate fuel consumption rate based on current weight.

        Returns:
            Fuel consumption in liters per kilometer
        """
        weight_tonnes = self.get_current_weight_tonnes(world)
        # Base consumption + additional consumption per tonne of cargo
        cargo_weight = weight_tonnes - BASE_TRUCK_WEIGHT_TONNES
        consumption_per_100km = (
            BASE_FUEL_CONSUMPTION_L_PER_100KM + cargo_weight * FUEL_CONSUMPTION_FACTOR_PER_TONNE
        )
        return consumption_per_100km / 100.0  # Convert to per km

    def _consume_fuel_and_emit_co2(self, world: World, distance_traveled_m: float) -> None:
        """Consume fuel and emit CO2 based on distance traveled.

        Args:
            world: World instance
            distance_traveled_m: Distance traveled in meters this tick
        """
        if distance_traveled_m <= 0:
            return

        distance_km = distance_traveled_m / 1000.0
        fuel_consumption_l_per_km = self._calculate_fuel_consumption_l_per_km(world)
        fuel_consumed_l = distance_km * fuel_consumption_l_per_km

        # Consume fuel
        self.current_fuel_l = max(0.0, self.current_fuel_l - fuel_consumed_l)

        # Calculate and emit CO2
        co2_emitted = fuel_consumed_l * CO2_KG_PER_LITER_DIESEL
        self.co2_emitted_kg += co2_emitted

    def _should_seek_gas_station(self) -> bool:
        """Determine if truck should start seeking a gas station based on fuel level.

        Uses probability-based decision that increases as fuel gets lower.
        Higher risk_factor means truck starts looking later (at lower fuel).

        Returns:
            True if truck should start seeking gas station
        """
        if self.is_fueling or self.is_seeking_gas_station or self.is_resting:
            return False

        # Calculate fuel percentage
        fuel_percentage = self.current_fuel_l / self.fuel_tank_capacity_l

        # Threshold: 30% to 15% based on risk_factor (higher risk = lower threshold)
        threshold = 0.30 - (self.risk_factor * 0.15)

        if fuel_percentage > threshold:
            return False

        # Linear probability increase as fuel drops below threshold
        min_threshold = 0.10  # Must seek at 10% regardless of risk
        if fuel_percentage <= min_threshold:
            return True

        # Probability increases linearly from threshold to min_threshold
        probability = (threshold - fuel_percentage) / (threshold - min_threshold)
        return random.random() < probability

    def decide(self, world: World) -> None:
        """Update truck state: route planning and movement with tachograph management.

        Priority order:
        1. Handle fueling state (highest priority)
        2. Handle resting state
        3. Handle loading/unloading at sites
        4. Handle broker messages (proposals)
        5. Seek gas station/parking when needed
        6. Execute movement based on delivery queue or random routes
        """
        # Handle fueling state (highest priority)
        if self.is_fueling:
            self._handle_fueling(world)
            return

        # Handle resting state (second highest priority)
        if self.is_resting:
            self._handle_resting(world)
            return

        # Handle loading state (at site loading packages)
        if self.is_loading:
            self._handle_loading(world)
            return

        # Handle unloading state (at site unloading packages)
        if self.is_unloading:
            self._handle_unloading(world)
            return

        # Process broker messages (proposals, assignments)
        # If broker messages result in new tasks, clear idle parking state
        had_no_tasks = not self.delivery_queue
        self._handle_broker_messages(world)
        # If we now have tasks and were in idle parking state, clear it
        if had_no_tasks and self.delivery_queue:
            # Clear idle parking seeking flag
            if self.is_seeking_idle_parking:
                self.is_seeking_idle_parking = False
            # Leave parking if we're parked (but not resting)
            if (
                self.current_building_id is not None
                and not self.is_resting
                and not self.is_seeking_parking
            ):
                # We were at idle parking - leave to start working
                self.leave_parking(world)

        # Check for overtime penalties (apply once per violation)
        if self.driving_time_s > 8 * 3600:
            self._apply_tachograph_penalty(world)

        # Decide if should seek gas station based on fuel level (priority over parking)
        if (
            not self.is_seeking_gas_station
            and not self.is_seeking_parking
            and not self.is_seeking_idle_parking
            and self._should_seek_gas_station()
        ):
            self.is_seeking_gas_station = True
            # Clear idle parking if we were seeking it
            if self.is_seeking_idle_parking:
                self.is_seeking_idle_parking = False
                # Leave parking if we're at idle parking
                if self.current_building_id is not None and not self.is_resting:
                    self.leave_parking(world)
            if self.original_destination is None:
                self.original_destination = self.destination
            gas_station_id, route = self._find_closest_gas_station(world)
            if gas_station_id and route:
                self.destination = route[-1] if route else None
                self.route_end_node = self.destination
                if route and self.current_node and route[0] == self.current_node:
                    self.route = route[1:]
                else:
                    self.route = route
            else:
                # No gas station found - clear seeking flag and continue
                self.is_seeking_gas_station = False
                if not self.is_seeking_parking:
                    self.original_destination = None

        # Decide if should seek parking based on driving time
        if (
            not self.is_seeking_parking
            and not self.is_seeking_gas_station
            and not self.is_seeking_idle_parking
            and self._should_seek_parking()
        ):
            self.is_seeking_parking = True
            # Clear idle parking if we were seeking it
            if self.is_seeking_idle_parking:
                self.is_seeking_idle_parking = False
                # Leave parking if we're at idle parking
                if self.current_building_id is not None and not self.is_resting:
                    self.leave_parking(world)
            if self.original_destination is None:
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
                if not self.is_seeking_gas_station:
                    self.original_destination = None

        # Case 1: At a node
        if self.current_node is not None:
            # Handle gas station arrival when seeking gas station
            if (
                self.is_seeking_gas_station
                and not self.route
                and self._try_enter_gas_station(world)
            ):
                return
            # If couldn't enter, fall through to try next gas station or continue

            # Handle parking arrival when seeking parking (for rest)
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

            # Handle idle parking arrival (park but don't rest)
            if self.is_seeking_idle_parking and not self.route:
                # Try to find parking at current node
                node = world.graph.get_node(self.current_node)
                if node:
                    parked = False
                    # O(1) lookup for parking buildings by type
                    for building in node.get_buildings_by_type(Parking):
                        if building.has_space():
                            try:
                                self.park_in_building(world, building.id)
                                # Successfully parked - but don't start resting
                                self.is_seeking_idle_parking = False
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
                            self.is_seeking_idle_parking = False
                            self._tried_parkings.clear()
                return

            # Check if we've arrived at a delivery task site
            if not self.route and self.delivery_queue and self._try_start_site_operation(world):
                return

            # Normal behavior: enter next edge or plan route
            if not self.route:
                if (
                    not self.is_seeking_parking
                    and not self.is_seeking_gas_station
                    and not self.is_seeking_idle_parking
                ):
                    self._plan_next_destination(world)
                return
            else:
                self._enter_next_edge(world)
                return

        # Case 2: On an edge, continue moving
        if self.current_edge is not None:
            self._move_along_edge(world)
            # After moving, check if we just arrived at a node and can continue immediately
            if self.current_node is not None and self.route:
                # Check if this is a stop we need to respect (not just a pass-through node)
                should_stop = False

                # Stop if seeking gas station and arrived at destination
                if self.is_seeking_gas_station and not self.route:
                    should_stop = True

                # Stop if seeking parking (for rest) and arrived at destination
                if self.is_seeking_parking and not self.route:
                    should_stop = True

                # Stop if seeking idle parking and arrived at destination
                if self.is_seeking_idle_parking and not self.route:
                    should_stop = True

                # Stop if we have delivery tasks and this is a task site
                if self.delivery_queue:
                    for task in self.delivery_queue:
                        if task.status == TaskStatus.PENDING:
                            task_node = self._get_site_node(task.site_id, world)
                            if task_node == self.current_node:
                                should_stop = True
                                break

                # If no reason to stop, immediately enter next edge
                if not should_stop:
                    self._enter_next_edge(world)
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

        # Check if out of fuel
        if self.current_fuel_l <= 0:
            # Truck is stranded - stop moving
            self.current_speed_kph = 0.0
            world.emit_event(
                {
                    "type": "agent_event",
                    "event_type": "out_of_fuel",
                    "agent_id": str(self.id),
                    "agent_type": "truck",
                    "edge_id": str(self.current_edge),
                    "edge_progress_m": self.edge_progress_m,
                }
            )
            return

        # Calculate distance traveled this tick
        # Convert kph to m/s: kph * 1000 / 3600
        distance_traveled_m = self.current_speed_kph * (1000.0 / 3600.0) * world.dt_s
        self.edge_progress_m += distance_traveled_m

        # Consume fuel and emit CO2 for this tick
        self._consume_fuel_and_emit_co2(world, distance_traveled_m)

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
        self._building_node_id = self.current_node

    def leave_parking(self, world: World) -> None:
        """Release the truck from its currently assigned parking building."""
        if self.current_building_id is None:
            return

        try:
            parking = self._resolve_parking(
                world, self.current_building_id, self.current_node or self._building_node_id
            )
        except ValueError:
            # Building no longer exists; clear parked state for consistency.
            self.current_building_id = None
            self._building_node_id = None
            return

        if self.id in parking.current_agents:
            parking.release(self.id)
        self.current_building_id = None
        self._building_node_id = None

    def _resolve_parking(
        self, world: World, building_id: BuildingID, node_id: NodeID | None
    ) -> Parking:
        """Return the parking instance for the building id scoped to a specific node."""
        target_node_id = node_id or self._building_node_id
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

    # --- Gas station methods ---

    def enter_gas_station(self, world: World, building_id: BuildingID) -> None:
        """Enter the specified gas station building on the current node.

        Args:
            world: World instance
            building_id: ID of the gas station to enter

        Raises:
            ValueError: If truck is not at a node, already in a building, or gas station full
        """
        if self.current_node is None:
            raise ValueError("Truck must be located at a node to enter gas station")
        if self.current_building_id is not None:
            raise ValueError(f"Truck is already in building {self.current_building_id}")

        gas_station = self._resolve_gas_station(world, building_id, self.current_node)
        gas_station.enter(self.id)
        self.current_building_id = building_id
        self._building_node_id = self.current_node

    def leave_gas_station(self, world: World) -> None:
        """Leave the current gas station.

        Args:
            world: World instance
        """
        if self.current_building_id is None:
            return

        try:
            gas_station = self._resolve_gas_station(
                world, self.current_building_id, self.current_node or self._building_node_id
            )
        except ValueError:
            # Gas station no longer exists; clear state for consistency
            self.current_building_id = None
            self._building_node_id = None
            return

        if self.id in gas_station.current_agents:
            gas_station.leave(self.id)
        self.current_building_id = None
        self._building_node_id = None

    def _resolve_gas_station(
        self, world: World, building_id: BuildingID, node_id: NodeID | None
    ) -> GasStation:
        """Return the gas station instance for the building id scoped to a specific node."""
        target_node_id = node_id or self._building_node_id
        if target_node_id is None:
            raise ValueError("Unable to resolve gas station without node context")

        node = world.graph.get_node(target_node_id)
        if node is None:
            raise ValueError(f"Node {target_node_id} not found in the world graph")

        for building in node.get_buildings():
            if building.id == building_id:
                if isinstance(building, GasStation):
                    return building
                raise ValueError(f"Building {building_id} is not a gas station")

        raise ValueError(f"Gas station {building_id} not found on node {target_node_id}")

    def _find_closest_gas_station(
        self, world: World
    ) -> tuple[BuildingID | None, list[NodeID] | None]:
        """Find the closest available gas station using the navigator.

        Uses waypoint-aware search if truck has an active destination, preferring
        gas stations "on the way" to minimize total trip cost.

        Returns:
            Tuple of (gas_station_building_id, route) or (None, None) if none found
        """
        if self.current_node is None:
            return None, None

        # Import here to avoid circular dependency
        from world.routing.criteria import BuildingTypeCriteria

        # Create criteria for gas station search
        criteria = BuildingTypeCriteria(GasStation, self._tried_gas_stations)

        # If truck has a destination, use waypoint-aware search
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

        # Extract building ID from matched item (which is the GasStation instance)
        gas_station = matched_item
        return gas_station.id, route

    def _try_enter_gas_station(self, world: World) -> bool:
        """Try to enter a gas station at the current node.

        Returns:
            True if successfully entered or waiting, False if should try another
        """
        node = world.graph.get_node(self.current_node)
        if node is None:
            return False

        # Look for gas stations at this node
        for building in node.get_buildings_by_type(GasStation):
            if building.id in self._tried_gas_stations:
                continue

            if building.has_space():
                try:
                    self.enter_gas_station(world, building.id)
                    # Successfully entered - start fueling
                    self.is_fueling = True
                    self.fueling_liters_needed = self.fuel_tank_capacity_l - self.current_fuel_l
                    return True
                except ValueError:
                    # Gas station full (race condition), add to tried list
                    self._tried_gas_stations.add(building.id)
            else:
                # Gas station is full - wait here
                # Unlike parking, we wait instead of looking for another
                return True

        # No gas station found or all tried - try next gas station
        gas_station_id, route = self._find_closest_gas_station(world)
        if gas_station_id and route:
            self.destination = route[-1] if route else None
            self.route_end_node = self.destination
            if route and route[0] == self.current_node:
                self.route = route[1:]
            else:
                self.route = route
            return False
        else:
            # No more gas stations available - give up seeking
            self.is_seeking_gas_station = False
            self.destination = self.original_destination
            if not self.is_seeking_parking:
                self.original_destination = None
            self._tried_gas_stations.clear()
            return False

    def _handle_fueling(self, world: World) -> None:
        """Handle truck fueling state and completion.

        While fueling:
        - Increment fuel level based on pump rate
        - When complete: calculate cost, transfer money, leave gas station
        """
        if self.current_building_id is None:
            # Not at a gas station - abort fueling
            self.is_fueling = False
            return

        # Calculate fuel pumped this tick
        fuel_pumped = FUELING_RATE_L_PER_S * world.dt_s

        # Check if fueling is complete
        fuel_needed = self.fuel_tank_capacity_l - self.current_fuel_l
        if fuel_pumped >= fuel_needed:
            # Complete fueling
            fuel_pumped = fuel_needed
            self.current_fuel_l = self.fuel_tank_capacity_l

            # Calculate and apply cost
            try:
                gas_station = self._resolve_gas_station(
                    world,
                    self.current_building_id,
                    self.current_node or self._building_node_id,
                )
                fuel_price = gas_station.get_fuel_price(world.global_fuel_price)
                total_cost = self.fueling_liters_needed * fuel_price

                # Transfer money: truck pays, gas station receives
                self.balance_ducats -= total_cost
                gas_station.add_revenue(total_cost)

                # Emit fueling complete event
                world.emit_event(
                    {
                        "type": "agent_event",
                        "event_type": "fueling_complete",
                        "agent_id": str(self.id),
                        "agent_type": "truck",
                        "gas_station_id": str(self.current_building_id),
                        "liters_fueled": self.fueling_liters_needed,
                        "fuel_price_per_liter": fuel_price,
                        "total_cost": total_cost,
                        "new_balance": self.balance_ducats,
                    }
                )
            except ValueError:
                # Gas station no longer exists - free fuel!
                pass

            # Leave gas station
            self.leave_gas_station(world)

            # Reset fueling state
            self.is_fueling = False
            self.fueling_liters_needed = 0.0
            self.is_seeking_gas_station = False
            self._tried_gas_stations.clear()

            # Restore original destination
            if self.original_destination is not None:
                self.destination = self.original_destination
                if not self.is_seeking_parking:
                    self.original_destination = None
                self._set_route(world)
        else:
            # Continue fueling
            self.current_fuel_l += fuel_pumped

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

    # --- Delivery system methods ---

    def _handle_broker_messages(self, world: World) -> None:
        """Process messages from broker (proposals, assignments)."""
        for msg in self.inbox:
            if msg.typ == "proposal":
                self._handle_proposal(msg, world)
            elif msg.typ == "assignment_confirmed":
                self._handle_assignment_confirmation(msg, world)

        # Clear inbox after processing
        self.inbox = []

    def _handle_proposal(self, msg: Msg, world: World) -> None:
        """Handle a pickup proposal from the broker.

        Evaluates whether the truck can feasibly pick up and deliver the package
        within the deadlines, considering current load, route, and driving time.
        """
        body = msg.body
        package_id = PackageID(body.get("package_id", ""))
        origin_site_id = SiteID(body.get("origin_site_id", ""))
        destination_site_id = SiteID(body.get("destination_site_id", ""))
        package_size = float(body.get("package_size", 0))
        pickup_deadline_tick = int(body.get("pickup_deadline_tick", 0))
        delivery_deadline_tick = int(body.get("delivery_deadline_tick", 0))

        # Store broker ID for future communication
        self.broker_id = msg.src

        # Check if we can accept this proposal
        can_accept, rejection_reason = self._evaluate_proposal(
            world,
            package_id,
            origin_site_id,
            destination_site_id,
            package_size,
            pickup_deadline_tick,
            delivery_deadline_tick,
        )

        if can_accept:
            # Calculate estimated times
            est_pickup_tick, est_delivery_tick = self._estimate_delivery_times(
                world, origin_site_id, destination_site_id
            )

            # Send acceptance
            response = Msg(
                src=self.id,
                dst=msg.src,
                typ="accept",
                body={
                    "package_id": str(package_id),
                    "estimated_pickup_tick": est_pickup_tick,
                    "estimated_delivery_tick": est_delivery_tick,
                },
            )
        else:
            # Send rejection
            response = Msg(
                src=self.id,
                dst=msg.src,
                typ="reject",
                body={
                    "package_id": str(package_id),
                    "rejection_reason": rejection_reason,
                },
            )

        self.outbox.append(response)

    def _evaluate_proposal(
        self,
        world: World,
        _package_id: PackageID,  # Reserved for future logging/tracking
        origin_site_id: SiteID,
        destination_site_id: SiteID,
        package_size: float,
        pickup_deadline_tick: int,
        delivery_deadline_tick: int,
    ) -> tuple[bool, str | None]:
        """Evaluate if the truck can accept a pickup proposal.

        Returns:
            Tuple of (can_accept, rejection_reason)
        """
        # Check capacity
        current_load = self.get_total_loaded_size(world)
        if current_load + package_size > self.capacity:
            return False, "insufficient_capacity"

        # Estimate pickup and delivery times
        est_pickup_tick, est_delivery_tick = self._estimate_delivery_times(
            world, origin_site_id, destination_site_id
        )

        # Check if we can make the pickup deadline
        if est_pickup_tick > pickup_deadline_tick:
            return False, "cannot_meet_pickup_deadline"

        # Check if we can make the delivery deadline
        if est_delivery_tick > delivery_deadline_tick:
            return False, "cannot_meet_delivery_deadline"

        # Check driving time constraints
        # Estimate driving time needed (rough estimate)
        driving_needed_s = (est_delivery_tick - world.tick) * world.dt_s
        potential_driving = self.driving_time_s + driving_needed_s

        # If this would cause significant overtime without rest opportunity
        if potential_driving > 8 * 3600:
            # Check if there's time for rest
            time_margin = (delivery_deadline_tick - est_delivery_tick) * world.dt_s
            rest_needed = self._calculate_required_rest()
            if time_margin < rest_needed:
                return False, "insufficient_rest_time"

        return True, None

    def _estimate_delivery_times(
        self, world: World, origin_site_id: SiteID, destination_site_id: SiteID
    ) -> tuple[int, int]:
        """Estimate pickup and delivery tick times.

        Returns:
            Tuple of (estimated_pickup_tick, estimated_delivery_tick)
        """
        current_tick = world.tick

        # Get current position
        current_node = self.current_node
        if current_node is None and self.current_edge is not None:
            # On an edge - estimate remaining travel time on current edge
            edge = world.graph.get_edge(self.current_edge)
            if edge is not None:
                current_node = edge.to_node

        if current_node is None:
            return current_tick + 99999, current_tick + 99999

        # Get origin and destination nodes
        origin_node = self._get_site_node(origin_site_id, world)
        dest_node = self._get_site_node(destination_site_id, world)

        if origin_node is None or dest_node is None:
            return current_tick + 99999, current_tick + 99999

        # Calculate time to complete current delivery queue
        queue_time_s = self._estimate_queue_completion_time(world)

        # Time to origin
        time_to_origin_s = world.router.estimate_travel_time_s(
            current_node, origin_node, world.graph, self.max_speed_kph
        )

        # Loading time at origin (estimate based on package size, assume ~0.1 tonnes per size unit)
        package_weight = 0.1  # Rough estimate
        loading_time_s = package_weight / 0.5 * 60  # loading_rate = 0.5 tonnes/min

        # Time from origin to destination
        time_to_dest_s = world.router.estimate_travel_time_s(
            origin_node, dest_node, world.graph, self.max_speed_kph
        )

        # Unloading time at destination
        unloading_time_s = loading_time_s

        # Total estimates
        total_to_pickup_s = queue_time_s + time_to_origin_s
        total_to_delivery_s = total_to_pickup_s + loading_time_s + time_to_dest_s + unloading_time_s

        # Convert to ticks
        est_pickup_tick = current_tick + int(total_to_pickup_s / world.dt_s)
        est_delivery_tick = current_tick + int(total_to_delivery_s / world.dt_s)

        return est_pickup_tick, est_delivery_tick

    def _estimate_queue_completion_time(self, world: World) -> float:
        """Estimate time to complete all tasks in the current delivery queue.

        Returns:
            Estimated time in seconds
        """
        if not self.delivery_queue:
            return 0.0

        total_time = 0.0
        current_node = self.current_node

        if current_node is None and self.current_edge is not None:
            edge = world.graph.get_edge(self.current_edge)
            if edge is not None:
                current_node = edge.to_node

        if current_node is None:
            return float("inf")

        for task in self.delivery_queue:
            if task.status == TaskStatus.COMPLETED:
                continue

            # Travel time to task site
            task_node = self._get_site_node(task.site_id, world)
            if task_node is None:
                continue

            travel_time = world.router.estimate_travel_time_s(
                current_node, task_node, world.graph, self.max_speed_kph
            )
            total_time += travel_time

            # Loading/unloading time
            # Estimate weight from packages
            task_weight = 0.0
            for pkg_id in task.package_ids:
                package = world.packages.get(pkg_id)
                if package is not None:
                    task_weight += package.size * 0.1  # Convert size to weight

            operation_time = task_weight / 0.5 * 60  # 0.5 tonnes/min
            total_time += operation_time

            current_node = task_node

        return total_time

    def _handle_assignment_confirmation(self, msg: Msg, _world: World) -> None:
        """Handle confirmation that a package has been assigned to this truck."""
        body = msg.body
        package_id = PackageID(body.get("package_id", ""))
        origin_site_id = SiteID(body.get("origin_site_id", ""))
        destination_site_id = SiteID(body.get("destination_site_id", ""))

        # Add pickup task to queue
        pickup_task = DeliveryTask(
            site_id=origin_site_id,
            task_type=TaskType.PICKUP,
            package_ids=[package_id],
            estimated_arrival_tick=0,  # Will be updated during route planning
            status=TaskStatus.PENDING,
        )

        # Add delivery task to queue
        delivery_task = DeliveryTask(
            site_id=destination_site_id,
            task_type=TaskType.DELIVERY,
            package_ids=[package_id],
            estimated_arrival_tick=0,
            status=TaskStatus.PENDING,
        )

        # Add tasks to queue (pickup before delivery for this package)
        self._add_delivery_tasks(pickup_task, delivery_task)

    def _add_delivery_tasks(self, pickup_task: DeliveryTask, delivery_task: DeliveryTask) -> None:
        """Add pickup and delivery tasks to the queue intelligently.

        Tries to consolidate with existing tasks at the same sites.
        """
        # Check if we already have a pickup task for this site
        pickup_added = False
        for existing_task in self.delivery_queue:
            if (
                existing_task.site_id == pickup_task.site_id
                and existing_task.task_type == TaskType.PICKUP
                and existing_task.status == TaskStatus.PENDING
            ):
                # Consolidate: add packages to existing task
                for pkg_id in pickup_task.package_ids:
                    if pkg_id not in existing_task.package_ids:
                        existing_task.package_ids.append(pkg_id)
                pickup_added = True
                break

        if not pickup_added:
            # Find optimal position for pickup task
            # For now, append to end (can be optimized later)
            self.delivery_queue.append(pickup_task)

        # Check if we already have a delivery task for this site
        delivery_added = False
        for existing_task in self.delivery_queue:
            if (
                existing_task.site_id == delivery_task.site_id
                and existing_task.task_type == TaskType.DELIVERY
                and existing_task.status == TaskStatus.PENDING
            ):
                # Consolidate: add packages to existing task
                for pkg_id in delivery_task.package_ids:
                    if pkg_id not in existing_task.package_ids:
                        existing_task.package_ids.append(pkg_id)
                delivery_added = True
                break

        if not delivery_added:
            # Delivery task must come after pickup
            self.delivery_queue.append(delivery_task)

    def _try_start_site_operation(self, world: World) -> bool:
        """Try to start loading/unloading at the current node.

        Returns:
            True if an operation was started, False otherwise
        """
        if self.current_node is None or not self.delivery_queue:
            return False

        # Get the next pending task
        current_task = None
        for task in self.delivery_queue:
            if task.status == TaskStatus.PENDING:
                current_task = task
                break

        if current_task is None:
            return False

        # Check if we're at the task's site
        task_node = self._get_site_node(current_task.site_id, world)
        if task_node != self.current_node:
            return False

        # Get the site building
        site = self._resolve_site(world, current_task.site_id, self.current_node)
        if site is None:
            return False

        # Try to enter the site
        if not site.has_space():
            # Site is full, wait
            return True  # Return True to indicate we're handling this (waiting)

        try:
            site.enter(self.id)
            self.current_building_id = site.id
            self._building_node_id = self.current_node
        except ValueError:
            return True  # Site became full, wait

        # Mark task as in progress
        current_task.status = TaskStatus.IN_PROGRESS

        # Calculate loading/unloading time
        total_weight = 0.0
        for pkg_id in current_task.package_ids:
            package = world.packages.get(pkg_id)
            if package is not None:
                total_weight += package.size * 0.1  # Size to weight conversion

        self.loading_target_s = site.calculate_loading_time_s(total_weight)
        self.loading_progress_s = 0.0

        if current_task.task_type == TaskType.PICKUP:
            self.is_loading = True
        else:
            self.is_unloading = True

        return True

    def _handle_loading(self, world: World) -> None:
        """Handle package loading at a site."""
        self.loading_progress_s += world.dt_s

        if self.loading_progress_s >= self.loading_target_s:
            # Loading complete
            self._complete_loading(world)

    def _complete_loading(self, world: World) -> None:
        """Complete the loading operation at current site."""
        # Find the current loading task
        current_task = None
        for task in self.delivery_queue:
            if task.status == TaskStatus.IN_PROGRESS and task.task_type == TaskType.PICKUP:
                current_task = task
                break

        if current_task is None:
            self.is_loading = False
            return

        # Load all packages from this task
        for pkg_id in current_task.package_ids:
            package = world.packages.get(pkg_id)
            if package is not None and self.can_load_package(world, pkg_id):
                self.load_package(pkg_id)
                world.update_package_status(pkg_id, PackageStatus.IN_TRANSIT.value, self.id)

                # Remove from site's active packages
                site = self._resolve_site(world, current_task.site_id, self.current_node)
                if site is not None:
                    site.remove_package(pkg_id)
                    site.update_statistics("picked_up")

        # Mark task as completed
        current_task.status = TaskStatus.COMPLETED

        # Leave the site
        self._leave_site(world)

        # Reset loading state
        self.is_loading = False
        self.loading_progress_s = 0.0
        self.loading_target_s = 0.0

        # Notify broker of pickup
        if self.broker_id is not None:
            for pkg_id in current_task.package_ids:
                pickup_msg = Msg(
                    src=self.id,
                    dst=self.broker_id,
                    typ="pickup_confirmed",
                    body={"package_id": str(pkg_id)},
                )
                self.outbox.append(pickup_msg)

    def _handle_unloading(self, world: World) -> None:
        """Handle package unloading at a site."""
        self.loading_progress_s += world.dt_s

        if self.loading_progress_s >= self.loading_target_s:
            # Unloading complete
            self._complete_unloading(world)

    def _complete_unloading(self, world: World) -> None:
        """Complete the unloading operation at current site."""
        # Find the current unloading task
        current_task = None
        for task in self.delivery_queue:
            if task.status == TaskStatus.IN_PROGRESS and task.task_type == TaskType.DELIVERY:
                current_task = task
                break

        if current_task is None:
            self.is_unloading = False
            return

        # Unload all packages destined for this site
        for pkg_id in list(current_task.package_ids):  # Copy list since we're modifying
            if pkg_id in self.loaded_packages:
                package = world.packages.get(pkg_id)
                self.unload_package(pkg_id)

                if package is not None:
                    # Check if on time
                    on_time = world.tick <= package.delivery_deadline_tick
                    world.update_package_status(pkg_id, PackageStatus.DELIVERED.value, self.id)

                    # Update site statistics
                    site = self._resolve_site(world, current_task.site_id, self.current_node)
                    if site is not None:
                        site.update_statistics("delivered", package.value_currency)

                    # Notify broker of delivery
                    if self.broker_id is not None:
                        delivery_msg = Msg(
                            src=self.id,
                            dst=self.broker_id,
                            typ="delivery_confirmed",
                            body={
                                "package_id": str(pkg_id),
                                "delivery_tick": world.tick,
                                "on_time": on_time,
                                "delivery_site_id": str(current_task.site_id),
                            },
                        )
                        self.outbox.append(delivery_msg)

        # Mark task as completed
        current_task.status = TaskStatus.COMPLETED

        # Leave the site
        self._leave_site(world)

        # Reset unloading state
        self.is_unloading = False
        self.loading_progress_s = 0.0
        self.loading_target_s = 0.0

    def _leave_site(self, world: World) -> None:
        """Leave the current site building."""
        if self.current_building_id is None:
            return

        site = self._resolve_site(
            world, self.current_building_id, self.current_node or self._building_node_id
        )
        if site is not None and self.id in site.current_agents:
            site.leave(self.id)

        self.current_building_id = None
        self._building_node_id = None

    def _resolve_site(self, world: World, site_id: SiteID, node_id: NodeID | None) -> Site | None:
        """Resolve a site building from its ID."""
        target_node_id = node_id or self._building_node_id
        if target_node_id is None:
            return None

        node = world.graph.get_node(target_node_id)
        if node is None:
            return None

        for building in node.get_buildings():
            if building.id == site_id and isinstance(building, Site):
                return building

        return None

    def _get_site_node(self, site_id: SiteID, world: World) -> NodeID | None:
        """Get the node ID where a site is located."""
        for node_id_raw, node in world.graph.nodes.items():
            for building in node.buildings:
                if isinstance(building, Site) and building.id == site_id:
                    return cast(NodeID, node_id_raw)
        return None

    def _plan_next_destination(self, world: World) -> None:
        """Plan route to next destination based on delivery queue.

        If no delivery tasks are pending, the truck seeks the closest parking
        to wait for broker assignments (idle parking, not rest).
        """
        # First, clean up completed tasks
        self.delivery_queue = [
            task for task in self.delivery_queue if task.status != TaskStatus.COMPLETED
        ]

        # Check if we have pending delivery tasks
        if self.delivery_queue:
            # Clear idle parking state if we have tasks
            if self.is_seeking_idle_parking:
                self.is_seeking_idle_parking = False
                if self.current_building_id is not None and not self.is_resting:
                    self.leave_parking(world)

            # Find next pending task
            next_task = None
            for task in self.delivery_queue:
                if task.status == TaskStatus.PENDING:
                    next_task = task
                    break

            if next_task is not None:
                # Route to next task's site
                dest_node = self._get_site_node(next_task.site_id, world)
                if dest_node is not None:
                    self.destination = dest_node
                    self._set_route(world)
                    return

        # No delivery tasks - seek closest parking for idle waiting
        # Only if not already at a parking (unless we're resting)
        if self.current_building_id is not None and not self.is_resting:
            # Already at a parking, stay there
            self.destination = None
            self.route = []
            self.route_start_node = None
            self.route_end_node = None
            return

        # Seek closest parking
        if not self.is_seeking_idle_parking:
            self.is_seeking_idle_parking = True
            self._tried_parkings.clear()

        parking_id, route = self._find_closest_parking(world)
        if parking_id and route:
            self.destination = route[-1] if route else None
            self.route_end_node = self.destination
            if route and self.current_node and route[0] == self.current_node:
                self.route = route[1:]
            else:
                self.route = route
        else:
            # No parking found - clear seeking flag and stay put
            self.is_seeking_idle_parking = False
            self.destination = None
            self.route = []
            self.route_start_node = None
            self.route_end_node = None

    def serialize_diff(self) -> dict[str, Any] | None:
        """Return a small dict for UI delta, or None if no changes.

        Only emits updates when watch fields change (node, edge, speed, route, route boundary,
        loaded packages, or building). Watch field changes are detected using
        TruckWatchFieldsDTO comparison.
        When changes are detected, returns complete state (TruckStateDTO) including tachograph
        and fuel fields.
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
            current_building_id=self.current_building_id,  # Triggers update on building enter/leave
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
            is_seeking_idle_parking=self.is_seeking_idle_parking,
            original_destination=self.original_destination,
            # Fuel system fields
            fuel_tank_capacity_l=self.fuel_tank_capacity_l,
            current_fuel_l=self.current_fuel_l,
            co2_emitted_kg=self.co2_emitted_kg,
            is_seeking_gas_station=self.is_seeking_gas_station,
            is_fueling=self.is_fueling,
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
            "is_seeking_idle_parking": self.is_seeking_idle_parking,
            "original_destination": self.original_destination,
            # Fuel system fields
            "fuel_tank_capacity_l": self.fuel_tank_capacity_l,
            "current_fuel_l": self.current_fuel_l,
            "co2_emitted_kg": self.co2_emitted_kg,
            "is_seeking_gas_station": self.is_seeking_gas_station,
            "is_fueling": self.is_fueling,
            "fueling_liters_needed": self.fueling_liters_needed,
            # Delivery system fields
            "delivery_queue": [task.to_dict() for task in self.delivery_queue],
            "is_loading": self.is_loading,
            "is_unloading": self.is_unloading,
            "loading_progress_s": self.loading_progress_s,
            "loading_target_s": self.loading_target_s,
            "broker_id": str(self.broker_id) if self.broker_id else None,
            # Metadata
            "inbox_count": len(self.inbox),
            "outbox_count": len(self.outbox),
            "tags": self.tags.copy(),
        }
