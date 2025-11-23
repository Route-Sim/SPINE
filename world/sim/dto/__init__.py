"""DTOs for simulation domain."""

from .agent_dto import BuildingCreateDTO, TruckCreateDTO
from .truck_dto import TruckStateDTO, TruckWatchFieldsDTO

__all__ = ["TruckCreateDTO", "BuildingCreateDTO", "TruckStateDTO", "TruckWatchFieldsDTO"]
