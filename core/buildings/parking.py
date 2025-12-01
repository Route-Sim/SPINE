"""Parking building type for staging transport agents."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, ClassVar

from core.buildings.occupancy import OccupiableBuilding
from core.types import AgentID, BuildingID


@dataclass
class Parking(OccupiableBuilding):
    """Parking building that tracks parked agents up to a capacity limit.

    Inherits agent storage functionality from OccupiableBuilding.
    Provides `park()` and `release()` as domain-specific aliases for
    `enter()` and `leave()`.
    """

    TYPE: ClassVar[str] = "parking"

    def park(self, agent_id: AgentID) -> None:
        """Register an agent as parked in this facility.

        This is a domain-specific alias for `enter()`.

        Args:
            agent_id: The agent to park

        Raises:
            ValueError: If agent is already parked or parking is at capacity
        """
        self.enter(agent_id)

    def release(self, agent_id: AgentID) -> None:
        """Remove an agent from the parking occupancy set.

        This is a domain-specific alias for `leave()`.

        Args:
            agent_id: The agent to release

        Raises:
            ValueError: If agent is not parked here
        """
        self.leave(agent_id)

    def assign_occupants(self, agents: Iterable[AgentID]) -> None:
        """Replace the occupancy set with a validated iterable of agents.

        Overrides parent to use Parking-specific error messages.

        Args:
            agents: Iterable of agent IDs to assign as occupants

        Raises:
            ValueError: If assignment exceeds parking capacity
        """
        occupants = {AgentID(agent) for agent in agents}
        if len(occupants) > self.capacity:
            raise ValueError("Occupant assignment exceeds parking capacity")
        self.current_agents = occupants

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Parking":
        """Deserialize parking from dictionary."""
        agents_raw = data.get("current_agents", [])
        agents = {AgentID(agent) for agent in agents_raw}
        return cls(
            id=BuildingID(data["id"]),
            capacity=int(data["capacity"]),
            current_agents=agents,
        )
