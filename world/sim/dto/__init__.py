"""DTOs for simulation domain."""

from .agent_dto import BuildingCreateDTO
from .simulation_dto import SimulationParamsDTO
from .statistics_dto import StatisticsBatchDTO, TickStatisticsDTO
from .step_result_dto import StepResultDTO, TickDataDTO
from .truck_dto import TruckCreateDTO, TruckStateDTO, TruckWatchFieldsDTO

__all__ = [
    "TruckCreateDTO",
    "BuildingCreateDTO",
    "TruckStateDTO",
    "TruckWatchFieldsDTO",
    "SimulationParamsDTO",
    "TickStatisticsDTO",
    "StatisticsBatchDTO",
    "StepResultDTO",
    "TickDataDTO",
]
