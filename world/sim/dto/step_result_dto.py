"""DTOs for simulation step results."""

from typing import Any

from pydantic import BaseModel, Field


class StepResultDTO(BaseModel):
    """DTO for the result of a simulation step.

    Captures all state changes from a single tick for UI synchronization.

    Attributes:
        events: List of world events that occurred during the step.
        agent_diffs: List of agent state changes (None entries filtered out).
        building_updates: List of building state changes (only dirty buildings).
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
