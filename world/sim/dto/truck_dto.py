"""DTOs for truck state serialization with selective field comparison.

This module defines two DTOs for truck state management:
- TruckWatchFieldsDTO: Position and navigation fields that trigger serialization
- TruckStateDTO: Complete state payload returned in diffs

Only changes to watch fields trigger diff emission, but diffs always contain all fields.
"""

from pydantic import BaseModel, ConfigDict

from core.types import AgentID, EdgeID, NodeID


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
    """

    model_config = ConfigDict(frozen=True)

    current_node: NodeID | None
    current_edge: EdgeID | None
    current_speed_kph: float
    route: tuple[NodeID, ...]  # Immutable tuple for hashing
    route_start_node: NodeID | None
    route_end_node: NodeID | None


class TruckStateDTO(BaseModel):
    """DTO for complete truck state returned in diff payloads.

    Contains all truck fields including watch fields (position/navigation)
    and non-watch fields (tachograph counters, metadata). This is the
    complete state snapshot sent to the frontend when watch fields change.

    Fields:
        id: Agent unique identifier
        kind: Agent kind string ("truck")
        max_speed_kph: Maximum speed capability
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
