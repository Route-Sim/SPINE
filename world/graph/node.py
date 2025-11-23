from dataclasses import dataclass, field

from core.buildings.base import Building
from core.types import BuildingID, NodeID


@dataclass
class Node:
    id: NodeID
    x: float
    y: float
    buildings: list[Building] = field(default_factory=list)
    _buildings_by_type: dict[type[Building], list[Building]] = field(
        default_factory=dict, init=False, repr=False
    )
    _building_counts_by_type: dict[type[Building], int] = field(
        default_factory=dict, init=False, repr=False
    )

    def add_building(self, building: Building) -> None:
        """Add a building to this node.

        Maintains the flat list, type-indexed dictionary, and count index for O(1) lookups.
        """
        self.buildings.append(building)
        # Update type index
        building_type = type(building)
        if building_type not in self._buildings_by_type:
            self._buildings_by_type[building_type] = []
        self._buildings_by_type[building_type].append(building)
        # Update count index
        self._building_counts_by_type[building_type] = (
            self._building_counts_by_type.get(building_type, 0) + 1
        )

    def get_buildings(self) -> list[Building]:
        """Get all buildings at this node."""
        return self.buildings

    def get_buildings_by_type(self, building_type: type[Building]) -> list[Building]:
        """Get all buildings of a specific type at this node.

        O(1) access using type index.

        Args:
            building_type: The type of building to retrieve (e.g., Parking, Site)

        Returns:
            List of buildings of the specified type (empty list if none found)
        """
        return self._buildings_by_type.get(building_type, [])

    def get_building_count_by_type(self, building_type: type[Building]) -> int:
        """Get the count of buildings of a specific type at this node.

        O(1) access using count index. More efficient than len(get_buildings_by_type()).

        Args:
            building_type: The type of building to count (e.g., Parking, Site)

        Returns:
            Number of buildings of the specified type at this node
        """
        return self._building_counts_by_type.get(building_type, 0)

    def has_building_type(self, building_type: type[Building]) -> bool:
        """Check if this node has any buildings of the specified type.

        O(1) check using type index.

        Args:
            building_type: The type of building to check for

        Returns:
            True if at least one building of this type exists at this node
        """
        return (
            building_type in self._buildings_by_type
            and len(self._buildings_by_type[building_type]) > 0
        )

    def remove_building(self, building_id: BuildingID) -> None:
        """Remove a building from this node by ID.

        Updates the flat list, type index, and count index.
        """
        building = next(b for b in self.buildings if b.id == building_id)
        self.buildings.remove(building)
        # Update type index
        building_type = type(building)
        if building_type in self._buildings_by_type:
            self._buildings_by_type[building_type].remove(building)
            # Clean up empty type lists
            if not self._buildings_by_type[building_type]:
                del self._buildings_by_type[building_type]
        # Update count index
        if building_type in self._building_counts_by_type:
            self._building_counts_by_type[building_type] -= 1
            # Clean up zero counts
            if self._building_counts_by_type[building_type] <= 0:
                del self._building_counts_by_type[building_type]

    def get_building(self, building_id: BuildingID) -> Building:
        """Get a building by ID."""
        return next(building for building in self.buildings if building.id == building_id)
