"""Broker agent for negotiating package pickups with trucks."""

from dataclasses import dataclass, field
from typing import Any, cast

from core.messages import Msg
from core.packages.package import Package
from core.types import AgentID, NegotiationStatus, NodeID, PackageID, PackageStatus, SiteID
from world.world import World

# Financial constants
PICKUP_EXPIRY_FINE_MULTIPLIER: float = 0.5  # Fine = 50% of package value
LATE_DELIVERY_PENALTY_PER_TICK: float = 0.001  # 0.1% per tick late


@dataclass
class NegotiationState:
    """Tracks the state of a package negotiation."""

    package_id: PackageID
    status: NegotiationStatus
    candidate_trucks: list[AgentID]  # Trucks to try in order
    current_truck_idx: int = 0  # Index of truck currently being negotiated with
    responses_received: int = 0


@dataclass
class Broker:
    """Singleton agent that negotiates package pickups with trucks.

    The broker receives information about new packages and negotiates with nearby
    trucks to determine which should pick up and deliver each package.

    Key constraints:
    - Only ONE active negotiation at a time to prevent race conditions
    - Trucks evaluate proposals against their current state
    - Broker holds company finances and pays/receives for deliveries

    Attributes:
        id: Agent unique identifier
        kind: Agent kind string ("broker")
        balance_ducats: Company financial balance
        package_queue: FIFO queue of packages awaiting negotiation
        active_negotiation: Currently active negotiation state (only one)
        assigned_packages: Mapping of package ID to assigned truck
        known_packages: Set of package IDs the broker has already seen
    """

    id: AgentID
    kind: str = "broker"
    inbox: list[Msg] = field(default_factory=list)
    outbox: list[Msg] = field(default_factory=list)
    tags: dict[str, Any] = field(default_factory=dict)

    # Financial state
    balance_ducats: float = 10000.0  # Starting capital

    # Negotiation state
    package_queue: list[PackageID] = field(default_factory=list)
    active_negotiation: NegotiationState | None = None
    assigned_packages: dict[PackageID, AgentID] = field(default_factory=dict)
    known_packages: set[PackageID] = field(default_factory=set)

    # Tracking
    _last_serialized_state: dict[str, Any] = field(default_factory=dict, init=False)

    def perceive(self, world: World) -> None:
        """Scan world for new packages and add them to negotiation queue.

        This runs every tick before decide() and adds any new WAITING_PICKUP
        packages to the queue for negotiation.
        """
        for package_id, package in world.packages.items():
            if package.status != PackageStatus.WAITING_PICKUP:
                continue
            if package_id in self.known_packages:
                continue

            self.known_packages.add(package_id)
            if package_id in self.assigned_packages:
                continue

            if self.active_negotiation is None or self.active_negotiation.package_id != package_id:
                self.package_queue.append(package_id)

    def decide(self, world: World) -> None:
        """Process negotiations and manage package lifecycle.

        Only ONE package negotiation per tick to prevent race conditions
        where a truck accepts multiple packages based on stale state.

        Priority:
        1. Process inbox responses for active negotiation
        2. Start new negotiation if none active and queue not empty
        3. Check for pickup deadline expiry on queued packages
        4. Process delivery confirmations
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            logger.debug(f"Broker.decide() starting at tick {world.tick}")

            # 1. Process inbox messages
            logger.debug(f"Broker: Processing {len(self.inbox)} inbox messages")
            self._process_inbox(world)
            logger.debug("Broker: Inbox processed")

            # 2. Handle active negotiation responses
            if self.active_negotiation is not None:
                logger.debug(
                    f"Broker: Handling active negotiation for package {self.active_negotiation.package_id}"
                )
                self._handle_negotiation_response(world)
                logger.debug("Broker: Active negotiation handled")

            # 3. Start new negotiation if none active
            if self.active_negotiation is None and self.package_queue:
                logger.debug(
                    f"Broker: Starting new negotiation (queue size: {len(self.package_queue)})"
                )
                self._start_new_negotiation(world)
                logger.debug("Broker: New negotiation started")

            # 4. Check for pickup deadline expiry and apply fines
            logger.debug("Broker: Checking package expiry")
            self._check_package_expiry(world)
            logger.debug("Broker: Package expiry checked")

            # Clear inbox after processing
            self.inbox = []
            logger.debug(f"Broker.decide() completed at tick {world.tick}")

        except Exception as e:
            logger.error(f"Broker.decide() error at tick {world.tick}: {e}", exc_info=True)
            raise

    def _process_inbox(self, world: World) -> None:
        """Process all messages in inbox."""
        for msg in self.inbox:
            if msg.typ == "accept":
                self._handle_accept_message(msg, world)
            elif msg.typ == "reject":
                self._handle_reject_message(msg, world)
            elif msg.typ == "delivery_confirmed":
                self._handle_delivery_confirmation(msg, world)
            elif msg.typ == "pickup_confirmed":
                self._handle_pickup_confirmation(msg, world)

    def _handle_accept_message(self, msg: Msg, _world: World) -> None:
        """Handle acceptance of a pickup proposal."""
        package_id = PackageID(msg.body.get("package_id", ""))

        # Verify this is for the active negotiation
        if self.active_negotiation is None or self.active_negotiation.package_id != package_id:
            return  # Stale response, ignore

        # Mark negotiation as accepted
        self.active_negotiation.status = NegotiationStatus.ACCEPTED

    def _handle_reject_message(self, msg: Msg, _world: World) -> None:
        """Handle rejection of a pickup proposal."""
        package_id = PackageID(msg.body.get("package_id", ""))

        # Verify this is for the active negotiation
        if self.active_negotiation is None or self.active_negotiation.package_id != package_id:
            return  # Stale response, ignore

        # Move to next truck candidate
        self.active_negotiation.current_truck_idx += 1
        self.active_negotiation.responses_received += 1

    def _handle_delivery_confirmation(self, msg: Msg, world: World) -> None:
        """Handle confirmation that a package was delivered."""
        package_id = PackageID(msg.body.get("package_id", ""))
        delivery_tick = msg.body.get("delivery_tick", world.tick)
        on_time = msg.body.get("on_time", True)

        # Get package to calculate payment
        package = world.packages.get(package_id)
        if package is None:
            return

        # Calculate payment
        payment = package.value_currency

        if not on_time:
            # Calculate late penalty
            ticks_late = delivery_tick - package.delivery_deadline_tick
            if ticks_late > 0:
                penalty = payment * LATE_DELIVERY_PENALTY_PER_TICK * ticks_late
                payment = max(0.0, payment - penalty)

        # Receive payment
        self.balance_ducats += payment

        # Emit payment event
        world.emit_event(
            {
                "type": "broker_event",
                "event_type": "delivery_payment_received",
                "package_id": str(package_id),
                "payment": payment,
                "on_time": on_time,
                "new_balance": self.balance_ducats,
            }
        )

        # Remove from assigned packages
        if package_id in self.assigned_packages:
            del self.assigned_packages[package_id]

    def _handle_pickup_confirmation(self, msg: Msg, world: World) -> None:
        """Handle confirmation that a package was picked up."""
        package_id = PackageID(msg.body.get("package_id", ""))
        agent_id = msg.src

        # Emit pickup event
        world.emit_event(
            {
                "type": "broker_event",
                "event_type": "package_pickup_confirmed",
                "package_id": str(package_id),
                "agent_id": str(agent_id),
            }
        )

    def _handle_negotiation_response(self, world: World) -> None:
        """Process the current negotiation state after inbox processing."""
        if self.active_negotiation is None:
            return

        neg = self.active_negotiation
        package_id = neg.package_id

        # Check if package still exists
        package = world.packages.get(package_id)
        if package is None or package.status != PackageStatus.WAITING_PICKUP:
            # Package no longer available - abort negotiation
            self.active_negotiation = None
            return

        # If accepted, finalize assignment
        if neg.status == NegotiationStatus.ACCEPTED:
            truck_id = neg.candidate_trucks[neg.current_truck_idx]
            self._finalize_assignment(package_id, truck_id, package, world)
            self.active_negotiation = None
            return

        # If we've tried all candidates, put package back in queue
        if neg.current_truck_idx >= len(neg.candidate_trucks):
            # All trucks rejected - put back in queue for later
            if package_id not in self.package_queue:
                self.package_queue.append(package_id)
            self.active_negotiation = None
            return

        # If we haven't sent proposal to current truck yet, send it
        # (This handles moving to next truck after rejection)
        if neg.responses_received == neg.current_truck_idx:
            self._send_proposal_to_current_truck(world)

    def _start_new_negotiation(self, world: World) -> None:
        """Start negotiation for the next package in queue.

        To prevent infinite loops when no trucks are available, we limit
        how many packages we try per tick (max = current queue size).
        """
        import logging

        logger = logging.getLogger(__name__)

        logger.debug(f"_start_new_negotiation: Queue has {len(self.package_queue)} packages")

        # Limit attempts to prevent infinite loop when no trucks available
        max_attempts = len(self.package_queue)
        attempts = 0

        while self.package_queue and attempts < max_attempts:
            attempts += 1
            package_id = self.package_queue.pop(0)
            logger.debug(
                f"_start_new_negotiation: Processing package {package_id} (attempt {attempts}/{max_attempts})"
            )

            # Verify package still exists and is available
            package = world.packages.get(package_id)
            if package is None or package.status != PackageStatus.WAITING_PICKUP:
                logger.debug(f"_start_new_negotiation: Package {package_id} no longer available")
                continue

            # Skip if already assigned
            if package_id in self.assigned_packages:
                logger.debug(f"_start_new_negotiation: Package {package_id} already assigned")
                continue

            # Find candidate trucks
            logger.debug(f"_start_new_negotiation: Finding candidates for package {package_id}")
            candidates = self._find_candidate_trucks(package, world)
            logger.debug(
                f"_start_new_negotiation: Found {len(candidates)} candidates for package {package_id}"
            )

            if not candidates:
                # No trucks available - put back at end of queue
                logger.debug(
                    f"_start_new_negotiation: No candidates, requeueing package {package_id}"
                )
                self.package_queue.append(package_id)
                continue

            # Start negotiation
            logger.debug(f"_start_new_negotiation: Starting negotiation for package {package_id}")
            self.active_negotiation = NegotiationState(
                package_id=package_id,
                status=NegotiationStatus.PROPOSED,
                candidate_trucks=candidates,
                current_truck_idx=0,
                responses_received=0,
            )

            # Send proposal to first candidate
            logger.debug(f"_start_new_negotiation: Sending proposal to truck {candidates[0]}")
            self._send_proposal_to_current_truck(world)
            logger.debug("_start_new_negotiation: Completed successfully")
            return

        if attempts >= max_attempts:
            logger.warning(
                f"_start_new_negotiation: Reached max attempts ({max_attempts}), "
                f"no negotiation started. Queue size: {len(self.package_queue)}"
            )
        else:
            logger.debug("_start_new_negotiation: Queue empty, no negotiation started")

    def _find_candidate_trucks(self, package: Package, world: World) -> list[AgentID]:
        """Find trucks that could potentially pick up this package.

        Trucks are sorted by estimated travel time to the pickup site.

        Args:
            package: Package to be picked up
            world: World instance

        Returns:
            List of truck AgentIDs sorted by proximity to pickup site
        """
        import logging

        from agents.transports.truck import Truck

        logger = logging.getLogger(__name__)

        logger.debug(
            f"_find_candidate_trucks: Finding trucks for package at site {package.origin_site}"
        )

        candidates: list[tuple[float, AgentID]] = []

        # Get pickup site node
        logger.debug(f"_find_candidate_trucks: Getting site node for {package.origin_site}")
        origin_node = self._get_site_node(package.origin_site, world)
        if origin_node is None:
            logger.debug(f"_find_candidate_trucks: Site {package.origin_site} node not found")
            return []
        logger.debug(f"_find_candidate_trucks: Site node is {origin_node}")

        logger.debug(f"_find_candidate_trucks: Evaluating {len(world.agents)} agents")

        for idx, (agent_id, agent) in enumerate(world.agents.items()):
            if idx % 5 == 0:  # Log every 5 agents to avoid spam
                logger.debug(
                    f"_find_candidate_trucks: Processing agent {idx + 1}/{len(world.agents)}"
                )

            if not isinstance(agent, Truck):
                continue

            # Skip trucks that are busy with high-priority tasks
            if agent.is_fueling or agent.is_resting:
                continue

            # Get truck's current node
            truck_node = agent.current_node
            if truck_node is None:
                edge = (
                    world.graph.get_edge(agent.current_edge)
                    if agent.current_edge is not None
                    else None
                )
                truck_node = edge.to_node if edge is not None else None

            if truck_node is None:
                continue

            # Estimate travel time to pickup site
            logger.debug(
                f"_find_candidate_trucks: Estimating travel time for truck {agent_id} from {truck_node} to {origin_node}"
            )
            travel_time = world.router.estimate_travel_time_s(
                truck_node, origin_node, world.graph, agent.max_speed_kph
            )
            logger.debug(f"_find_candidate_trucks: Truck {agent_id} travel time: {travel_time}s")

            if travel_time < float("inf"):
                candidates.append((travel_time, agent_id))

        # Sort by travel time (closest first)
        candidates.sort(key=lambda x: x[0])

        logger.debug(f"_find_candidate_trucks: Found {len(candidates)} candidate trucks")
        return [agent_id for _, agent_id in candidates]

    def _send_proposal_to_current_truck(self, world: World) -> None:
        """Send pickup proposal to the current candidate truck."""
        if self.active_negotiation is None:
            return

        neg = self.active_negotiation
        if neg.current_truck_idx >= len(neg.candidate_trucks):
            return

        truck_id = neg.candidate_trucks[neg.current_truck_idx]
        package = world.packages.get(neg.package_id)
        if package is None:
            return

        # Create proposal message
        proposal = Msg(
            src=self.id,
            dst=truck_id,
            typ="proposal",
            body={
                "package_id": str(neg.package_id),
                "origin_site_id": str(package.origin_site),
                "destination_site_id": str(package.destination_site),
                "package_size": package.size,
                "package_value": package.value_currency,
                "pickup_deadline_tick": package.pickup_deadline_tick,
                "delivery_deadline_tick": package.delivery_deadline_tick,
            },
        )

        self.outbox.append(proposal)

    def _finalize_assignment(
        self, package_id: PackageID, truck_id: AgentID, package: Package, world: World
    ) -> None:
        """Finalize the assignment of a package to a truck."""
        # Record assignment
        self.assigned_packages[package_id] = truck_id

        # Send assignment confirmation to truck
        confirmation = Msg(
            src=self.id,
            dst=truck_id,
            typ="assignment_confirmed",
            body={
                "package_id": str(package_id),
                "origin_site_id": str(package.origin_site),
                "destination_site_id": str(package.destination_site),
                "package_size": package.size,
                "pickup_deadline_tick": package.pickup_deadline_tick,
                "delivery_deadline_tick": package.delivery_deadline_tick,
            },
        )

        self.outbox.append(confirmation)

        # Emit assignment event
        world.emit_event(
            {
                "type": "broker_event",
                "event_type": "package_assigned",
                "package_id": str(package_id),
                "agent_id": str(truck_id),
            }
        )

    def _check_package_expiry(self, world: World) -> None:
        """Check for expired packages and apply fines.

        This checks packages in the queue and assigned packages that have
        expired their pickup deadline.
        """
        current_tick = world.tick
        expired_in_queue: list[PackageID] = []

        # Check packages still in queue
        for package_id in self.package_queue:
            package = world.packages.get(package_id)
            if package is None:
                expired_in_queue.append(package_id)
                continue

            if package.is_expired(current_tick):
                # Apply fine
                fine = package.value_currency * PICKUP_EXPIRY_FINE_MULTIPLIER
                self.balance_ducats -= fine

                world.emit_event(
                    {
                        "type": "broker_event",
                        "event_type": "pickup_expiry_fine",
                        "package_id": str(package_id),
                        "fine": fine,
                        "new_balance": self.balance_ducats,
                    }
                )

                expired_in_queue.append(package_id)

        # Remove expired packages from queue
        for package_id in expired_in_queue:
            if package_id in self.package_queue:
                self.package_queue.remove(package_id)
            if package_id in self.known_packages:
                self.known_packages.discard(package_id)
            if package_id in self.assigned_packages:
                del self.assigned_packages[package_id]

    def _get_site_node(self, site_id: SiteID, world: World) -> NodeID | None:
        """Get the node ID where a site is located.

        Args:
            site_id: Site building ID
            world: World instance

        Returns:
            NodeID where the site is located, or None if not found
        """
        import logging

        from core.buildings.site import Site

        logger = logging.getLogger(__name__)
        logger.debug(
            f"_get_site_node: Searching for site {site_id} in {len(world.graph.nodes)} nodes"
        )

        for node_id_raw, node in world.graph.nodes.items():
            for building in node.buildings:
                if isinstance(building, Site) and building.id == site_id:
                    logger.debug(f"_get_site_node: Found site {site_id} at node {node_id_raw}")
                    return cast(NodeID, node_id_raw)

        logger.warning(f"_get_site_node: Site {site_id} not found in graph")
        return None

    def serialize_diff(self) -> dict[str, Any] | None:
        """Return a small dict for UI delta, or None if no changes."""
        current_state = {
            "id": str(self.id),
            "kind": self.kind,
            "balance_ducats": self.balance_ducats,
            "queue_size": len(self.package_queue),
            "assigned_count": len(self.assigned_packages),
            "has_active_negotiation": self.active_negotiation is not None,
        }

        if current_state == self._last_serialized_state:
            return None

        self._last_serialized_state = current_state.copy()
        return current_state

    def serialize_full(self) -> dict[str, Any]:
        """Return complete agent state for state snapshot."""
        return {
            "id": str(self.id),
            "kind": self.kind,
            "balance_ducats": self.balance_ducats,
            "package_queue": [str(pid) for pid in self.package_queue],
            "assigned_packages": {
                str(pid): str(aid) for pid, aid in self.assigned_packages.items()
            },
            "known_packages_count": len(self.known_packages),
            "active_negotiation": (
                {
                    "package_id": str(self.active_negotiation.package_id),
                    "status": self.active_negotiation.status.value,
                    "current_truck_idx": self.active_negotiation.current_truck_idx,
                    "candidates_count": len(self.active_negotiation.candidate_trucks),
                }
                if self.active_negotiation
                else None
            ),
            "inbox_count": len(self.inbox),
            "outbox_count": len(self.outbox),
            "tags": self.tags.copy(),
        }
