"""Handler for tick rate update actions."""

from typing import Any

from .base import HandlerContext


class TickRateActionHandler:
    """Handler for tick rate actions."""

    @staticmethod
    def handle_update(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle tick rate update action.

        Args:
            params: Action parameters (required 'tick_rate')
            context: Handler context

        Raises:
            ValueError: If tick_rate is missing or invalid
        """
        if "tick_rate" not in params:
            raise ValueError("tick_rate is required for tick_rate.update action")

        tick_rate = params["tick_rate"]
        if not isinstance(tick_rate, int | float):
            raise ValueError("tick_rate must be a number")

        context.state.set_tick_rate(float(tick_rate))
        context.logger.info(f"Tick rate set to: {context.state.tick_rate}")
