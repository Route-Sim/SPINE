"""Tests for simulation queue infrastructure."""

import threading
import time

import pytest

from world.sim.actions.action_parser import ActionRequest
from world.sim.queues import (
    ActionQueue,
    ActionType,
    Signal,
    SignalQueue,
    SignalType,
    create_add_agent_action,
    create_delete_agent_action,
    create_pause_action,
    create_resume_action,
    create_start_action,
    create_stop_action,
    create_tick_end_signal,
    create_tick_start_signal,
    create_update_simulation_action,
    signal_type_to_string,
)


class TestActionQueue:
    """Test ActionQueue functionality."""

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        queue = ActionQueue()
        action_request = create_start_action(tick_rate=30.0)

        queue.put(action_request)
        retrieved = queue.get()

        assert retrieved.action == ActionType.START.value
        assert retrieved.params["tick_rate"] == 30.0

    def test_empty_queue(self) -> None:
        """Test getting from empty queue."""
        queue = ActionQueue()

        with pytest.raises(RuntimeError, match="No actions available"):
            queue.get(timeout=0.1)

    def test_get_nowait(self) -> None:
        """Test non-blocking get."""
        queue = ActionQueue()

        # Empty queue should return None
        assert queue.get_nowait() is None

        # Add action and retrieve
        action_request = create_start_action()
        queue.put(action_request)
        retrieved = queue.get_nowait()

        assert retrieved is not None
        assert retrieved.action == ActionType.START.value

    def test_queue_size(self) -> None:
        """Test queue size tracking."""
        queue = ActionQueue()

        assert queue.empty()
        assert queue.qsize() == 0

        action_request = create_start_action()
        queue.put(action_request)
        assert not queue.empty()
        assert queue.qsize() == 1

        queue.get()
        assert queue.empty()
        assert queue.qsize() == 0


class TestSignalQueue:
    """Test SignalQueue functionality."""

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        queue = SignalQueue()
        signal = create_tick_start_signal(tick=123)

        queue.put(signal)
        retrieved = queue.get()

        assert retrieved.signal == signal_type_to_string(SignalType.TICK_START)
        assert retrieved.data == {"tick": 123}

    def test_empty_queue(self) -> None:
        """Test getting from empty queue."""
        queue = SignalQueue()

        with pytest.raises(RuntimeError, match="No signals available"):
            queue.get(timeout=0.1)

    def test_get_nowait(self) -> None:
        """Test non-blocking get."""
        queue = SignalQueue()

        # Empty queue should return None
        assert queue.get_nowait() is None

        # Add signal and retrieve
        signal = create_tick_start_signal(tick=456)
        queue.put(signal)
        retrieved = queue.get_nowait()

        assert retrieved is not None
        assert retrieved.signal == signal_type_to_string(SignalType.TICK_START)
        assert retrieved.data == {"tick": 456}


