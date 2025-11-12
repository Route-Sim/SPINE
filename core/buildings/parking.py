"""Parking building type for staging transport agents."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from core.buildings.base import Building
from core.types import AgentID, BuildingID


@dataclass
class Parking(Building):
    """Parking building that tracks parked agents up to a capacity limit."""

    capacity: int
    current_agents: set[AgentID] = field(default_factory=set)
    TYPE: ClassVar[str] = "parking"

    def __post_init__(self) -> None:
        """Validate the parking configuration."""
        if self.capacity <= 0:
            raise ValueError("Parking capacity must be positive")
        if len(self.current_agents) > self.capacity:
            raise ValueError("Parking occupancy exceeds capacity")

    def has_space(self) -> bool:
        """Return True if additional agents can park."""
        return len(self.current_agents) < self.capacity

    def park(self, agent_id: AgentID) -> None:
        """Register an agent as parked in this facility."""
        if agent_id in self.current_agents:
            raise ValueError(f"Agent {agent_id} is already parked")
        if not self.has_space():
            raise ValueError("Parking is at full capacity")
        self.current_agents.add(agent_id)

    def release(self, agent_id: AgentID) -> None:
        """Remove an agent from the parking occupancy set."""
        if agent_id not in self.current_agents:
            raise ValueError(f"Agent {agent_id} is not parked here")
        self.current_agents.remove(agent_id)

    def assign_occupants(self, agents: Iterable[AgentID]) -> None:
        """Replace the occupancy set with a validated iterable of agents."""
        occupants = {AgentID(agent) for agent in agents}
        if len(occupants) > self.capacity:
            raise ValueError("Occupant assignment exceeds parking capacity")
        self.current_agents = occupants

    def to_dict(self) -> dict[str, Any]:
        """Serialize parking to dictionary with deterministic occupant order."""
        data = super().to_dict()
        data["capacity"] = self.capacity
        data["current_agents"] = sorted(str(agent) for agent in self.current_agents)
        return data

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
