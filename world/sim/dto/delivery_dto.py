"""DTOs for delivery task management and broker negotiation."""

from pydantic import BaseModel, ConfigDict, Field

from core.types import AgentID, PackageID, SiteID, TaskStatus, TaskType


class DeliveryTaskDTO(BaseModel):
    """DTO for serializing delivery tasks."""

    model_config = ConfigDict(frozen=True)

    site_id: str
    task_type: TaskType
    package_ids: list[str] = Field(default_factory=list)
    estimated_arrival_tick: int = 0
    status: TaskStatus = TaskStatus.PENDING


class PickupProposalDTO(BaseModel):
    """DTO for broker pickup proposal sent to trucks.

    Contains all information a truck needs to evaluate whether it can
    accept the pickup job.
    """

    model_config = ConfigDict(frozen=True)

    package_id: PackageID
    origin_site_id: SiteID
    destination_site_id: SiteID
    package_size: float  # Size in tonnes
    package_value: float  # Value in currency
    pickup_deadline_tick: int
    delivery_deadline_tick: int


class PickupResponseDTO(BaseModel):
    """DTO for truck response to broker proposal.

    Trucks respond with either accept or reject, along with their
    estimated times if accepting.
    """

    model_config = ConfigDict(frozen=True)

    package_id: PackageID
    accepted: bool
    estimated_pickup_tick: int | None = None
    estimated_delivery_tick: int | None = None
    rejection_reason: str | None = None


class AssignmentConfirmationDTO(BaseModel):
    """DTO for broker confirmation of package assignment to a truck.

    Sent to truck after broker selects it as the winner of negotiation.
    """

    model_config = ConfigDict(frozen=True)

    package_id: PackageID
    origin_site_id: SiteID
    destination_site_id: SiteID
    package_size: float
    pickup_deadline_tick: int
    delivery_deadline_tick: int


class DeliveryConfirmationDTO(BaseModel):
    """DTO for truck confirmation of package delivery.

    Sent to broker when truck successfully delivers a package.
    """

    model_config = ConfigDict(frozen=True)

    package_id: PackageID
    agent_id: AgentID
    delivery_tick: int
    on_time: bool
    delivery_site_id: SiteID
