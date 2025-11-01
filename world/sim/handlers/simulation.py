"""Handler for simulation control actions (start, stop, pause, resume)."""

from typing import Any

from ..queues import (
    create_error_signal,
    create_full_agent_data_signal,
    create_full_map_data_signal,
    create_simulation_paused_signal,
    create_simulation_resumed_signal,
    create_simulation_started_signal,
    create_simulation_stopped_signal,
    create_state_snapshot_end_signal,
    create_state_snapshot_start_signal,
)
from .base import HandlerContext


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


def _emit_error(context: HandlerContext, error_message: str) -> None:
    """Emit an error signal."""
    try:
        context.signal_queue.put(
            create_error_signal(error_message, context.state.current_tick), timeout=1.0
        )
    except Exception as e:
        context.logger.error(f"Failed to emit error signal: {e}")


def _emit_signal(context: HandlerContext, signal: Any) -> None:
    """Emit a signal to the signal queue."""
    try:
        context.signal_queue.put(signal, timeout=1.0)
    except Exception as e:
        context.logger.error(f"Failed to emit signal: {e}")


class SimulationActionHandler:
    """Handler for simulation control actions."""

    @staticmethod
    def handle_start(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle start simulation action.

        Args:
            params: Action parameters (optional 'tick_rate')
            context: Handler context
        """
        # tick_rate is optional for simulation.start
        if "tick_rate" in params:
            tick_rate = params["tick_rate"]
            if not isinstance(tick_rate, int | float):
                raise ValueError("tick_rate must be a number")
            context.state.set_tick_rate(float(tick_rate))

        context.state.start()
        tick_rate_int = int(context.state.tick_rate) if context.state.tick_rate else None
        _emit_signal(context, create_simulation_started_signal(tick_rate=tick_rate_int))

        # Emit state snapshot when simulation starts
        _emit_state_snapshot(context)

        context.logger.info(f"Simulation started with tick rate: {context.state.tick_rate}")

    @staticmethod
    def handle_stop(_params: dict[str, Any], context: HandlerContext) -> None:
        """Handle stop simulation action.

        Args:
            _params: Action parameters (unused)
            context: Handler context
        """
        context.state.stop()
        _emit_signal(context, create_simulation_stopped_signal())
        context.logger.info("Simulation stopped")

    @staticmethod
    def handle_pause(_params: dict[str, Any], context: HandlerContext) -> None:
        """Handle pause simulation action.

        Args:
            _params: Action parameters (unused)
            context: Handler context
        """
        if context.state.running:
            context.state.pause()
            _emit_signal(context, create_simulation_paused_signal())
            context.logger.info("Simulation paused")

    @staticmethod
    def handle_resume(_params: dict[str, Any], context: HandlerContext) -> None:
        """Handle resume simulation action.

        Args:
            _params: Action parameters (unused)
            context: Handler context
        """
        if context.state.running and context.state.paused:
            context.state.resume()
            _emit_signal(context, create_simulation_resumed_signal())
            context.logger.info("Simulation resumed")
