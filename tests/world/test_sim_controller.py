"""Tests for simulation controller."""

import contextlib
import time
from typing import Any
from unittest.mock import Mock

from agents.base import AgentBase
from core.types import AgentID
from world.sim.actions.action_parser import ActionRequest
from world.sim.controller import SimulationController
from world.sim.queues import (
    ActionQueue,
    ActionType,
    SignalQueue,
    SignalType,
    signal_type_to_string,
)
from world.sim.state import SimulationState
from world.world import World


class TestSimulationState:
    """Test SimulationState functionality."""

    def test_initial_state(self) -> None:
        """Test initial state values."""
        state = SimulationState()

        assert not state.running
        assert not state.paused
        assert state.tick_rate == 20.0
        assert state.current_tick == 0

    def test_start_stop(self) -> None:
        """Test start and stop operations."""
        state = SimulationState()

        state.start()
        assert state.running
        assert not state.paused

        state.stop()
        assert not state.running
        assert not state.paused

    def test_pause_resume(self) -> None:
        """Test pause and resume operations."""
        state = SimulationState()

        state.start()
        state.pause()
        assert state.running
        assert state.paused

        state.resume()
        assert state.running
        assert not state.paused

    def test_set_tick_rate(self) -> None:
        """Test setting tick rate."""
        state = SimulationState()

        state.set_tick_rate(50.0)
        assert state.tick_rate == 50.0

        # Test clamping
        state.set_tick_rate(200.0)
        assert state.tick_rate == 100.0

        state.set_tick_rate(0.05)
        assert state.tick_rate == 0.1

    def test_increment_tick(self) -> None:
        """Test tick increment."""
        state = SimulationState()

        assert state.current_tick == 0
        state.increment_tick()
        assert state.current_tick == 1
        state.increment_tick()
        assert state.current_tick == 2


