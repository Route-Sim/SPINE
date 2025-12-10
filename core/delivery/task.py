"""Delivery task data structure for truck delivery queue."""

from dataclasses import dataclass, field
from typing import Any

from core.types import PackageID, SiteID, TaskStatus, TaskType


@dataclass
class DeliveryTask:
    """Represents a pickup or delivery task in a truck's delivery queue.

    Each task represents a stop at a site - either to pick up packages or
    to deliver packages. Multiple packages can be associated with a single
    task if they share the same origin (for pickup) or destination (for delivery).

    Attributes:
        site_id: The site where this task takes place
        task_type: Either PICKUP or DELIVERY
        package_ids: List of packages to load (pickup) or unload (delivery)
        estimated_arrival_tick: Estimated simulation tick when truck will arrive
        status: Current status of the task (PENDING, IN_PROGRESS, COMPLETED)
    """

    site_id: SiteID
    task_type: TaskType
    package_ids: list[PackageID] = field(default_factory=list)
    estimated_arrival_tick: int = 0
    status: TaskStatus = TaskStatus.PENDING

    def add_package(self, package_id: PackageID) -> None:
        """Add a package to this task.

        Args:
            package_id: Package ID to add

        Raises:
            ValueError: If package is already in this task
        """
        if package_id in self.package_ids:
            raise ValueError(f"Package {package_id} is already in this task")
        self.package_ids.append(package_id)

    def remove_package(self, package_id: PackageID) -> None:
        """Remove a package from this task.

        Args:
            package_id: Package ID to remove

        Raises:
            ValueError: If package is not in this task
        """
        if package_id not in self.package_ids:
            raise ValueError(f"Package {package_id} is not in this task")
        self.package_ids.remove(package_id)

    def is_empty(self) -> bool:
        """Check if this task has no packages."""
        return len(self.package_ids) == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize task to dictionary."""
        return {
            "site_id": str(self.site_id),
            "task_type": self.task_type.value,
            "package_ids": [str(pid) for pid in self.package_ids],
            "estimated_arrival_tick": self.estimated_arrival_tick,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeliveryTask":
        """Deserialize task from dictionary."""
        return cls(
            site_id=SiteID(data["site_id"]),
            task_type=TaskType(data["task_type"]),
            package_ids=[PackageID(pid) for pid in data.get("package_ids", [])],
            estimated_arrival_tick=data.get("estimated_arrival_tick", 0),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
        )
