"""Thread-safe queue infrastructure for Backend communication."""

import queue
import threading
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from .action_parser import ActionRequest


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
    # Future package/site actions
    CREATE_PACKAGE = "create_package"
    CANCEL_PACKAGE = "cancel_package"
    ADD_SITE = "add_site"
    MODIFY_SITE = "modify_site"


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
    MAP_CREATED = "map_created"
    STATE_SNAPSHOT_START = "state_snapshot_start"
    STATE_SNAPSHOT_END = "state_snapshot_end"
    FULL_MAP_DATA = "full_map_data"
    FULL_AGENT_DATA = "full_agent_data"
    PACKAGE_CREATED = "package_created"
    PACKAGE_EXPIRED = "package_expired"
    PACKAGE_PICKED_UP = "package_picked_up"
    PACKAGE_DELIVERED = "package_delivered"
    SITE_STATS_UPDATE = "site_stats_update"


def signal_type_to_string(signal_type: SignalType) -> str:
    """Convert SignalType enum to domain.signal format string.

    Args:
        signal_type: The SignalType enum value

    Returns:
        Domain.signal format string (e.g., "simulation.started")
    """
    mapping: dict[SignalType, str] = {
        SignalType.TICK_START: "tick.start",
        SignalType.TICK_END: "tick.end",
        SignalType.AGENT_UPDATE: "agent.updated",
        SignalType.WORLD_EVENT: "event.created",
        SignalType.ERROR: "error",
        SignalType.SIMULATION_STARTED: "simulation.started",
        SignalType.SIMULATION_STOPPED: "simulation.stopped",
        SignalType.SIMULATION_PAUSED: "simulation.paused",
        SignalType.SIMULATION_RESUMED: "simulation.resumed",
        SignalType.MAP_EXPORTED: "map.exported",
        SignalType.MAP_IMPORTED: "map.imported",
        SignalType.MAP_CREATED: "map.created",
        SignalType.STATE_SNAPSHOT_START: "state.snapshot_start",
        SignalType.STATE_SNAPSHOT_END: "state.snapshot_end",
        SignalType.FULL_MAP_DATA: "state.full_map_data",
        SignalType.FULL_AGENT_DATA: "state.full_agent_data",
        SignalType.PACKAGE_CREATED: "package.created",
        SignalType.PACKAGE_EXPIRED: "package.expired",
        SignalType.PACKAGE_PICKED_UP: "package.picked_up",
        SignalType.PACKAGE_DELIVERED: "package.delivered",
        SignalType.SITE_STATS_UPDATE: "site.stats_update",
    }
    return mapping[signal_type]


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

        # Validate metadata for package/site actions
        if self.type in [ActionType.CREATE_PACKAGE, ActionType.CANCEL_PACKAGE] and (
            self.metadata is None or "package_id" not in self.metadata
        ):
            raise ValueError(f"metadata with 'package_id' is required for {self.type} action")

        if self.type in [ActionType.ADD_SITE, ActionType.MODIFY_SITE] and (
            self.metadata is None or "site_id" not in self.metadata
        ):
            raise ValueError(f"metadata with 'site_id' is required for {self.type} action")

        return self


class Signal(BaseModel):
    """Signal emitted from Backend to Frontend.

    Signals follow the format: {"signal": "domain.signal", "data": {...}}
    where all contextual information is consolidated into the data dict.
    """

    signal: str  # Format: "domain.signal" (e.g., "simulation.started")
    data: dict[str, Any] = Field(default_factory=dict)  # All context consolidated here

    def model_dump(self, **_kwargs: Any) -> dict[str, Any]:
        """Override model_dump to ensure consistent format."""
        return {"signal": self.signal, "data": self.data}


