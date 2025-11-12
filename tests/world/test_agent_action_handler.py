"""Tests for agent action handler describe functionality."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from agents.base import AgentBase
from core.types import AgentID
from world.sim.handlers.agent import AgentActionHandler
from world.sim.handlers.base import HandlerContext
from world.sim.queues import SignalQueue, SignalType
from world.sim.state import SimulationState
from world.world import World


class _DummyGraph:
    """Minimal graph stub required by the world."""

    def __init__(self) -> None:
        self.nodes: dict[str, Any] = {}


def _build_context(running: bool = True) -> HandlerContext:
    """Create a handler context for testing."""
    state = SimulationState()
    if running:
        state.start()
    world = World(graph=_DummyGraph(), router=None, traffic=None)
    signal_queue = SignalQueue()
    logger = logging.getLogger(__name__)
    return HandlerContext(state=state, world=world, signal_queue=signal_queue, logger=logger)


def test_handle_describe_emits_agent_state() -> None:
    """Ensure describe action emits the full agent state."""
    context = _build_context()
    agent_id = AgentID("agent-1")
    agent = AgentBase(id=agent_id, kind="test")
    context.world.add_agent(agent_id, agent)

    AgentActionHandler.handle_describe({"agent_id": "agent-1"}, context)

    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.AGENT_DESCRIBED.value
    assert signal.data["id"] == agent_id
    assert signal.data["kind"] == "test"
    assert signal.data["tick"] == 0


def test_handle_describe_allows_not_running_simulation() -> None:
    """Ensure describe action succeeds when simulation is not running."""
    context = _build_context(running=False)
    agent_id = AgentID("agent-1")
    agent = AgentBase(id=agent_id, kind="test")
    context.world.add_agent(agent_id, agent)

    AgentActionHandler.handle_describe({"agent_id": "agent-1"}, context)

    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.AGENT_DESCRIBED.value
    assert signal.data["id"] == agent_id


def test_handle_describe_agent_not_found() -> None:
    """Ensure describe action emits error when agent is missing."""
    context = _build_context()

    with pytest.raises(ValueError, match="Agent not found: agent-unknown"):
        AgentActionHandler.handle_describe({"agent_id": "agent-unknown"}, context)

    error_signal = context.signal_queue.get_nowait()
    assert error_signal is not None
    assert error_signal.signal == SignalType.ERROR.value
    assert "agent-unknown" in error_signal.data["message"]


def test_handle_list_returns_all_agents() -> None:
    """Ensure list action returns all agents with full state."""
    context = _build_context()
    truck_id = AgentID("truck-1")
    building_id = AgentID("building-1")
    context.world.add_agent(truck_id, AgentBase(id=truck_id, kind="truck"))
    context.world.add_agent(building_id, AgentBase(id=building_id, kind="building"))

    AgentActionHandler.handle_list({}, context)

    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.AGENT_LISTED.value
    assert signal.data["total"] == 2
    agent_ids = {agent["agent_id"] for agent in signal.data["agents"]}
    assert agent_ids == {truck_id, building_id}


def test_handle_list_filters_by_kind() -> None:
    """Ensure list action filters by agent kind when provided."""
    context = _build_context()
    truck_id = AgentID("truck-1")
    building_id = AgentID("building-1")
    context.world.add_agent(truck_id, AgentBase(id=truck_id, kind="truck"))
    context.world.add_agent(building_id, AgentBase(id=building_id, kind="building"))

    AgentActionHandler.handle_list({"agent_kind": "truck"}, context)

    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.AGENT_LISTED.value
    assert signal.data["total"] == 1
    returned_agents = signal.data["agents"]
    assert len(returned_agents) == 1
    assert returned_agents[0]["agent_id"] == truck_id
    assert returned_agents[0]["kind"] == "truck"


def test_handle_list_invalid_filter_type() -> None:
    """Ensure invalid filter types raise a ValueError."""
    context = _build_context()

    with pytest.raises(ValueError, match="agent_kind must be a string"):
        AgentActionHandler.handle_list({"agent_kind": 123}, context)


def test_handle_list_handles_empty_world() -> None:
    """Ensure list action succeeds when no agents are present."""
    context = _build_context()

    AgentActionHandler.handle_list({}, context)

    signal = context.signal_queue.get_nowait()
    assert signal is not None
    assert signal.signal == SignalType.AGENT_LISTED.value
    assert signal.data["total"] == 0
    assert signal.data["agents"] == []
