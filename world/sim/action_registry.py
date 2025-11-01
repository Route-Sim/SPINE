"""Registry for mapping action strings to handler functions."""

from collections.abc import Callable
from typing import Any

from .handlers.agent import AgentActionHandler
from .handlers.map import MapActionHandler
from .handlers.simulation import SimulationActionHandler
from .handlers.state import StateActionHandler
from .handlers.tick_rate import TickRateActionHandler


class ActionRegistry:
    """Registry for mapping action strings to handler functions."""

    def __init__(self) -> None:
        """Initialize the registry with all action handlers."""
        self._handlers: dict[str, Callable[[dict[str, Any], Any], None]] = {}
        self._register_all()

    def _register_all(self) -> None:
        """Register all action handlers."""
        # Simulation actions
        self.register("simulation.start", SimulationActionHandler.handle_start)
        self.register("simulation.stop", SimulationActionHandler.handle_stop)
        self.register("simulation.pause", SimulationActionHandler.handle_pause)
        self.register("simulation.resume", SimulationActionHandler.handle_resume)

        # Tick rate actions
        self.register("tick_rate.update", TickRateActionHandler.handle_update)

        # Agent actions
        self.register("agent.create", AgentActionHandler.handle_create)
        self.register("agent.delete", AgentActionHandler.handle_delete)
        self.register("agent.update", AgentActionHandler.handle_update)

        # Map actions
        self.register("map.export", MapActionHandler.handle_export)
        self.register("map.import", MapActionHandler.handle_import)
        self.register("map.create", MapActionHandler.handle_create)

        # State actions
        self.register("state.request", StateActionHandler.handle_request)

    def register(self, action: str, handler: Callable[[dict[str, Any], Any], None]) -> None:
        """Register a handler for an action.

        Args:
            action: Action string in format "domain.action"
            handler: Handler function that takes (params, context) and returns None
        """
        self._handlers[action] = handler

    def get_handler(self, action: str) -> Callable[[dict[str, Any], Any], None] | None:
        """Get handler for an action.

        Args:
            action: Action string in format "domain.action"

        Returns:
            Handler function or None if not found
        """
        return self._handlers.get(action)

    def has_handler(self, action: str) -> bool:
        """Check if a handler exists for an action.

        Args:
            action: Action string in format "domain.action"

        Returns:
            True if handler exists, False otherwise
        """
        return action in self._handlers


def create_default_registry() -> ActionRegistry:
    """Create and return a default action registry with all handlers registered.

    Returns:
        ActionRegistry instance with all default handlers registered
    """
    return ActionRegistry()
