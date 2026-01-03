"""Handler for simulation control actions (start, stop, pause, resume)."""

import base64
import binascii
import json
from typing import Any

from world.sim.dto.simulation_dto import SimulationParamsDTO

from ..queues import (
    create_error_signal,
    create_simulation_paused_signal,
    create_simulation_resumed_signal,
    create_simulation_started_signal,
    create_simulation_state_exported_signal,
    create_simulation_state_imported_signal,
    create_simulation_stopped_signal,
    create_simulation_updated_signal,
)
from .base import HandlerContext

# File extension for SPINE simulation save files
SAVE_FILE_EXTENSION = ".ssave"


def _emit_signal(context: HandlerContext, signal: Any) -> None:
    """Emit a signal to the signal queue."""
    try:
        context.signal_queue.put(signal, timeout=1.0)
    except Exception as e:
        context.logger.error(f"Failed to emit signal: {e}")


def _emit_error(context: HandlerContext, error_message: str) -> None:
    """Emit an error signal."""
    try:
        context.signal_queue.put(
            create_error_signal(error_message, context.state.current_tick), timeout=1.0
        )
    except Exception as e:
        context.logger.error(f"Failed to emit error signal: {e}")


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

        # Apply tick_rate if provided (this will recalculate dt_s if speed is already set)
        if sim_params.tick_rate is not None:
            context.state.set_tick_rate(float(sim_params.tick_rate))

        # Apply speed if provided (this will recalculate dt_s based on current tick_rate)
        if sim_params.speed is not None:
            context.state.set_speed(float(sim_params.speed))
            # Update world's dt_s if available
            if context.world is not None:
                context.world.dt_s = context.state.dt_s

        context.state.start()

        # Create response DTO with current values
        response_params = SimulationParamsDTO(
            tick_rate=int(context.state.tick_rate),
            speed=context.state.speed,
        )
        _emit_signal(context, create_simulation_started_signal(response_params))

        context.logger.info(
            f"Simulation started with tick rate: {context.state.tick_rate}, speed: {context.state.speed}, dt_s: {context.state.dt_s}"
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

        # Apply tick_rate if provided (this will recalculate dt_s if speed is already set)
        if sim_params.tick_rate is not None:
            context.state.set_tick_rate(float(sim_params.tick_rate))

        # Apply speed if provided (this will recalculate dt_s based on current tick_rate)
        if sim_params.speed is not None:
            context.state.set_speed(float(sim_params.speed))
            # Update world's dt_s if available
            if context.world is not None:
                context.world.dt_s = context.state.dt_s

        # Create response DTO with current values
        response_params = SimulationParamsDTO(
            tick_rate=int(context.state.tick_rate),
            speed=context.state.speed,
        )
        _emit_signal(context, create_simulation_updated_signal(response_params))

        context.logger.info(
            f"Simulation updated: tick rate={context.state.tick_rate}, speed={context.state.speed}, dt_s={context.state.dt_s}"
        )

    @staticmethod
    def handle_export_state(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle export simulation state action (sends base64-encoded save file via WebSocket).

        Args:
            params: Action parameters (optional 'filename' for custom name)
            context: Handler context
        """
        try:
            # Get optional filename from params
            filename = params.get("filename", "save")
            if not filename.endswith(SAVE_FILE_EXTENSION):
                filename += SAVE_FILE_EXTENSION

            # Export complete world state
            state_data = context.world.get_full_state()

            # Convert to JSON and encode to base64
            json_str = json.dumps(state_data, indent=2)
            file_content_base64 = base64.b64encode(json_str.encode("utf-8")).decode("ascii")

            _emit_signal(
                context,
                create_simulation_state_exported_signal(
                    filename=filename, file_content=file_content_base64
                ),
            )
            context.logger.info(f"Simulation state exported via WebSocket: {filename}")
        except Exception as e:
            context.logger.error(f"Unexpected error exporting state: {e}", exc_info=True)
            _emit_error(context, f"Unexpected error exporting state: {e}")
            raise

    @staticmethod
    def handle_import_state(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle import simulation state action (receives base64-encoded save file via WebSocket).

        Args:
            params: Action parameters (required 'file_content' base64 string, optional 'filename')
            context: Handler context

        Raises:
            ValueError: If file_content is missing
        """
        if "file_content" not in params:
            raise ValueError("file_content is required for simulation.import_state action")

        file_content_base64 = params["file_content"]
        if not isinstance(file_content_base64, str):
            raise ValueError("file_content must be a base64-encoded string")

        filename = params.get("filename", "unknown.ssave")

        # Stop simulation if it's running
        if context.state.running:
            context.logger.info("Stopping simulation to import state")
            context.state.stop()

        try:
            # Decode base64 and parse JSON
            json_str = base64.b64decode(file_content_base64).decode("utf-8")
            state_data = json.loads(json_str)

            # Restore world state from dictionary
            context.world.restore_from_state(state_data)
            _emit_signal(context, create_simulation_state_imported_signal(filename))
            context.logger.info(f"Simulation state imported via WebSocket: {filename}")
        except (binascii.Error, UnicodeDecodeError) as e:
            context.logger.error(f"Failed to decode base64 state data: {e}")
            _emit_error(context, f"Invalid base64 encoding: {e}")
            raise ValueError(f"Invalid base64 encoding: {e}") from e
        except json.JSONDecodeError as e:
            context.logger.error(f"Failed to parse state JSON: {e}")
            _emit_error(context, f"Invalid JSON format: {e}")
            raise ValueError(f"Invalid JSON format: {e}") from e
        except ValueError as e:
            context.logger.error(f"Failed to import state: {e}")
            _emit_error(context, f"Failed to import state: {e}")
            raise
        except Exception as e:
            context.logger.error(f"Unexpected error importing state: {e}", exc_info=True)
            _emit_error(context, f"Unexpected error importing state: {e}")
            raise
