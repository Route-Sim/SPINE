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

    def add_building(self, building: Building) -> None:
        """Add a building to this node.

        Maintains both the flat list and the type-indexed dictionary for O(1) type lookups.
        """
        self.buildings.append(building)
        # Update type index
        building_type = type(building)
        if building_type not in self._buildings_by_type:
            self._buildings_by_type[building_type] = []
        self._buildings_by_type[building_type].append(building)

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

        Updates both the flat list and the type index.
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

    def get_building(self, building_id: BuildingID) -> Building:
        """Get a building by ID."""
        return next(building for building in self.buildings if building.id == building_id)