class ActionQueue:
    """Thread-safe queue for ActionRequests from Frontend to Backend."""

    def __init__(self, maxsize: int = 1000) -> None:
        from .action_parser import ActionRequest

        self._queue: queue.Queue[ActionRequest] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, action_request: "ActionRequest", timeout: float | None = None) -> None:
        """Put an action request into the queue."""
        try:
            self._queue.put(action_request, timeout=timeout)
        except queue.Full:
            raise RuntimeError("Action queue is full")

    def get(self, timeout: float | None = None) -> "ActionRequest":
        """Get an action request from the queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            raise RuntimeError("No actions available")

    def get_nowait(self) -> "ActionRequest | None":
        """Get an action request from the queue without blocking."""
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
    return Signal(signal=signal_type_to_string(SignalType.TICK_START), data={"tick": tick})


def create_tick_end_signal(tick: int) -> Signal:
    """Create a tick end signal."""
    return Signal(signal=signal_type_to_string(SignalType.TICK_END), data={"tick": tick})


def create_agent_update_signal(agent_id: str, data: dict[str, Any], tick: int) -> Signal:
    """Create an agent update signal."""
    signal_data = {**data, "agent_id": agent_id, "tick": tick}
    return Signal(signal=signal_type_to_string(SignalType.AGENT_UPDATE), data=signal_data)


def create_world_event_signal(data: dict[str, Any], tick: int) -> Signal:
    """Create a world event signal."""
    signal_data = {**data, "tick": tick}
    return Signal(signal=signal_type_to_string(SignalType.WORLD_EVENT), data=signal_data)


def create_error_signal(error_message: str, tick: int | None = None) -> Signal:
    """Create an error signal.

    Per API reference, error signals should have:
    {
      "signal": "error",
      "data": {
        "code": string,
        "message": string
      }
    }
    """
    error_data: dict[str, Any] = {"message": error_message}
    if tick is not None:
        error_data["tick"] = tick
    # Use generic error code if not provided
    if "code" not in error_data:
        error_data["code"] = "GENERIC_ERROR"
    return Signal(signal=signal_type_to_string(SignalType.ERROR), data=error_data)


def create_simulation_started_signal(tick_rate: int | None = None) -> Signal:
    """Create a simulation started signal."""
    data: dict[str, Any] = {}
    if tick_rate is not None:
        data["tick_rate"] = tick_rate
    return Signal(signal=signal_type_to_string(SignalType.SIMULATION_STARTED), data=data)


def create_simulation_stopped_signal() -> Signal:
    """Create a simulation stopped signal."""
    return Signal(signal=signal_type_to_string(SignalType.SIMULATION_STOPPED), data={})


def create_simulation_paused_signal() -> Signal:
    """Create a simulation paused signal."""
    return Signal(signal=signal_type_to_string(SignalType.SIMULATION_PAUSED), data={})


def create_simulation_resumed_signal() -> Signal:
    """Create a simulation resumed signal."""
    return Signal(signal=signal_type_to_string(SignalType.SIMULATION_RESUMED), data={})


def create_map_exported_signal(map_name: str) -> Signal:
    """Create a map exported signal."""
    return Signal(
        signal=signal_type_to_string(SignalType.MAP_EXPORTED), data={"map_name": map_name}
    )


def create_map_imported_signal(map_name: str) -> Signal:
    """Create a map imported signal."""
    return Signal(
        signal=signal_type_to_string(SignalType.MAP_IMPORTED), data={"map_name": map_name}
    )


def create_map_created_signal(data: dict[str, Any]) -> Signal:
    """Create a map created signal."""
    return Signal(signal=signal_type_to_string(SignalType.MAP_CREATED), data=data)


def create_state_snapshot_start_signal() -> Signal:
    """Create a state snapshot start signal."""
    return Signal(signal=signal_type_to_string(SignalType.STATE_SNAPSHOT_START), data={})


def create_state_snapshot_end_signal() -> Signal:
    """Create a state snapshot end signal."""
    return Signal(signal=signal_type_to_string(SignalType.STATE_SNAPSHOT_END), data={})


def create_full_map_data_signal(graph_data: dict[str, Any]) -> Signal:
    """Create a full map data signal."""
    return Signal(signal=signal_type_to_string(SignalType.FULL_MAP_DATA), data=graph_data)


def create_full_agent_data_signal(agent_data: dict[str, Any]) -> Signal:
    """Create a full agent data signal."""
    return Signal(signal=signal_type_to_string(SignalType.FULL_AGENT_DATA), data=agent_data)


def create_request_state_action() -> Action:
    """Create a request state action."""
    return Action(type=ActionType.REQUEST_STATE)


# Package-related signal factory functions
def create_package_created_signal(package_data: dict[str, Any], tick: int) -> Signal:
    """Create a package created signal."""
    signal_data = {**package_data, "tick": tick}
    return Signal(signal=signal_type_to_string(SignalType.PACKAGE_CREATED), data=signal_data)


def create_package_expired_signal(
    package_id: str, site_id: str, value_lost: float, tick: int
) -> Signal:
    """Create a package expired signal."""
    return Signal(
        signal=signal_type_to_string(SignalType.PACKAGE_EXPIRED),
        data={
            "package_id": package_id,
            "site_id": site_id,
            "value_lost": value_lost,
            "tick": tick,
        },
    )


def create_package_picked_up_signal(package_id: str, agent_id: str, tick: int) -> Signal:
    """Create a package picked up signal."""
    return Signal(
        signal=signal_type_to_string(SignalType.PACKAGE_PICKED_UP),
        data={
            "package_id": package_id,
            "agent_id": agent_id,
            "tick": tick,
        },
    )


def create_package_delivered_signal(
    package_id: str, site_id: str, value: float, tick: int
) -> Signal:
    """Create a package delivered signal."""
    return Signal(
        signal=signal_type_to_string(SignalType.PACKAGE_DELIVERED),
        data={
            "package_id": package_id,
            "site_id": site_id,
            "value": value,
            "tick": tick,
        },
    )


def create_site_stats_signal(site_id: str, stats: dict[str, Any], tick: int) -> Signal:
    """Create a site statistics update signal."""
    return Signal(
        signal=signal_type_to_string(SignalType.SITE_STATS_UPDATE),
        data={
            "site_id": site_id,
            "stats": stats,
            "tick": tick,
        },
    )
