"""DTOs for simulation performance statistics."""

from pydantic import BaseModel, Field


class TickStatisticsDTO(BaseModel):
    """Statistics for a single simulation tick.

    Attributes:
        tick: Tick number
        action_time_ms: Time spent processing actions (milliseconds)
        step_time_ms: Time spent running simulation step (milliseconds)
        total_time_ms: Total processing time (milliseconds)
        target_tick_rate: Target ticks per second
        achieved_rate: Actual achieved rate (calculated from total_time_ms)
    """

    tick: int = Field(ge=0, description="Tick number")
    action_time_ms: float = Field(ge=0.0, description="Time spent processing actions (ms)")
    step_time_ms: float = Field(ge=0.0, description="Time spent running simulation step (ms)")
    total_time_ms: float = Field(ge=0.0, description="Total processing time (ms)")
    target_tick_rate: float = Field(gt=0.0, description="Target ticks per second")
    achieved_rate: float = Field(ge=0.0, description="Actual achieved rate (ticks per second)")

    def to_dict(self) -> dict[str, float | int]:
        """Convert to dictionary."""
        return {
            "tick": self.tick,
            "action_time_ms": self.action_time_ms,
            "step_time_ms": self.step_time_ms,
            "total_time_ms": self.total_time_ms,
            "target_tick_rate": self.target_tick_rate,
            "achieved_rate": self.achieved_rate,
        }


class StatisticsBatchDTO(BaseModel):
    """Batch of tick statistics for efficient storage.

    Attributes:
        batch_id: Unique batch identifier
        timestamp: Batch creation timestamp
        ticks: List of tick statistics
    """

    batch_id: int = Field(ge=0, description="Unique batch identifier")
    timestamp: float = Field(ge=0.0, description="Batch creation timestamp")
    ticks: list[TickStatisticsDTO] = Field(
        default_factory=list, description="List of tick statistics"
    )

    def to_dict(self) -> dict[str, int | float | list[dict[str, float | int]]]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "timestamp": self.timestamp,
            "ticks": [tick.to_dict() for tick in self.ticks],
        }
