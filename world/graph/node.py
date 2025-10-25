from dataclasses import dataclass, field

from agents.buildings.building import Building
from core.types import AgentID, NodeID


@dataclass
class Node:
    id: NodeID
    x: float
    y: float
    buildings: list[Building] = field(default_factory=list)

    def add_building(self, building: Building) -> None:
        self.buildings.append(building)

    def get_buildings(self) -> list[Building]:
        return self.buildings

    def remove_building(self, building_id: AgentID) -> None:
        self.buildings.remove(
            next(building for building in self.buildings if building.id == building_id)
        )

    def get_building(self, building_id: AgentID) -> Building:
        return next(building for building in self.buildings if building.id == building_id)
