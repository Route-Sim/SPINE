"""Action processor for executing action requests."""

import logging
from typing import TYPE_CHECKING

from world.world import World

from ..handlers.base import HandlerContext
from ..state import SimulationState
from .action_parser import ActionRequest
from .action_registry import ActionRegistry

if TYPE_CHECKING:
    from ..queues import SignalQueue


class ActionProcessor:
    """Processor for executing action requests."""

    def __init__(
        self,
        registry: ActionRegistry,
        state: SimulationState,
        world: World,
        signal_queue: "SignalQueue",
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the action processor.

        Args:
            registry: Action registry mapping actions to handlers
            state: Simulation state
            world: World instance
            signal_queue: Signal queue for emitting signals
            logger: Logger instance
        """
        self.registry = registry
        self.state = state
        self.world = world
        self.signal_queue = signal_queue
        self.logger = logger or logging.getLogger(__name__)

    def process(self, action_request: ActionRequest) -> None:
        """Process an action request.

        Args:
            action_request: Action request to process

        Raises:
            ValueError: If action is unknown or parameters are invalid
            RuntimeError: If handler execution fails
        """
        action = action_request.action
        params = action_request.params

        self.logger.debug(f"Processing action: {action}")

        # Get handler from registry
        handler = self.registry.get_handler(action)
        if handler is None:
            error_msg = f"Unknown action: {action}"
            self.logger.warning(error_msg)
            self._emit_error(error_msg)
            raise ValueError(error_msg)

        # Create handler context
        context = HandlerContext(
            state=self.state,
            world=self.world,
            signal_queue=self.signal_queue,
            logger=self.logger,
        )

        # Execute handler
        try:
            handler(params, context)
        except ValueError as e:
            # Validation errors are expected - just log and emit error signal
            self.logger.warning(f"Validation error processing action {action}: {e}")
            self._emit_error(str(e))
            raise
        except Exception as e:
            # Unexpected errors - log with full traceback
            self.logger.error(f"Error processing action {action}: {e}", exc_info=True)
            self._emit_error(f"Action processing error: {e}")
            raise RuntimeError(f"Failed to process action {action}: {e}") from e

    def _emit_error(self, error_message: str) -> None:
        """Emit an error signal.

        Args:
            error_message: Error message to emit
        """
        # Import here to avoid circular import
        from ..queues import create_error_signal

        try:
            self.signal_queue.put(
                create_error_signal(error_message, self.state.current_tick), timeout=1.0
            )
        except Exception as e:
            self.logger.error(f"Failed to emit error signal: {e}")
