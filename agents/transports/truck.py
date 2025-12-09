"""Truck transport agent for autonomous navigation through the graph network."""

import random
from dataclasses import dataclass, field
from typing import Any

from core.buildings.gas_station import GasStation
from core.buildings.parking import Parking
from core.messages import Msg
from core.types import AgentID, BuildingID, EdgeID, NodeID, PackageID
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
    is_seeking_parking: bool = False  # Flag for active parking search
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

        Behavior:
        - Handle fueling state (highest priority after resting)
        - Track driving time and enforce rest periods
        - Apply penalties for overtime driving
        - Seek gas station when fuel is low
        - Seek parking when approaching time limits
        - Handle parking/gas station full scenarios
        - If route is empty: pick random destination and compute route
        - If at node with route: enter next edge in route
        - If on edge: update position along edge, transition to node when complete
        """
        # Handle fueling state (highest priority)
        if self.is_fueling:
            self._handle_fueling(world)
            return

        # Handle resting state (second highest priority)
        if self.is_resting:
            self._handle_resting(world)
            return

        # Check for overtime penalties (apply once per violation)
        if self.driving_time_s > 8 * 3600:
            self._apply_tachograph_penalty(world)

        # Decide if should seek gas station based on fuel level (priority over parking)
        if (
            not self.is_seeking_gas_station
            and not self.is_seeking_parking
            and self._should_seek_gas_station()
        ):
            self.is_seeking_gas_station = True
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
            and self._should_seek_parking()
        ):
            self.is_seeking_parking = True
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
                if not self.is_seeking_parking and not self.is_seeking_gas_station:
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
            "original_destination": self.original_destination,
            # Fuel system fields
            "fuel_tank_capacity_l": self.fuel_tank_capacity_l,
            "current_fuel_l": self.current_fuel_l,
            "co2_emitted_kg": self.co2_emitted_kg,
            "is_seeking_gas_station": self.is_seeking_gas_station,
            "is_fueling": self.is_fueling,
            "fueling_liters_needed": self.fueling_liters_needed,
            # Metadata
            "inbox_count": len(self.inbox),
            "outbox_count": len(self.outbox),
            "tags": self.tags.copy(),
        }
