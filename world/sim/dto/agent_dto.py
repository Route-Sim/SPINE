"""DTOs for agent creation and management."""

from pydantic import BaseModel, Field, field_validator

from agents.transports.truck import Truck
from core.types import AgentID, NodeID


class TruckCreateDTO(BaseModel):
    """DTO for truck creation parameters."""

    max_speed_kph: float = Field(default=100.0, gt=0.0, description="Maximum speed in km/h")
    risk_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Risk tolerance for tachograph parking search (0=cautious, 1=risky)",
    )
    initial_balance_ducats: float = Field(
        default=0.0, description="Starting financial balance in ducats"
    )

    @field_validator("max_speed_kph")
    @classmethod
    def validate_max_speed(cls, v: float) -> float:
        """Ensure max_speed_kph is positive."""
        if v <= 0:
            raise ValueError("max_speed_kph must be a positive number")
        return v

    def to_truck(self, agent_id: AgentID, kind: str, spawn_node: NodeID) -> Truck:
        """Create a Truck instance from this DTO.

        Args:
            agent_id: Unique agent identifier
            kind: Agent kind string (typically "truck")
            spawn_node: Node where truck should spawn

        Returns:
            Configured Truck instance
        """
        return Truck(
            id=agent_id,
            kind=kind,
            max_speed_kph=self.max_speed_kph,
            current_speed_kph=0.0,
            current_node=spawn_node,
            current_edge=None,
            edge_progress_m=0.0,
            route=[],
            destination=None,
            risk_factor=self.risk_factor,
            balance_ducats=self.initial_balance_ducats,
        )


class BuildingCreateDTO(BaseModel):
    """DTO for building agent creation parameters.

    Currently buildings have no specific parameters beyond base agent fields.
    """

    pass
