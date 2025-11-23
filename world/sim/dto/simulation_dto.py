"""DTOs for simulation control parameters and responses."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class SimulationParamsDTO(BaseModel):
    """DTO for simulation parameters used in actions and responses.

    Attributes:
        tick_rate: Ticks per second (how often we compute). Default 20 Hz.
        speed: Simulation speed multiplier (dt_s = speed). Default 1.0s per tick.
    """

    tick_rate: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Ticks per second (1-100 Hz)",
    )
    speed: float | None = Field(
        default=None,
        gt=0.0,
        le=10.0,
        description="Simulation speed multiplier (dt_s, 0.01-10.0 seconds per tick)",
    )

    @field_validator("tick_rate")
    @classmethod
    def validate_tick_rate(cls, v: int | None) -> int | None:
        """Ensure tick_rate is within valid range."""
        if v is not None and (v < 1 or v > 100):
            raise ValueError("tick_rate must be between 1 and 100")
        return v

    @field_validator("speed")
    @classmethod
    def validate_speed(cls, v: float | None) -> float | None:
        """Ensure speed is within valid range."""
        if v is not None and (v <= 0.0 or v > 10.0):
            raise ValueError("speed must be between 0.01 and 10.0")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: dict[str, Any] = {}
        if self.tick_rate is not None:
            result["tick_rate"] = self.tick_rate
        if self.speed is not None:
            result["speed"] = self.speed
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationParamsDTO":
        """Create DTO from dictionary with optional fields."""
        return cls(
            tick_rate=data.get("tick_rate"),
            speed=data.get("speed"),
        )
