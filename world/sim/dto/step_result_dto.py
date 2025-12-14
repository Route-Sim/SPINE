"""DTOs for simulation step results."""

from typing import Any

from pydantic import BaseModel, Field


class TickDataDTO(BaseModel):
    """DTO for tick time and day information.

    Represents the simulation time state for a given tick, calculated from
    elapsed simulation time starting at 12:00 on day 1.

    Attributes:
        tick: The current simulation tick number.
        time: Current time in 24-hour format (0.0-23.999...).
        day: Current simulation day (starts at 1).
    """

    tick: int = Field(description="Current simulation tick number")
    time: float = Field(ge=0.0, lt=24.0, description="Current time in 24-hour format")
    day: int = Field(ge=1, description="Current simulation day (starts at 1)")


class StepResultDTO(BaseModel):
    """DTO for the result of a simulation step.

    Captures all state changes from a single tick for UI synchronization.

    Attributes:
        events: List of world events that occurred during the step.
        agent_diffs: List of agent state changes (None entries filtered out).
        building_updates: List of building state changes (only dirty buildings).
        tick_data: Time and day information for this tick.
    """

    events: list[dict[str, Any]] = Field(
        default_factory=list, description="World events from this tick"
    )
    agent_diffs: list[dict[str, Any] | None] = Field(
        default_factory=list, description="Agent state diffs"
    )
    building_updates: list[dict[str, Any]] = Field(
        default_factory=list, description="Building state updates"
    )
    tick_data: TickDataDTO = Field(description="Time and day information for this tick")

    def get_events(self) -> list[dict[str, Any]]:
        """Get list of world events."""
        return self.events

    def get_agent_diffs(self) -> list[dict[str, Any]]:
        """Get list of non-None agent diffs."""
        return [diff for diff in self.agent_diffs if diff is not None]

    def get_building_updates(self) -> list[dict[str, Any]]:
        """Get list of building updates."""
        return self.building_updates

    def has_events(self) -> bool:
        """Check if there are any events."""
        return len(self.events) > 0

    def has_agent_updates(self) -> bool:
        """Check if there are any agent updates."""
        return any(diff is not None for diff in self.agent_diffs)

    def has_building_updates(self) -> bool:
        """Check if there are any building updates."""
        return len(self.building_updates) > 0

    def get_tick_data(self) -> TickDataDTO:
        """Get tick time and day information."""
        return self.tick_data
