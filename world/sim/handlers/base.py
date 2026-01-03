"""Base classes for action handlers."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from world.world import World

from ..state import SimulationState

if TYPE_CHECKING:
    from ..queues import SignalQueue


@dataclass
class HandlerContext:
    """Context passed to action handlers containing required dependencies."""

    state: SimulationState
    world: World
    signal_queue: "SignalQueue"
    logger: logging.Logger


class ActionHandler(ABC):
    """Abstract base class for action handlers."""

    @abstractmethod
    def handle(self, params: dict[str, Any], context: HandlerContext) -> None:
        """Execute the action.

        Args:
            params: Action parameters from the request
            context: Handler context with state, world, signal_queue, and logger

        Raises:
            ValueError: If required parameters are missing or invalid
            RuntimeError: If action execution fails
        """
        pass
