"""Handler for state request actions."""

from typing import Any

from ..queues import (
    create_error_signal,
    create_full_agent_data_signal,
    create_full_map_data_signal,
    create_state_snapshot_end_signal,
    create_state_snapshot_start_signal,
)
from .base import HandlerContext


def _emit_error(context: HandlerContext, error_message: str) -> None:
    """Emit an error signal."""
    try:
        context.signal_queue.put(
            create_error_signal(error_message, context.state.current_tick), timeout=1.0
        )
    except Exception as e:
        context.logger.error(f"Failed to emit error signal: {e}")


def _emit_state_snapshot(context: HandlerContext) -> None:
    """Emit complete state snapshot signals."""
    try:
        # Emit start signal
        context.signal_queue.put(create_state_snapshot_start_signal(), timeout=1.0)

        # Get full state from world
        full_state = context.world.get_full_state()

        # Emit map data
        context.signal_queue.put(create_full_map_data_signal(full_state["graph"]), timeout=1.0)

        # Emit agent data for each agent
        for agent_data in full_state["agents"]:
            context.signal_queue.put(create_full_agent_data_signal(agent_data), timeout=1.0)

        # Emit end signal
        context.signal_queue.put(create_state_snapshot_end_signal(), timeout=1.0)

        context.logger.info("State snapshot emitted successfully")

    except Exception as e:
        context.logger.error(f"Error emitting state snapshot: {e}", exc_info=True)
        _emit_error(context, f"Failed to emit state snapshot: {e}")


class StateActionHandler:
    """Handler for state request actions."""

    @staticmethod
    def handle_request(_params: dict[str, Any], context: HandlerContext) -> None:
        """Handle request state action.

        Args:
            _params: Action parameters (unused)
            context: Handler context
        """
        _emit_state_snapshot(context)
        context.logger.info("State snapshot requested and emitted")
