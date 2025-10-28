"""Thread-safe queue infrastructure for Backend communication."""

import queue
import threading
from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator


class ActionType(str, Enum):
    """Types of actions that can be sent from Frontend to Backend."""

    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    SET_TICK_RATE = "set_tick_rate"
    ADD_AGENT = "add_agent"
    DELETE_AGENT = "delete_agent"
    MODIFY_AGENT = "modify_agent"
    EXPORT_MAP = "export_map"
    IMPORT_MAP = "import_map"
    REQUEST_STATE = "request_state"


class SignalType(str, Enum):
    """Types of signals that can be emitted from Backend to Frontend."""

    TICK_START = "tick_start"
    TICK_END = "tick_end"
    AGENT_UPDATE = "agent_update"
    WORLD_EVENT = "world_event"
    ERROR = "error"
    SIMULATION_STARTED = "simulation_started"
    SIMULATION_STOPPED = "simulation_stopped"
    SIMULATION_PAUSED = "simulation_paused"
    SIMULATION_RESUMED = "simulation_resumed"
    MAP_EXPORTED = "map_exported"
    MAP_IMPORTED = "map_imported"
    STATE_SNAPSHOT_START = "state_snapshot_start"
    STATE_SNAPSHOT_END = "state_snapshot_end"
    FULL_MAP_DATA = "full_map_data"
    FULL_AGENT_DATA = "full_agent_data"


class Action(BaseModel):
    """Action sent from Frontend to Backend."""

    type: ActionType
    tick_rate: float | None = None
    agent_id: str | None = None
    agent_data: dict[str, Any] | None = None
    agent_kind: str | None = None
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "Action":
        """Validate that required fields are provided for specific action types."""
        # Validate agent_id for actions that require it
        if (
            self.type
            in [
                ActionType.ADD_AGENT,
                ActionType.DELETE_AGENT,
                ActionType.MODIFY_AGENT,
            ]
            and self.agent_id is None
        ):
            raise ValueError(f"agent_id is required for {self.type} action")

        # Validate agent_kind for ADD_AGENT
        if self.type == ActionType.ADD_AGENT and self.agent_kind is None:
            raise ValueError(f"agent_kind is required for {self.type} action")

        # Validate tick_rate for START and SET_TICK_RATE
        if self.type in [ActionType.START, ActionType.SET_TICK_RATE] and self.tick_rate is None:
            raise ValueError(f"tick_rate is required for {self.type} action")

        # Validate metadata for export/import map actions
        if self.type in [ActionType.EXPORT_MAP, ActionType.IMPORT_MAP] and (
            self.metadata is None or "map_name" not in self.metadata
        ):
            raise ValueError(f"metadata with 'map_name' is required for {self.type} action")

        return self


class Signal(BaseModel):
    """Signal emitted from Backend to Frontend."""

    type: SignalType
    tick: int | None = None
    agent_id: str | None = None
    data: dict[str, Any] | None = None
    error_message: str | None = None
    timestamp: float | None = None


class ActionQueue:
    """Thread-safe queue for Actions from Frontend to Backend."""

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: queue.Queue[Action] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, action: Action, timeout: float | None = None) -> None:
        """Put an action into the queue."""
        try:
            self._queue.put(action, timeout=timeout)
        except queue.Full:
            raise RuntimeError("Action queue is full")

    def get(self, timeout: float | None = None) -> Action:
        """Get an action from the queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            raise RuntimeError("No actions available")

    def get_nowait(self) -> Action | None:
        """Get an action from the queue without blocking."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()

    def qsize(self) -> int:
        """Get the current size of the queue."""
        return self._queue.qsize()


class SignalQueue:
    """Thread-safe queue for Signals from Backend to Frontend."""

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: queue.Queue[Signal] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, signal: Signal, timeout: float | None = None) -> None:
        """Put a signal into the queue."""
        try:
            self._queue.put(signal, timeout=timeout)
        except queue.Full:
            raise RuntimeError("Signal queue is full")

    def get(self, timeout: float | None = None) -> Signal:
        """Get a signal from the queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            raise RuntimeError("No signals available")

    def get_nowait(self) -> Signal | None:
        """Get a signal from the queue without blocking."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()

    def qsize(self) -> int:
        """Get the current size of the queue."""
        return self._queue.qsize()