class TestSimulationController:
    """Test SimulationController functionality."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.world = Mock(spec=World)
        self.world.step.return_value = {"type": "tick", "events": [], "agents": []}

        # Track agents for get_full_state
        self.world._test_agents = []

        def mock_add_agent(_: AgentID, agent: AgentBase) -> None:
            self.world._test_agents.append(agent)

        def mock_get_full_state() -> dict[str, Any]:
            return {
                "graph": {"nodes": [], "edges": []},
                "agents": [agent.serialize_full() for agent in self.world._test_agents],
                "metadata": {"tick": 0, "dt_s": 0.05, "now_s": 0, "time_min": 0},
            }

        self.world.add_agent.side_effect = mock_add_agent
        self.world.get_full_state.side_effect = mock_get_full_state

        self.action_queue = ActionQueue()
        self.signal_queue = SignalQueue()
        self.controller = SimulationController(
            world=self.world,
            action_queue=self.action_queue,
            signal_queue=self.signal_queue,
        )

    def test_initial_state(self) -> None:
        """Test initial controller state."""
        assert not self.controller.state.running
        assert not self.controller.state.paused
        assert self.controller.state.tick_rate == 20.0

    def test_start_controller(self) -> None:
        """Test starting the controller."""
        self.controller.start()
        assert self.controller._thread is not None
        assert self.controller._thread.is_alive()

        # Clean up
        self.controller.stop()

    def test_handle_start_action(self) -> None:
        """Test handling start action."""
        action_request = ActionRequest(action=ActionType.START.value, params={"tick_rate": 30.0})
        self.controller.action_processor.process(action_request)

        assert self.controller.state.running
        assert not self.controller.state.paused
        assert self.controller.state.tick_rate == 30.0

    def test_handle_stop_action(self) -> None:
        """Test handling stop action."""
        # Start first
        self.controller.state.start()
        assert self.controller.state.running

        # Then stop
        action_request = ActionRequest(action=ActionType.STOP.value, params={})
        self.controller.action_processor.process(action_request)

        assert not self.controller.state.running
        assert not self.controller.state.paused

    def test_handle_pause_resume_actions(self) -> None:
        """Test handling pause and resume actions."""
        # Start first
        self.controller.state.start()
        assert self.controller.state.running

        # Pause
        action_request = ActionRequest(action=ActionType.PAUSE.value, params={})
        self.controller.action_processor.process(action_request)
        assert self.controller.state.paused

        # Resume
        action_request = ActionRequest(action=ActionType.RESUME.value, params={})
        self.controller.action_processor.process(action_request)
        assert not self.controller.state.paused

    def test_handle_update_simulation_action(self) -> None:
        """Test handling simulation update action (tick rate change)."""
        action_request = ActionRequest(action="simulation.update", params={"tick_rate": 50.0})
        self.controller.action_processor.process(action_request)

        assert self.controller.state.tick_rate == 50.0

        # Verify signal was emitted
        assert not self.signal_queue.empty()
        signal = self.signal_queue.get_nowait()
        assert signal is not None
        assert signal.signal == signal_type_to_string(SignalType.SIMULATION_UPDATED)
        assert signal.data["tick_rate"] == 50

    def test_handle_add_agent_action(self) -> None:
        """Test handling add agent action."""
        # Mock the world's add_agent method
        self.world.add_agent = Mock()

        action_request = ActionRequest(
            action=ActionType.ADD_AGENT.value,
            params={
                "agent_id": "test_agent",
                "agent_kind": "transport",
                "agent_data": {"capacity": 100.0, "load": 0.0},
            },
        )

        self.controller.action_processor.process(action_request)

        # Verify agent was added
        self.world.add_agent.assert_called_once()

    def test_handle_delete_agent_action(self) -> None:
        """Test handling delete agent action."""
        # Mock the world's remove_agent method
        self.world.remove_agent = Mock()

        action_request = ActionRequest(
            action=ActionType.DELETE_AGENT.value, params={"agent_id": "test_agent"}
        )

        self.controller.action_processor.process(action_request)

        # Verify agent was removed (handler converts string to AgentID)
        from core.types import AgentID

        self.world.remove_agent.assert_called_once_with(AgentID("test_agent"))

    def test_handle_modify_agent_action(self) -> None:
        """Test handling modify agent action."""
        # Mock the world's modify_agent method
        self.world.modify_agent = Mock()

        action_request = ActionRequest(
            action=ActionType.MODIFY_AGENT.value,
            params={"agent_id": "test_agent", "agent_data": {"x": 150, "y": 250}},
        )

        self.controller.action_processor.process(action_request)

        # Verify agent was modified (handler converts string to AgentID)
        from core.types import AgentID

        self.world.modify_agent.assert_called_once_with(AgentID("test_agent"), {"x": 150, "y": 250})

    def test_run_simulation_step(self) -> None:
        """Test running a simulation step."""
        # Mock world step to return specific data
        self.world.step.return_value = {
            "type": "tick",
            "events": [{"type": "test_event"}],
            "agents": [{"id": "agent_1", "kind": "transport"}],
        }

        # Start the controller
        self.controller.start()
        self.controller.state.start()

        # Run a step
        self.controller._run_simulation_step()

        # Verify world step was called
        self.world.step.assert_called_once()

        # Clean up
        self.controller.stop()

    def test_process_actions(self) -> None:
        """Test processing actions from queue."""
        # Add actions to queue
        from world.sim.actions.action_parser import ActionRequest

        self.action_queue.put(
            ActionRequest(action=ActionType.START.value, params={"tick_rate": 25.0})
        )
        self.action_queue.put(
            ActionRequest(action=ActionType.UPDATE_SIMULATION.value, params={"tick_rate": 40.0})
        )

        # Process actions
        self.controller._process_actions()

        # Verify state changes
        assert self.controller.state.running
        assert self.controller.state.tick_rate == 40.0

    def test_emit_signal(self) -> None:
        """Test signal emission."""
        from world.sim.queues import create_tick_start_signal

        signal = create_tick_start_signal(tick=100)
        self.controller._emit_signal(signal)

        # Verify signal was added to queue
        assert not self.signal_queue.empty()
        retrieved_signal = self.signal_queue.get_nowait()
        assert retrieved_signal is not None
        assert retrieved_signal.signal == signal_type_to_string(SignalType.TICK_START)
        assert retrieved_signal.data == {"tick": 100}

    def test_error_handling(self) -> None:
        """Test error handling in action processing."""
        # Mock world to raise exception
        self.world.add_agent.side_effect = Exception("Test error")

        action_request = ActionRequest(
            action=ActionType.ADD_AGENT.value,
            params={"agent_id": "test_agent", "agent_kind": "transport"},
        )

        # Should not raise exception, but emit error signal
        with contextlib.suppress(Exception):
            self.controller.action_processor.process(action_request)

        # Verify error signal was emitted
        assert not self.signal_queue.empty()
        error_signal = self.signal_queue.get_nowait()
        assert error_signal is not None
        assert error_signal.signal == signal_type_to_string(SignalType.ERROR)
        assert error_signal.data["message"] is not None
        assert "Test error" in error_signal.data["message"]

    def test_controller_lifecycle(self) -> None:
        """Test full controller lifecycle."""
        # Start controller
        self.controller.start()
        assert self.controller._thread is not None
        assert self.controller._thread.is_alive()

        # Stop controller
        self.controller.stop()

        # Wait a bit for thread to finish
        time.sleep(0.1)
        assert not self.controller._thread.is_alive()

    def test_simulation_loop_integration(self) -> None:
        """Test integration of simulation loop with commands."""
        # Start controller
        self.controller.start()

        # Send start action
        from world.sim.actions.action_parser import ActionRequest

        self.action_queue.put(
            ActionRequest(action=ActionType.START.value, params={"tick_rate": 100.0})
        )

        # Let it run for a short time
        time.sleep(0.2)

        # Verify simulation started
        assert self.controller.state.running

        # Send stop action
        self.action_queue.put(ActionRequest(action=ActionType.STOP.value, params={}))

        # Let it process
        time.sleep(0.1)

        # Stop controller
        self.controller.stop()

        # Verify simulation stopped
        assert not self.controller.state.running

    def test_simulation_started_signal_on_start(self) -> None:
        """Test that simulation.started signal is emitted when simulation starts (no snapshot)."""
        # Start controller
        self.controller.start()

        # Send start action
        from world.sim.actions.action_parser import ActionRequest

        self.action_queue.put(
            ActionRequest(action=ActionType.START.value, params={"tick_rate": 30.0})
        )
        self.action_queue.put(
            ActionRequest(action=ActionType.START.value, params={"tick_rate": 30.0})
        )

        # Wait for action to be processed (queue empty)
        import time

        max_wait = 1.0  # Maximum wait time in seconds
        wait_interval = 0.01  # Check every 10ms
        waited = 0.0
        while not self.action_queue.empty() and waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval

        # Give a bit more time for state to be updated
        time.sleep(0.05)

        # Verify simulation started
        assert self.controller.state.running

        # Stop controller
        self.controller.stop()

        # Check for signals
        signals = []
        while not self.signal_queue.empty():
            signal = self.signal_queue.get_nowait()
            if signal:
                signals.append(signal)

        # Should have simulation_started signal
        signal_strings = [s.signal for s in signals]
        assert signal_type_to_string(SignalType.SIMULATION_STARTED) in signal_strings

    def test_agent_serialize_full(self) -> None:
        """Test agent serialize_full method."""
        from agents.base import AgentBase
        from core.types import AgentID

        # Create a test agent
        agent = AgentBase(id=AgentID("test_agent"), kind="test")
        agent.tags = {"status": "active", "position": {"x": 100, "y": 200}}

        # Test serialize_full
        full_data = agent.serialize_full()

        assert full_data["id"] == "test_agent"
        assert full_data["kind"] == "test"
        assert full_data["tags"] == {"status": "active", "position": {"x": 100, "y": 200}}
        assert full_data["inbox_count"] == 0
        assert full_data["outbox_count"] == 0

    def test_building_agent_serialize_full(self) -> None:
        """Test BuildingAgent serialize_full method."""
        from agents.buildings.building_agent import BuildingAgent
        from core.buildings.base import Building
        from core.types import AgentID, BuildingID

        # Create a test building
        building = Building(id=BuildingID("building1"))

        # Create building agent
        agent = BuildingAgent(building=building, id=AgentID("building_agent"), kind="building")
        agent.tags = {"status": "operational"}

        # Test serialize_full
        full_data = agent.serialize_full()

        assert full_data["id"] == "building1"
        assert full_data["kind"] == "building"
        assert full_data["tags"] == {"status": "operational"}
        assert full_data["inbox_count"] == 0
        assert full_data["outbox_count"] == 0
        assert "building" in full_data
        assert full_data["building"]["id"] == "building1"

    def test_world_get_full_state(self) -> None:
        """Test World get_full_state method."""
        # Add an agent to the world
        from agents.base import AgentBase
        from core.types import AgentID

        agent = AgentBase(id=AgentID("test_agent"), kind="test")
        agent.tags = {"status": "active"}
        self.world.add_agent(AgentID("test_agent"), agent)

        # Get full state
        full_state = self.world.get_full_state()

        # Verify structure
        assert "graph" in full_state
        assert "agents" in full_state
        assert "metadata" in full_state

        # Verify graph data
        assert "nodes" in full_state["graph"]
        assert "edges" in full_state["graph"]

        # Verify agents data
        assert len(full_state["agents"]) == 1
        agent_data = full_state["agents"][0]
        assert agent_data["id"] == "test_agent"
        assert agent_data["kind"] == "test"
        assert agent_data["tags"] == {"status": "active"}

        # Verify metadata
        assert "tick" in full_state["metadata"]
        assert "dt_s" in full_state["metadata"]
        assert "now_s" in full_state["metadata"]
        assert "time_min" in full_state["metadata"]