class TestSignal:
    """Test Signal model."""

    def test_tick_signals(self) -> None:
        """Test tick signal creation."""
        start_signal = Signal(
            signal=signal_type_to_string(SignalType.TICK_START), data={"tick": 100}
        )
        end_signal = Signal(signal=signal_type_to_string(SignalType.TICK_END), data={"tick": 100})

        assert start_signal.signal == signal_type_to_string(SignalType.TICK_START)
        assert start_signal.data == {"tick": 100}
        assert end_signal.signal == signal_type_to_string(SignalType.TICK_END)
        assert end_signal.data == {"tick": 100}

    def test_agent_update_signal(self) -> None:
        """Test agent update signal creation."""
        data = {
            "position": {"x": 10, "y": 20},
            "status": "moving",
            "agent_id": "agent_1",
            "tick": 50,
        }
        signal = Signal(signal=signal_type_to_string(SignalType.AGENT_UPDATE), data=data)

        assert signal.signal == signal_type_to_string(SignalType.AGENT_UPDATE)
        assert signal.data["agent_id"] == "agent_1"
        assert signal.data["position"] == {"x": 10, "y": 20}
        assert signal.data["status"] == "moving"
        assert signal.data["tick"] == 50

    def test_error_signal(self) -> None:
        """Test error signal creation."""
        signal = Signal(
            signal=signal_type_to_string(SignalType.ERROR),
            data={"code": "GENERIC_ERROR", "message": "Test error", "tick": 75},
        )

        assert signal.signal == signal_type_to_string(SignalType.ERROR)
        assert signal.data["message"] == "Test error"
        assert signal.data["code"] == "GENERIC_ERROR"
        assert signal.data["tick"] == 75


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_start_action(self) -> None:
        """Test create_start_action function."""
        action = create_start_action(tick_rate=40.0)

        assert isinstance(action, ActionRequest)
        assert action.action == ActionType.START.value
        assert action.params == {"tick_rate": 40.0}

    def test_create_stop_action(self) -> None:
        """Test create_stop_action function."""
        action = create_stop_action()

        assert isinstance(action, ActionRequest)
        assert action.action == ActionType.STOP.value
        assert action.params == {}

    def test_create_pause_and_resume_actions(self) -> None:
        """Test pause and resume convenience helpers."""
        pause_action = create_pause_action()
        resume_action = create_resume_action()

        assert pause_action.action == ActionType.PAUSE.value
        assert pause_action.params == {}
        assert resume_action.action == ActionType.RESUME.value
        assert resume_action.params == {}

    def test_create_agent_actions(self) -> None:
        """Test agent-related action helpers."""
        agent_payload = {"capacity": 50}
        add_action = create_add_agent_action("agent_1", "transport", agent_payload)
        delete_action = create_delete_agent_action("agent_1")

        assert add_action.action == ActionType.ADD_AGENT.value
        assert add_action.params == {
            "agent_id": "agent_1",
            "agent_kind": "transport",
            "agent_data": agent_payload,
        }
        assert delete_action.action == ActionType.DELETE_AGENT.value
        assert delete_action.params == {"agent_id": "agent_1"}

    def test_create_update_simulation_action(self) -> None:
        """Test simulation update helper for tick rate changes."""
        action = create_update_simulation_action(55)

        assert action.action == ActionType.UPDATE_SIMULATION.value
        assert action.params == {"tick_rate": 55}

    def test_create_tick_signals(self) -> None:
        """Test create tick signal functions."""
        start_signal = create_tick_start_signal(tick=200)
        end_signal = create_tick_end_signal(tick=200)

        assert start_signal.signal == signal_type_to_string(SignalType.TICK_START)
        assert start_signal.data == {"tick": 200}
        assert end_signal.signal == signal_type_to_string(SignalType.TICK_END)
        assert end_signal.data == {"tick": 200}


class TestThreadSafety:
    """Test thread safety of queues."""

    def test_concurrent_put_get(self) -> None:
        """Test concurrent put and get operations."""
        queue = ActionQueue()
        results = []

        def producer() -> None:
            for i in range(10):
                queue.put(create_start_action(tick_rate=float(i)))
                time.sleep(0.01)

        def consumer() -> None:
            for _ in range(10):
                try:
                    action_request = queue.get(timeout=1.0)
                    results.append(action_request.params["tick_rate"])
                except Exception:
                    break

        # Start producer and consumer threads
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        consumer_thread.join()

        # Verify all actions were processed
        assert len(results) == 10
        assert set(results) == set(range(10))

    def test_queue_full_handling(self) -> None:
        """Test handling of full queue."""
        queue = ActionQueue(maxsize=2)

        # Fill queue
        action1 = create_start_action()
        action2 = create_start_action()
        action3 = create_start_action()
        queue.put(action1)
        queue.put(action2)

        # Try to put more - should raise exception
        with pytest.raises(RuntimeError, match="Action queue is full"):
            queue.put(action3, timeout=0.1)
