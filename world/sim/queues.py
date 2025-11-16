"""Thread-safe queue infrastructure for Backend communication."""

import queue
import threading
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .actions.action_parser import ActionRequest


class ActionType(str, Enum):
    """Canonical action identifiers following the '<domain>.<action>' protocol."""

    START = "simulation.start"
    STOP = "simulation.stop"
    PAUSE = "simulation.pause"
    RESUME = "simulation.resume"
    SET_TICK_RATE = "tick_rate.update"
    ADD_AGENT = "agent.create"
    DELETE_AGENT = "agent.delete"
    MODIFY_AGENT = "agent.update"
    DESCRIBE_AGENT = "agent.describe"
    LIST_AGENTS = "agent.list"
    EXPORT_MAP = "map.export"
    IMPORT_MAP = "map.import"
    CREATE_MAP = "map.create"
    CREATE_BUILDING = "building.create"


class SignalType(str, Enum):
    """Canonical signal identifiers following the '<domain>.<signal>' protocol."""

    TICK_START = "tick.start"
    TICK_END = "tick.end"
    AGENT_CREATED = "agent.created"
    AGENT_UPDATE = "agent.updated"
    AGENT_DESCRIBED = "agent.described"
    AGENT_LISTED = "agent.listed"
    WORLD_EVENT = "event.created"  # TODO: REWORK
    ERROR = "error"
    SIMULATION_STARTED = "simulation.started"
    SIMULATION_STOPPED = "simulation.stopped"
    SIMULATION_PAUSED = "simulation.paused"
    SIMULATION_RESUMED = "simulation.resumed"
    MAP_EXPORTED = "map.exported"
    MAP_IMPORTED = "map.imported"
    MAP_CREATED = "map.created"
    PACKAGE_CREATED = "package.created"
    PACKAGE_EXPIRED = "package.expired"
    PACKAGE_PICKED_UP = "package.picked_up"
    PACKAGE_DELIVERED = "package.delivered"
    SITE_STATS_UPDATE = "site.stats_update"  # TODO: should be part of building.updated signal
    BUILDING_CREATED = "building.created"


def signal_type_to_string(signal_type: SignalType) -> str:
    """Return the canonical ``<domain>.<signal>`` string for a signal type.

    Args:
        signal_type: The SignalType enum value

    Returns:
        Domain.signal format string (e.g., "simulation.started")
    """
    return signal_type.value


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
        self._queue: queue.Queue[ActionRequest] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, action_request: ActionRequest, timeout: float | None = None) -> None:
        """Put an action request into the queue."""
        try:
            self._queue.put(action_request, timeout=timeout)
        except queue.Full:
            raise RuntimeError("Action queue is full")

    def get(self, timeout: float | None = None) -> ActionRequest:
        """Get an action request from the queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            raise RuntimeError("No actions available")

    def get_nowait(self) -> ActionRequest | None:
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


# Convenience helpers for creating protocol-compliant actions
def _create_action(action_type: ActionType, params: dict[str, Any] | None = None) -> ActionRequest:
    """Build an ActionRequest from a canonical identifier and parameter mapping."""
    return ActionRequest(action=action_type.value, params=params or {})


def create_start_action(tick_rate: float = 20.0) -> ActionRequest:
    """Create a start simulation action."""
    return _create_action(ActionType.START, {"tick_rate": tick_rate})


def create_stop_action() -> ActionRequest:
    """Create a stop simulation action."""
    return _create_action(ActionType.STOP)


def create_pause_action() -> ActionRequest:
    """Create a pause simulation action."""
    return _create_action(ActionType.PAUSE)


def create_resume_action() -> ActionRequest:
    """Create a resume simulation action."""
    return _create_action(ActionType.RESUME)


def create_set_tick_rate_action(tick_rate: float) -> ActionRequest:
    """Create a set tick rate action."""
    return _create_action(ActionType.SET_TICK_RATE, {"tick_rate": tick_rate})


def create_delete_agent_action(agent_id: str) -> ActionRequest:
    """Create a delete agent action."""
    return _create_action(ActionType.DELETE_AGENT, {"agent_id": agent_id})


def create_add_agent_action(
    agent_id: str, agent_kind: str, agent_data: dict[str, Any]
) -> ActionRequest:
    """Create an add agent action."""
    return _create_action(
        ActionType.ADD_AGENT,
        {"agent_id": agent_id, "agent_kind": agent_kind, "agent_data": agent_data},
    )


def create_describe_agent_action(agent_id: str) -> ActionRequest:
    """Create a describe agent action."""
    return _create_action(ActionType.DESCRIBE_AGENT, {"agent_id": agent_id})


def create_list_agents_action(agent_kind: str | None = None) -> ActionRequest:
    """Create an agent list action, optionally filtered by kind."""
    params: dict[str, Any] = {}
    if agent_kind is not None:
        params["agent_kind"] = agent_kind
    return _create_action(ActionType.LIST_AGENTS, params)


def create_export_map_action(map_name: str) -> ActionRequest:
    """Create an export map action."""
    return _create_action(ActionType.EXPORT_MAP, {"map_name": map_name})


def create_import_map_action(map_name: str) -> ActionRequest:
    """Create an import map action."""
    return _create_action(ActionType.IMPORT_MAP, {"map_name": map_name})


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


def create_agent_described_signal(agent_state: dict[str, Any], tick: int) -> Signal:
    """Create an agent described signal with the complete agent state."""
    signal_data = {**agent_state, "tick": tick}
    return Signal(signal=signal_type_to_string(SignalType.AGENT_DESCRIBED), data=signal_data)


def create_agent_listed_signal(agents: list[dict[str, Any]], total: int, tick: int) -> Signal:
    """Create an agent listed signal containing aggregated agent data."""
    return Signal(
        signal=signal_type_to_string(SignalType.AGENT_LISTED),
        data={"total": total, "agents": agents, "tick": tick},
    )


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
    """Create a map created signal with generation metadata and graph structure."""
    return Signal(signal=signal_type_to_string(SignalType.MAP_CREATED), data=data)


def create_building_create_action(
    building_id: str, node_id: int, capacity: int, building_type: str
) -> ActionRequest:
    """Create a building create action.

    Args:
        building_id: Unique identifier for the building
        node_id: Graph node identifier where the building will be placed
        capacity: Building capacity (type-specific, e.g., parking capacity)
        building_type: Type of building to create (e.g., "parking")

    Returns:
        ActionRequest for building.create action
    """
    params: dict[str, Any] = {
        "building_id": building_id,
        "node_id": node_id,
        "capacity": capacity,
        "building_type": building_type,
    }
    return _create_action(ActionType.CREATE_BUILDING, params)


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


def create_building_created_signal(
    building_data: dict[str, Any], node_id: int, tick: int | None = None
) -> Signal:
    """Create a building created signal."""
    data: dict[str, Any] = {
        "node_id": node_id,
        "building": building_data,
    }
    if tick is not None:
        data["tick"] = tick
    return Signal(signal=signal_type_to_string(SignalType.BUILDING_CREATED), data=data)
