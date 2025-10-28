"""Tests for simulation queue infrastructure."""

import threading
import time

import pytest

from world.sim.queues import (
    Action,
    ActionQueue,
    ActionType,
    Signal,
    SignalQueue,
    SignalType,
    create_full_agent_data_signal,
    create_full_map_data_signal,
    create_request_state_action,
    create_start_action,
    create_state_snapshot_end_signal,
    create_state_snapshot_start_signal,
    create_stop_action,
    create_tick_end_signal,
    create_tick_start_signal,
)


class TestActionQueue:
    """Test ActionQueue functionality."""

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        queue = ActionQueue()
        action = create_start_action(tick_rate=30.0)

        queue.put(action)
        retrieved = queue.get()

        assert retrieved.type == ActionType.START
        assert retrieved.tick_rate == 30.0

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
        action = create_start_action()
        queue.put(action)
        retrieved = queue.get_nowait()

        assert retrieved is not None
        assert retrieved.type == ActionType.START

    def test_queue_size(self) -> None:
        """Test queue size tracking."""
        queue = ActionQueue()

        assert queue.empty()
        assert queue.qsize() == 0

        queue.put(create_start_action())
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

        assert retrieved.type == SignalType.TICK_START
        assert retrieved.tick == 123

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
        assert retrieved.type == SignalType.TICK_START
        assert retrieved.tick == 456


class TestAction:
    """Test Action model."""

    def test_start_action(self) -> None:
        """Test start action creation."""
        action = Action(type=ActionType.START, tick_rate=25.0)

        assert action.type == ActionType.START
        assert action.tick_rate == 25.0
        assert action.agent_id is None
        assert action.agent_data is None

    def test_add_agent_action(self) -> None:
        """Test add agent action creation."""
        agent_data = {"x": 100, "y": 200, "capacity": 50}
        action = Action(
            type=ActionType.ADD_AGENT,
            agent_id="agent_1",
            agent_kind="transport",
            agent_data=agent_data,
        )

        assert action.type == ActionType.ADD_AGENT
        assert action.agent_id == "agent_1"
        assert action.agent_kind == "transport"
        assert action.agent_data == agent_data

    def test_action_validation(self) -> None:
        """Test action validation."""
        # Valid action
        action = Action(type=ActionType.STOP)
        assert action.type == ActionType.STOP

        # Invalid action type should raise validation error
        with pytest.raises(ValueError):
            Action(type="invalid_type")  # type: ignore[arg-type]


class TestSignal:
    """Test Signal model."""

    def test_tick_signals(self) -> None:
        """Test tick signal creation."""
        start_signal = Signal(type=SignalType.TICK_START, tick=100)
        end_signal = Signal(type=SignalType.TICK_END, tick=100)

        assert start_signal.type == SignalType.TICK_START
        assert start_signal.tick == 100
        assert end_signal.type == SignalType.TICK_END
        assert end_signal.tick == 100

    def test_agent_update_signal(self) -> None:
        """Test agent update signal creation."""
        data = {"position": {"x": 10, "y": 20}, "status": "moving"}
        signal = Signal(type=SignalType.AGENT_UPDATE, agent_id="agent_1", data=data, tick=50)

        assert signal.type == SignalType.AGENT_UPDATE
        assert signal.agent_id == "agent_1"
        assert signal.data == data
        assert signal.tick == 50

    def test_error_signal(self) -> None:
        """Test error signal creation."""
        signal = Signal(type=SignalType.ERROR, error_message="Test error", tick=75)

        assert signal.type == SignalType.ERROR
        assert signal.error_message == "Test error"
        assert signal.tick == 75


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_start_action(self) -> None:
        """Test create_start_action function."""
        action = create_start_action(tick_rate=40.0)

        assert action.type == ActionType.START
        assert action.tick_rate == 40.0

    def test_create_stop_action(self) -> None:
        """Test create_stop_action function."""
        action = create_stop_action()

        assert action.type == ActionType.STOP
        assert action.tick_rate is None

    def test_create_tick_signals(self) -> None:
        """Test create tick signal functions."""
        start_signal = create_tick_start_signal(tick=200)
        end_signal = create_tick_end_signal(tick=200)

        assert start_signal.type == SignalType.TICK_START
        assert start_signal.tick == 200
        assert end_signal.type == SignalType.TICK_END
        assert end_signal.tick == 200


class TestThreadSafety:
    """Test thread safety of queues."""

    def test_concurrent_put_get(self) -> None:
        """Test concurrent put and get operations."""
        queue = ActionQueue()
        results = []

        def producer() -> None:
            for i in range(10):
                action = Action(type=ActionType.START, tick_rate=float(i))
                queue.put(action)
                time.sleep(0.01)

        def consumer() -> None:
            for _ in range(10):
                try:
                    action = queue.get(timeout=1.0)
                    results.append(action.tick_rate)
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
        queue.put(create_start_action())
        queue.put(create_start_action())

        # Try to put more - should raise exception
        with pytest.raises(RuntimeError, match="Action queue is full"):
            queue.put(create_start_action(), timeout=0.1)


class TestStateSnapshotSignals:
    """Test state snapshot signal functionality."""

    def test_state_snapshot_start_signal(self) -> None:
        """Test state snapshot start signal creation."""
        signal = create_state_snapshot_start_signal()

        assert signal.type == SignalType.STATE_SNAPSHOT_START
        assert signal.tick is None
        assert signal.data is None

    def test_state_snapshot_end_signal(self) -> None:
        """Test state snapshot end signal creation."""
        signal = create_state_snapshot_end_signal()

        assert signal.type == SignalType.STATE_SNAPSHOT_END
        assert signal.tick is None
        assert signal.data is None

    def test_full_map_data_signal(self) -> None:
        """Test full map data signal creation."""
        map_data = {
            "nodes": [{"id": "1", "x": 0.0, "y": 0.0, "buildings": []}],
            "edges": [{"id": "1", "from_node": "1", "to_node": "2", "length_m": 100.0, "mode": 1}],
        }
        signal = create_full_map_data_signal(map_data)

        assert signal.type == SignalType.FULL_MAP_DATA
        assert signal.data == map_data
        assert signal.tick is None

    def test_full_agent_data_signal(self) -> None:
        """Test full agent data signal creation."""
        agent_data = {
            "id": "agent1",
            "kind": "transport",
            "tags": {"status": "moving"},
            "inbox_count": 0,
            "outbox_count": 1,
        }
        signal = create_full_agent_data_signal(agent_data)

        assert signal.type == SignalType.FULL_AGENT_DATA
        assert signal.data == agent_data
        assert signal.tick is None

    def test_request_state_action(self) -> None:
        """Test request state action creation."""
        action = create_request_state_action()

        assert action.type == ActionType.REQUEST_STATE
        assert action.tick_rate is None
        assert action.agent_id is None
        assert action.agent_data is None
        assert action.agent_kind is None
        assert action.metadata is None
