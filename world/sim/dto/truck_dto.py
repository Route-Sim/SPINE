"""DTOs for truck creation and state serialization.

This module defines DTOs for truck management:
- TruckCreateDTO: Parameters for creating new trucks
- TruckWatchFieldsDTO: Position and navigation fields that trigger serialization
- TruckStateDTO: Complete state payload returned in diffs

Only changes to watch fields trigger diff emission, but diffs always contain all fields.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.types import AgentID, EdgeID, NodeID, PackageID

if TYPE_CHECKING:
    from agents.transports.truck import Truck


class TruckCreateDTO(BaseModel):
    """DTO for truck creation parameters."""

    max_speed_kph: float = Field(default=100.0, gt=0.0, description="Maximum speed in km/h")
    capacity: float = Field(
        default=24.0,
        ge=4.0,
        le=45.0,
        description="Truck cargo capacity (unitless, typically represents tonnes)",
    )
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

    def to_truck(self, agent_id: AgentID, kind: str, spawn_node: NodeID) -> "Truck":
        """Create a Truck instance from this DTO.

        Args:
            agent_id: Unique agent identifier
            kind: Agent kind string (typically "truck")
            spawn_node: Node where truck should spawn

        Returns:
            Configured Truck instance
        """
        # Import here to avoid circular dependency
        from agents.transports.truck import Truck

        return Truck(
            id=agent_id,
            kind=kind,
            max_speed_kph=self.max_speed_kph,
            capacity=self.capacity,
            current_speed_kph=0.0,
            current_node=spawn_node,
            current_edge=None,
            edge_progress_m=0.0,
            route=[],
            destination=None,
            risk_factor=self.risk_factor,
            balance_ducats=self.initial_balance_ducats,
        )


class TruckWatchFieldsDTO(BaseModel):
    """DTO for truck fields that trigger serialization when changed.

    These are position and navigation fields that represent meaningful state
    changes requiring frontend updates. Changes to these fields trigger
    a full state diff emission.

    Fields:
        current_node: Node ID if truck is at a node
        current_edge: Edge ID if truck is on an edge
        current_speed_kph: Current speed (changes when entering edges)
        route: Remaining nodes to visit
        route_start_node: Origin node for current route
        route_end_node: Destination node for current route
        loaded_packages: Currently loaded package IDs
    """

    model_config = ConfigDict(frozen=True)

    current_node: NodeID | None
    current_edge: EdgeID | None
    current_speed_kph: float
    route: tuple[NodeID, ...]  # Immutable tuple for hashing
    route_start_node: NodeID | None
    route_end_node: NodeID | None
    loaded_packages: tuple[PackageID, ...]  # Immutable tuple for hashing


class TruckStateDTO(BaseModel):
    """DTO for complete truck state returned in diff payloads.

    Contains all truck fields including watch fields (position/navigation)
    and non-watch fields (tachograph counters, metadata). This is the
    complete state snapshot sent to the frontend when watch fields change.

    Fields:
        id: Agent unique identifier
        kind: Agent kind string ("truck")
        max_speed_kph: Maximum speed capability
        capacity: Cargo capacity (unitless)
        loaded_packages: List of loaded package IDs
        current_speed_kph: Current speed on edge
        current_node: Node ID if at a node
        current_edge: Edge ID if on an edge
        route: Remaining nodes to visit
        route_start_node: Route origin
        route_end_node: Route destination
        current_building_id: Parking building association
        driving_time_s: Accumulated driving time
        resting_time_s: Accumulated rest time
        is_resting: Currently in mandatory rest
        balance_ducats: Financial balance
        risk_factor: Risk tolerance (0.0-1.0)
        is_seeking_parking: Actively seeking parking
        original_destination: Preserved destination when diverting
    """

    model_config = ConfigDict(frozen=True)

    id: AgentID
    kind: str
    max_speed_kph: float
    capacity: float
    loaded_packages: list[PackageID]
    current_speed_kph: float
    current_node: NodeID | None
    current_edge: EdgeID | None
    route: list[NodeID]
    route_start_node: NodeID | None
    route_end_node: NodeID | None
    current_building_id: str | None
    # Tachograph fields
    driving_time_s: float
    resting_time_s: float
    is_resting: bool
    balance_ducats: float
    risk_factor: float
    is_seeking_parking: bool
    original_destination: NodeID | None
