"""Registry for mapping canonical action identifiers to handler functions."""

from collections.abc import Callable
from typing import Any

from ..handlers.agent import AgentActionHandler
from ..handlers.map import MapActionHandler
from ..handlers.simulation import SimulationActionHandler
from ..handlers.state import StateActionHandler
from ..handlers.tick_rate import TickRateActionHandler
from ..queues import ActionType


class ActionRegistry:
    """Registry for mapping action identifiers to handler functions."""

    def __init__(self) -> None:
        """Initialize the registry with all action handlers."""
        self._handlers: dict[str, Callable[[dict[str, Any], Any], None]] = {}
        self._register_all()

    def _register_all(self) -> None:
        """Register all action handlers."""
        # Simulation actions
        self.register(ActionType.START, SimulationActionHandler.handle_start)
        self.register(ActionType.STOP, SimulationActionHandler.handle_stop)
        self.register(ActionType.PAUSE, SimulationActionHandler.handle_pause)
        self.register(ActionType.RESUME, SimulationActionHandler.handle_resume)

        # Tick rate actions
        self.register(ActionType.SET_TICK_RATE, TickRateActionHandler.handle_update)

        # Agent actions
        self.register(ActionType.ADD_AGENT, AgentActionHandler.handle_create)
        self.register(ActionType.DELETE_AGENT, AgentActionHandler.handle_delete)
        self.register(ActionType.MODIFY_AGENT, AgentActionHandler.handle_update)
        self.register(ActionType.DESCRIBE_AGENT, AgentActionHandler.handle_describe)

        # Map actions
        self.register(ActionType.EXPORT_MAP, MapActionHandler.handle_export)
        self.register(ActionType.IMPORT_MAP, MapActionHandler.handle_import)
        self.register(ActionType.CREATE_MAP, MapActionHandler.handle_create)

        # State actions
        self.register(ActionType.REQUEST_STATE, StateActionHandler.handle_request)

    def register(
        self, action: ActionType | str, handler: Callable[[dict[str, Any], Any], None]
    ) -> None:
        """Register a handler for an action.

        Args:
            action: Action identifier (`ActionType` or `<domain>.<action>` string)
            handler: Handler function that takes (params, context) and returns None
        """
        action_key = action.value if isinstance(action, ActionType) else action
        self._handlers[action_key] = handler

    def get_handler(self, action: ActionType | str) -> Callable[[dict[str, Any], Any], None] | None:
        """Get handler for an action.

        Args:
            action: Action identifier (`ActionType` or `<domain>.<action>` string)

        Returns:
            Handler function or None if not found
        """
        action_key = action.value if isinstance(action, ActionType) else action
        return self._handlers.get(action_key)

    def has_handler(self, action: ActionType | str) -> bool:
        """Check if a handler exists for an action.

        Args:
            action: Action identifier (`ActionType` or `<domain>.<action>` string)

        Returns:
            True if handler exists, False otherwise
        """
        action_key = action.value if isinstance(action, ActionType) else action
        return action_key in self._handlers


def create_default_registry() -> ActionRegistry:
    """Create and return a default action registry with all handlers registered.

    Returns:
        ActionRegistry instance with all default handlers registered
    """
    return ActionRegistry()
