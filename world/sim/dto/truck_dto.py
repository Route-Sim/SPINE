"""DTOs for truck creation and state serialization.

This module defines DTOs for truck management:
- TruckCreateDTO: Parameters for creating new trucks
- TruckWatchFieldsDTO: Position and navigation fields that trigger serialization
- TruckStateDTO: Complete state payload returned in diffs

Only changes to watch fields trigger diff emission, but diffs always contain all fields.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.types import AgentID, BuildingID, EdgeID, NodeID, PackageID

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
        description="Risk tolerance for tachograph/fuel search (0=cautious, 1=risky)",
    )
    initial_balance_ducats: float = Field(
        default=0.0, description="Starting financial balance in ducats"
    )
    fuel_tank_capacity_l: float = Field(
        default=500.0,
        gt=0.0,
        description="Maximum fuel tank capacity in liters",
    )
    initial_fuel_l: float | None = Field(
        default=None,
        ge=0.0,
        description="Initial fuel level in liters (defaults to full tank if not specified)",
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

        # Default to full tank if initial_fuel_l not specified
        initial_fuel = (
            self.initial_fuel_l if self.initial_fuel_l is not None else self.fuel_tank_capacity_l
        )
        # Clamp to tank capacity
        initial_fuel = min(initial_fuel, self.fuel_tank_capacity_l)

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
            fuel_tank_capacity_l=self.fuel_tank_capacity_l,
            current_fuel_l=initial_fuel,
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
        current_building_id: Building ID (triggers update on building enter/leave)

    Note: fuel_level is NOT a watch field - it changes continuously but updates
    are only sent when other watch fields change.
    """

    model_config = ConfigDict(frozen=True)

    current_node: NodeID | None
    current_edge: EdgeID | None
    current_speed_kph: float
    route: tuple[NodeID, ...]  # Immutable tuple for hashing
    route_start_node: NodeID | None
    route_end_node: NodeID | None
    loaded_packages: tuple[PackageID, ...]  # Immutable tuple for hashing
    current_building_id: BuildingID | None  # Triggers update on building enter/leave


class TruckStateDTO(BaseModel):
    """DTO for complete truck state returned in diff payloads.

    Contains all truck fields including watch fields (position/navigation)
    and non-watch fields (tachograph counters, fuel levels, metadata). This is the
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
        current_building_id: Building association (parking or gas station)
        driving_time_s: Accumulated driving time
        resting_time_s: Accumulated rest time
        is_resting: Currently in mandatory rest
        balance_ducats: Financial balance
        risk_factor: Risk tolerance (0.0-1.0)
        is_seeking_parking: Actively seeking parking (for rest)
        is_seeking_idle_parking: Actively seeking parking (when idle, no tasks)
        original_destination: Preserved destination when diverting
        fuel_tank_capacity_l: Maximum fuel tank capacity
        current_fuel_l: Current fuel level
        co2_emitted_kg: Total CO2 emitted
        is_seeking_gas_station: Actively seeking gas station
        is_fueling: Currently fueling at gas station
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
    is_seeking_idle_parking: bool
    original_destination: NodeID | None
    # Fuel system fields
    fuel_tank_capacity_l: float
    current_fuel_l: float
    co2_emitted_kg: float
    is_seeking_gas_station: bool
    is_fueling: bool