# Convenience functions for creating common actions
def create_start_action(tick_rate: float = 20.0) -> Action:
    """Create a start simulation action."""
    return Action(type=ActionType.START, tick_rate=tick_rate)


def create_stop_action() -> Action:
    """Create a stop simulation action."""
    return Action(type=ActionType.STOP)


def create_pause_action() -> Action:
    """Create a pause simulation action."""
    return Action(type=ActionType.PAUSE)


def create_resume_action() -> Action:
    """Create a resume simulation action."""
    return Action(type=ActionType.RESUME)


def create_set_tick_rate_action(tick_rate: float) -> Action:
    """Create a set tick rate action."""
    return Action(type=ActionType.SET_TICK_RATE, tick_rate=tick_rate)


def create_delete_agent_action(agent_id: str) -> Action:
    """Create a delete agent action."""
    return Action(type=ActionType.DELETE_AGENT, agent_id=agent_id)


def create_add_agent_action(agent_id: str, agent_kind: str, agent_data: dict[str, Any]) -> Action:
    """Create an add agent action."""
    return Action(
        type=ActionType.ADD_AGENT, agent_id=agent_id, agent_kind=agent_kind, agent_data=agent_data
    )


def create_export_map_action(map_name: str) -> Action:
    """Create an export map action."""
    return Action(type=ActionType.EXPORT_MAP, metadata={"map_name": map_name})


def create_import_map_action(map_name: str) -> Action:
    """Create an import map action."""
    return Action(type=ActionType.IMPORT_MAP, metadata={"map_name": map_name})


# Convenience functions for creating common signals
def create_tick_start_signal(tick: int) -> Signal:
    """Create a tick start signal."""
    return Signal(type=SignalType.TICK_START, tick=tick)


def create_tick_end_signal(tick: int) -> Signal:
    """Create a tick end signal."""
    return Signal(type=SignalType.TICK_END, tick=tick)


def create_agent_update_signal(agent_id: str, data: dict[str, Any], tick: int) -> Signal:
    """Create an agent update signal."""
    return Signal(type=SignalType.AGENT_UPDATE, agent_id=agent_id, data=data, tick=tick)


def create_world_event_signal(data: dict[str, Any], tick: int) -> Signal:
    """Create a world event signal."""
    return Signal(type=SignalType.WORLD_EVENT, data=data, tick=tick)


def create_error_signal(error_message: str, tick: int | None = None) -> Signal:
    """Create an error signal."""
    return Signal(type=SignalType.ERROR, error_message=error_message, tick=tick)


def create_simulation_started_signal() -> Signal:
    """Create a simulation started signal."""
    return Signal(type=SignalType.SIMULATION_STARTED)


def create_simulation_stopped_signal() -> Signal:
    """Create a simulation stopped signal."""
    return Signal(type=SignalType.SIMULATION_STOPPED)


def create_simulation_paused_signal() -> Signal:
    """Create a simulation paused signal."""
    return Signal(type=SignalType.SIMULATION_PAUSED)


def create_simulation_resumed_signal() -> Signal:
    """Create a simulation resumed signal."""
    return Signal(type=SignalType.SIMULATION_RESUMED)


def create_map_exported_signal(map_name: str) -> Signal:
    """Create a map exported signal."""
    return Signal(type=SignalType.MAP_EXPORTED, data={"map_name": map_name})


def create_map_imported_signal(map_name: str) -> Signal:
    """Create a map imported signal."""
    return Signal(type=SignalType.MAP_IMPORTED, data={"map_name": map_name})


def create_state_snapshot_start_signal() -> Signal:
    """Create a state snapshot start signal."""
    return Signal(type=SignalType.STATE_SNAPSHOT_START)


def create_state_snapshot_end_signal() -> Signal:
    """Create a state snapshot end signal."""
    return Signal(type=SignalType.STATE_SNAPSHOT_END)


def create_full_map_data_signal(graph_data: dict[str, Any]) -> Signal:
    """Create a full map data signal."""
    return Signal(type=SignalType.FULL_MAP_DATA, data=graph_data)


def create_full_agent_data_signal(agent_data: dict[str, Any]) -> Signal:
    """Create a full agent data signal."""
    return Signal(type=SignalType.FULL_AGENT_DATA, data=agent_data)


def create_request_state_action() -> Action:
    """Create a request state action."""
    return Action(type=ActionType.REQUEST_STATE)
