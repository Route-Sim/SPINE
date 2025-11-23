"""Handler for simulation control actions (start, stop, pause, resume)."""

from typing import Any

from world.sim.dto.simulation_dto import SimulationParamsDTO

from ..queues import (
    create_simulation_paused_signal,
    create_simulation_resumed_signal,
    create_simulation_started_signal,
    create_simulation_stopped_signal,
    create_simulation_updated_signal,
)
from .base import HandlerContext


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
            params: Action parameters (optional 'tick_rate' and 'speed')
            context: Handler context
        """
        # Parse parameters using DTO
        sim_params = SimulationParamsDTO.from_dict(params)

        # Apply tick_rate if provided
        if sim_params.tick_rate is not None:
            context.state.set_tick_rate(float(sim_params.tick_rate))

        # Apply speed (dt_s) if provided
        if sim_params.speed is not None:
            context.state.set_dt_s(sim_params.speed)
            # Update world's dt_s if available
            if context.world is not None:
                context.world.dt_s = sim_params.speed

        context.state.start()

        # Create response DTO with current values
        response_params = SimulationParamsDTO(
            tick_rate=int(context.state.tick_rate),
            speed=context.state.dt_s,
        )
        _emit_signal(context, create_simulation_started_signal(response_params))

        context.logger.info(
            f"Simulation started with tick rate: {context.state.tick_rate}, speed: {context.state.dt_s}"
        )

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

    @staticmethod
    def handle_update(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle simulation update action (e.g., tick rate and speed changes).

        Args:
            params: Action parameters (optional 'tick_rate' and 'speed')
            context: Handler context

        Raises:
            ValueError: If both tick_rate and speed are missing or invalid
        """
        # Parse parameters using DTO
        sim_params = SimulationParamsDTO.from_dict(params)

        # At least one parameter must be provided
        if sim_params.tick_rate is None and sim_params.speed is None:
            raise ValueError("At least one of 'tick_rate' or 'speed' must be provided")

        # Apply tick_rate if provided
        if sim_params.tick_rate is not None:
            context.state.set_tick_rate(float(sim_params.tick_rate))

        # Apply speed (dt_s) if provided
        if sim_params.speed is not None:
            context.state.set_dt_s(sim_params.speed)
            # Update world's dt_s if available
            if context.world is not None:
                context.world.dt_s = sim_params.speed

        # Create response DTO with current values
        response_params = SimulationParamsDTO(
            tick_rate=int(context.state.tick_rate),
            speed=context.state.dt_s,
        )
        _emit_signal(context, create_simulation_updated_signal(response_params))

        context.logger.info(
            f"Simulation updated: tick rate={context.state.tick_rate}, speed={context.state.dt_s}"
        )
