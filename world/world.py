import random
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from agents.base import AgentBase
    from world.generation.params import GenerationParams

from core.buildings.base import Building
from core.buildings.site import Site
from core.packages.package import Package
from core.types import AgentID, NodeID, PackageID, SiteID
from world.io import map_manager
from world.routing.navigator import Navigator
from world.sim.dto.step_result_dto import StepResultDTO, TickDataDTO

# Constants for fuel price simulation
SECONDS_PER_DAY = 86400  # 24 hours in seconds
DEFAULT_FUEL_PRICE = 5.0  # Default fuel price in ducats/liter
DEFAULT_FUEL_VOLATILITY = 0.1  # ±10% daily change

# Simulation time constants
SIMULATION_START_HOUR = 12  # Simulation starts at 12:00 (noon)
SIMULATION_START_SECONDS = SIMULATION_START_HOUR * 3600  # 43200 seconds (12:00)


class World:
    def __init__(
        self,
        graph: Any,
        router: Any,
        traffic: Any,
        dt_s: float = 1.0,
        generation_params: "GenerationParams | None" = None,
        global_fuel_price: float = DEFAULT_FUEL_PRICE,
        fuel_price_volatility: float = DEFAULT_FUEL_VOLATILITY,
    ) -> None:
        self.graph = graph
        # Ensure router is Navigator instance
        self.router = router if router is not None else Navigator()
        self.traffic = traffic
        self.dt_s = dt_s
        self.tick = 0
        self.agents: dict[AgentID, AgentBase] = {}  # AgentID -> AgentBase
        self.packages: dict[PackageID, Package] = {}  # PackageID -> Package
        self._events: list[Any] = []
        self.generation_params = generation_params  # Store generation params if available

        # Global fuel price management
        self.global_fuel_price = global_fuel_price
        self.fuel_price_volatility = fuel_price_volatility
        self._last_fuel_price_day = -1  # Initialize to -1 so first tick triggers update

    def now_s(self) -> int:
        return int(self.tick * self.dt_s)

    def time_min(self) -> int:
        return int(self.now_s() / 60)

    def calculate_tick_data(self, tick: int | None = None) -> TickDataDTO:
        """Calculate tick time and day information.

        Simulation starts at 12:00 on day 1. Time is calculated based on
        elapsed simulation seconds from the start.

        Args:
            tick: Optional tick number to calculate for. If None, uses current self.tick.

        Returns:
            TickDataDTO with tick, time (24h format), and day.
        """
        # Use provided tick or current tick
        tick_number = tick if tick is not None else self.tick
        # Calculate elapsed seconds from start (tick 0 = 12:00 day 1)
        elapsed_seconds = tick_number * self.dt_s
        # Current time in seconds from midnight of day 1
        current_time_seconds = SIMULATION_START_SECONDS + elapsed_seconds
        # Calculate day (1-based)
        day = int(1 + (current_time_seconds // SECONDS_PER_DAY))
        # Calculate time in 24-hour format (0.0-23.999...)
        time_hours = (current_time_seconds % SECONDS_PER_DAY) / 3600.0
        return TickDataDTO(tick=tick_number, time=time_hours, day=day)

    def emit_event(self, e: Any) -> None:
        self._events.append(e)

    def step(self) -> StepResultDTO:
        """Execute one simulation tick and return the result.

        Returns:
            StepResultDTO containing all state changes from this tick.
        """
        self.tick += 1

        # 0) update global fuel price once per simulation day
        self._update_daily_fuel_price()
        # 1) sense (optional)
        for a in self.agents.values():
            a.perceive(self)
        # 2) dispatch messages (outboxes to inboxes)
        self._deliver_all()
        # 3) process sites (spawn packages, check expiry)
        self._process_sites(self.tick)
        # 4) decide/act
        for a in self.agents.values():
            a.decide(self)
        # 5) collect UI diffs
        diffs = [a.serialize_diff() for a in self.agents.values()]
        # 6) collect building updates (only dirty buildings)
        building_updates = self._collect_building_updates()
        evts = self._events
        self._events = []
        # 7) calculate tick time and day information
        tick_data = self.calculate_tick_data()
        return StepResultDTO(
            events=evts,
            agent_diffs=diffs,
            building_updates=building_updates,
            tick_data=tick_data,
        )

    def add_agent(self, agent_id: AgentID, agent: "AgentBase") -> None:
        """Add an agent to the world."""
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already exists")
        self.agents[agent_id] = agent
        self.emit_event({"type": "agent_added", "agent_id": agent_id, "agent_kind": agent.kind})

    def remove_agent(self, agent_id: AgentID) -> None:
        """Remove an agent from the world."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} does not exist")
        agent = self.agents.pop(agent_id)
        self.emit_event({"type": "agent_removed", "agent_id": agent_id, "agent_kind": agent.kind})

    def modify_agent(self, agent_id: AgentID, modifications: dict[str, Any]) -> None:
        """Modify an agent's properties."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} does not exist")

        agent = self.agents[agent_id]
        for key, value in modifications.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
            else:
                # Store in tags for arbitrary metadata
                agent.tags[key] = value

        self.emit_event(
            {"type": "agent_modified", "agent_id": agent_id, "modifications": modifications}
        )

    def add_package(self, package: Package) -> None:
        """Add a package to the world."""
        if package.id in self.packages:
            raise ValueError(f"Package {package.id} already exists")
        self.packages[package.id] = package
        self.emit_event(
            {"type": "package_created", "package_id": package.id, "data": package.to_dict()}
        )

    def remove_package(self, package_id: PackageID) -> None:
        """Remove a package from the world."""
        if package_id not in self.packages:
            raise ValueError(f"Package {package_id} does not exist")
        package = self.packages.pop(package_id)
        self.emit_event(
            {"type": "package_removed", "package_id": package_id, "data": package.to_dict()}
        )

    def get_packages_at_site(self, site_id: SiteID) -> list[Package]:
        """Get all packages waiting for pickup at a specific site."""
        return [
            package
            for package in self.packages.values()
            if package.origin_site == site_id and package.status.value == "WAITING_PICKUP"
        ]

    def get_package(self, package_id: PackageID) -> Package:
        """Get a package by ID."""
        if package_id not in self.packages:
            raise ValueError(f"Package {package_id} does not exist")
        return self.packages[package_id]

    def get_site_node(self, site_id: SiteID) -> NodeID | None:
        """Get the node ID where a site is located.

        Args:
            site_id: Site building ID to look up

        Returns:
            NodeID where the site is located, or None if not found
        """
        for node_id_raw, node in self.graph.nodes.items():
            for building in node.buildings:
                if isinstance(building, Site) and building.id == site_id:
                    return cast(NodeID, node_id_raw)
        return None

    def update_package_status(
        self, package_id: PackageID, new_status: str, agent_id: AgentID | None = None
    ) -> None:
        """Update package status and emit appropriate events."""
        if package_id not in self.packages:
            raise ValueError(f"Package {package_id} does not exist")

        package = self.packages[package_id]
        old_status = package.status.value
        package.status = package.status.__class__(new_status)

        # Emit specific events based on status change
        if new_status == "IN_TRANSIT" and old_status == "WAITING_PICKUP":
            self.emit_event(
                {
                    "type": "package_picked_up",
                    "package_id": package_id,
                    "agent_id": agent_id,
                    "data": package.to_dict(),
                }
            )
        elif new_status == "DELIVERED" and old_status == "IN_TRANSIT":
            self.emit_event(
                {
                    "type": "package_delivered",
                    "package_id": package_id,
                    "site_id": package.destination_site,
                    "value": package.value_currency,
                    "data": package.to_dict(),
                }
            )

    def export_graph(self, map_name: str) -> None:
        """Export the world's graph to a GraphML file.

        Args:
            map_name: Name for the map file (will be sanitized)

        Raises:
            ValueError: If the map file already exists
            OSError: If there's an error writing the file
        """
        map_manager.export_map(self.graph, map_name)

    def import_graph(self, map_name: str) -> None:
        """Import a graph from a GraphML file and replace the world's current graph.

        Args:
            map_name: Name of the map file to import (will be sanitized)

        Raises:
            FileNotFoundError: If the map file doesn't exist
            ValueError: If there's an error parsing the GraphML file
        """
        new_graph = map_manager.import_map(map_name)
        self.graph = new_graph
        self.emit_event({"type": "graph_imported", "map_name": map_name})

    def get_full_state(self) -> dict[str, Any]:
        """Get complete world state for state snapshot."""
        return {
            "graph": self.graph.to_dict(),
            "agents": [agent.serialize_full() for agent in self.agents.values()],
            "packages": [package.to_dict() for package in self.packages.values()],
            "metadata": {
                "tick": self.tick,
                "dt_s": self.dt_s,
                "now_s": self.now_s(),
                "time_min": self.time_min(),
                "global_fuel_price": self.global_fuel_price,
                "current_day": self.now_s() // SECONDS_PER_DAY,
            },
        }

    def _process_sites(self, current_tick: int) -> None:
        """Process all sites for package spawning and expiry checking."""
        # Get all sites from graph nodes
        sites: list[Site] = []
        for node in self.graph.nodes.values():
            for building in node.buildings:
                if isinstance(building, Site):
                    sites.append(building)

        # Process each site
        for site in sites:
            # Check for package spawning
            if site.should_spawn_package(self.dt_s):
                self._spawn_package_at_site(site, current_tick)

            # Check for package expiry
            self._check_package_expiry_at_site(site, current_tick)

    def _spawn_package_at_site(self, site: "Site", current_tick: int) -> None:
        """Spawn a new package at a site."""

        from core.buildings.site import Site as SiteType
        from core.packages.package import Package
        from core.types import PackageID, SiteID

        # Get available destination sites
        available_sites: list[SiteID] = []
        for node in self.graph.nodes.values():
            for building in node.buildings:
                if isinstance(building, SiteType) and building.id != site.id:
                    available_sites.append(building.id)

        if not available_sites:
            return  # No destinations available

        # Select destination
        destination_site = site.select_destination(available_sites)
        if not destination_site:
            return

        # Generate package parameters
        params = site.generate_package_parameters()

        # Create package ID
        package_id = PackageID(f"pkg-{site.id}-{current_tick}-{len(site.active_packages)}")

        # Create package
        package = Package(
            id=package_id,
            origin_site=site.id,
            destination_site=destination_site,
            size=params["size"],
            value_currency=params["value_currency"],
            priority=params["priority"],
            urgency=params["urgency"],
            spawn_tick=current_tick,
            pickup_deadline_tick=current_tick + params["pickup_deadline_tick"],
            delivery_deadline_tick=current_tick + params["delivery_deadline_tick"],
        )

        # Add to world and site
        self.add_package(package)
        site.add_package(package_id)
        site.update_statistics("generated")

    def _check_package_expiry_at_site(self, site: "Site", current_tick: int) -> None:
        """Check for expired packages at a site."""

        expired_packages = []
        # Check all packages that originated from this site
        from core.types import SiteID

        site_id: SiteID = site.id
        for package_id, package in self.packages.items():
            if package.origin_site == site_id and package.is_expired(current_tick):
                expired_packages.append(package_id)

        # Process expired packages
        for package_id in expired_packages:
            package = self.packages[package_id]
            package.status = package.status.__class__("EXPIRED")

            # Store package data before removal
            package_data = package.to_dict()
            value_lost = package.value_currency

            # Update site statistics
            site.update_statistics("expired", value_lost)
            site.remove_package(package_id)

            # Emit expiry event before removal
            self.emit_event(
                {
                    "type": "package_expired",
                    "package_id": package_id,
                    "site_id": site.id,
                    "value_lost": value_lost,
                    "data": package_data,
                }
            )

            # Remove package from world (directly without emitting event)
            del self.packages[package_id]

    def _update_daily_fuel_price(self) -> None:
        """Update global fuel price once per simulation day.

        Uses a random walk with volatility to simulate market fluctuations.
        The price changes at most once per simulation day (86400 simulation seconds).
        """
        current_day = self.now_s() // SECONDS_PER_DAY
        if current_day > self._last_fuel_price_day:
            # Random walk: multiply by (1 + random change within volatility range)
            change = random.uniform(-self.fuel_price_volatility, self.fuel_price_volatility)
            self.global_fuel_price *= 1 + change
            self._last_fuel_price_day = current_day

    def _deliver_all(self) -> None:
        # deliver last tick's outboxes (you can store separately)
        outboxes = []
        for a in self.agents.values():
            if a.outbox:
                outboxes.extend(a.outbox)
                a.outbox = []
        for m in outboxes:
            if m.dst and m.dst in self.agents:
                self.agents[m.dst].inbox.append(m)
            elif m.topic:
                for _, agent in self.agents.items():
                    if m.topic in agent.tags.get("topics", []):
                        agent.inbox.append(m)

    def _collect_building_updates(self) -> list[dict[str, Any]]:
        """Collect serialized state from all dirty buildings.

        Returns:
            List of serialized building states for buildings that have changed.
        """
        updates: list[dict[str, Any]] = []
        for node in self.graph.nodes.values():
            for building in node.buildings:
                if isinstance(building, Building) and building.is_dirty():
                    diff = building.serialize_diff()
                    if diff is not None:
                        updates.append(diff)
        return updates
