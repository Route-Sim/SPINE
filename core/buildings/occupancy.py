"""Base class for buildings that can hold agents with capacity limits."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from core.buildings.base import Building
from core.types import AgentID


@dataclass
class OccupiableBuilding(Building):
    """Base building class for facilities that can hold agents up to a capacity limit.

    Provides common functionality for buildings like Parking and GasStation
    that need to track which agents are currently occupying them.
    """

    capacity: int
    current_agents: set[AgentID] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Validate the occupancy configuration."""
        if self.capacity <= 0:
            raise ValueError(f"{self.__class__.__name__} capacity must be positive")
        if len(self.current_agents) > self.capacity:
            raise ValueError(f"{self.__class__.__name__} occupancy exceeds capacity")

    def has_space(self) -> bool:
        """Return True if additional agents can enter."""
        return len(self.current_agents) < self.capacity

    def enter(self, agent_id: AgentID) -> None:
        """Register an agent as occupying this facility.

        Args:
            agent_id: The agent to register

        Raises:
            ValueError: If agent is already present or facility is at capacity
        """
        if agent_id in self.current_agents:
            raise ValueError(f"Agent {agent_id} is already in {self.__class__.__name__}")
        if not self.has_space():
            raise ValueError(f"{self.__class__.__name__} is at full capacity")
        self.current_agents.add(agent_id)

    def leave(self, agent_id: AgentID) -> None:
        """Remove an agent from the occupancy set.

        Args:
            agent_id: The agent to remove

        Raises:
            ValueError: If agent is not present in the facility
        """
        if agent_id not in self.current_agents:
            raise ValueError(f"Agent {agent_id} is not in {self.__class__.__name__}")
        self.current_agents.remove(agent_id)

    def assign_occupants(self, agents: Iterable[AgentID]) -> None:
        """Replace the occupancy set with a validated iterable of agents.

        Args:
            agents: Iterable of agent IDs to assign as occupants

        Raises:
            ValueError: If assignment exceeds capacity
        """
        occupants = {AgentID(agent) for agent in agents}
        if len(occupants) > self.capacity:
            raise ValueError(f"Occupant assignment exceeds {self.__class__.__name__} capacity")
        self.current_agents = occupants

    def to_dict(self) -> dict[str, Any]:
        """Serialize occupancy data to dictionary with deterministic occupant order."""
        data = super().to_dict()
        data["capacity"] = self.capacity
        data["current_agents"] = sorted(str(agent) for agent in self.current_agents)
        return data
