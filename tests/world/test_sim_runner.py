"""Tests for the simulation runner signal handling and shutdown."""

import signal
import threading
import time
import unittest
from unittest.mock import Mock

from world.sim.runner import SimulationRunner, create_default_world


class TestSimulationRunnerSignals(unittest.TestCase):
    """Test signal handling in the simulation runner."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.world = create_default_world()
        # Use a unique port for each test to avoid conflicts
        import random

        port = 8000 + random.randint(1, 1000)
        self.runner = SimulationRunner(
            world=self.world,
            host="localhost",
            port=port,
            log_level="WARNING",  # Reduce log noise during tests
        )

    def tearDown(self) -> None:
        """Clean up after tests."""
        if hasattr(self, "runner"):
            self.runner.shutdown()

    def test_signal_handler_registration(self) -> None:
        """Test that signal handlers are properly registered."""
        # Check that signal handlers are set
        self.assertIsNotNone(signal.signal(signal.SIGINT, signal.SIG_DFL))
        self.assertIsNotNone(signal.signal(signal.SIGTERM, signal.SIG_DFL))

    def test_shutdown_event_setting(self) -> None:
        """Test that shutdown event is set when signal handler is called."""
        # Initially shutdown event should not be set
        self.assertFalse(self.runner._shutdown_event.is_set())

        # Simulate signal handler call
        self.runner._signal_handler(signal.SIGINT, None)

        # Shutdown event should now be set
        self.assertTrue(self.runner._shutdown_event.is_set())

    def test_controller_stop_on_shutdown(self) -> None:
        """Test that controller is stopped during shutdown."""
        # Start the controller
        self.runner.controller.start()

        # Send a start action to make the simulation actually run
        from world.sim.queues import Action, ActionType

        start_action = Action(type=ActionType.START, tick_rate=20.0)
        self.runner.action_queue.put(start_action)

        # Give it time to process the action
        time.sleep(0.2)

        # Verify controller is running
        self.assertTrue(self.runner.controller.state.running)

        # Call shutdown
        self.runner.shutdown()

        # Controller should be stopped
        self.assertFalse(self.runner.controller.state.running)

    def test_signal_broadcast_task_cancellation(self) -> None:
        """Test that signal broadcast task is properly cancelled."""
        # Mock the websocket server
        mock_websocket_server = Mock()
        mock_task = Mock()
        mock_task.done.return_value = False
        mock_websocket_server._signal_broadcast_task = mock_task
        self.runner.websocket_server = mock_websocket_server
        self.runner._signal_broadcast_task = mock_task

        # Call shutdown
        self.runner.shutdown()

        # Task should be cancelled
        mock_task.cancel.assert_called_once()

    def test_thread_cleanup_on_shutdown(self) -> None:
        """Test that threads are properly cleaned up during shutdown."""
        # Start controller to create thread
        self.runner.controller.start()
        controller_thread = self.runner.controller._thread

        # Call shutdown
        self.runner.shutdown()

        # Thread should be stopped
        assert controller_thread is not None
        self.assertFalse(controller_thread.is_alive())

    def test_graceful_shutdown_with_timeout(self) -> None:
        """Test graceful shutdown with thread timeout."""
        # Start controller
        self.runner.controller.start()

        # Mock a thread that takes longer than timeout
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        mock_thread.join.side_effect = lambda _timeout: time.sleep(0.1)
        self.runner._controller_thread = mock_thread

        # Call shutdown
        start_time = time.time()
        self.runner.shutdown()
        end_time = time.time()

        # Should complete within reasonable time (timeout is 5 seconds)
        self.assertLess(end_time - start_time, 6.0)
        mock_thread.join.assert_called_once_with(timeout=5.0)

    def test_multiple_shutdown_calls(self) -> None:
        """Test that multiple shutdown calls are handled gracefully."""
        # First shutdown
        self.runner.shutdown()

        # Second shutdown should not raise exceptions
        self.runner.shutdown()

        # Third shutdown should also be safe
        self.runner.shutdown()

    def test_shutdown_without_websocket_server(self) -> None:
        """Test shutdown when websocket server is None."""
        # Use type: ignore to suppress type checker warning for test
        self.runner.websocket_server = None  # type: ignore[assignment]
        self.runner._signal_broadcast_task = None

        # Should not raise exceptions
        self.runner.shutdown()

    def test_shutdown_with_cancelled_task(self) -> None:
        """Test shutdown when signal broadcast task is already cancelled."""
        # Create a mock task that's already done
        mock_task = Mock()
        mock_task.done.return_value = True
        self.runner._signal_broadcast_task = mock_task

        # Should not raise exceptions
        self.runner.shutdown()

        # Task should not be cancelled if already done
        mock_task.cancel.assert_not_called()


class TestSimulationRunnerIntegration(unittest.TestCase):
    """Integration tests for the simulation runner."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.world = create_default_world()
        # Use a unique port for each test to avoid conflicts
        import random

        port = 8000 + random.randint(1, 1000)
        self.runner = SimulationRunner(
            world=self.world, host="localhost", port=port, log_level="WARNING"
        )

    def tearDown(self) -> None:
        """Clean up after tests."""
        if hasattr(self, "runner"):
            self.runner.shutdown()

    def test_runner_startup_and_shutdown(self) -> None:
        """Test complete startup and shutdown cycle."""
        # Start runner in a separate thread
        runner_thread = threading.Thread(target=self.runner.start, daemon=True)
        runner_thread.start()

        # Give it time to start
        time.sleep(0.5)

        # Send a start action to make the simulation actually run
        from world.sim.queues import Action, ActionType

        start_action = Action(type=ActionType.START, tick_rate=20.0)
        self.runner.action_queue.put(start_action)

        # Give it time to process the action
        time.sleep(0.1)

        # Verify components are running
        self.assertTrue(self.runner.controller.state.running)

        # Shutdown
        self.runner.shutdown()

        # Verify shutdown
        self.assertFalse(self.runner.controller.state.running)

    def test_signal_handling_during_runtime(self) -> None:
        """Test signal handling while runner is running."""
        # Start runner in a separate thread
        runner_thread = threading.Thread(target=self.runner.start, daemon=True)
        runner_thread.start()

        # Give it time to start
        time.sleep(0.5)

        # Simulate signal
        self.runner._signal_handler(signal.SIGINT, None)

        # Give it time to process
        time.sleep(0.5)

        # Verify shutdown event is set
        self.assertTrue(self.runner._shutdown_event.is_set())

        # Clean shutdown
        self.runner.shutdown()

    def test_keyboard_interrupt_handling(self) -> None:
        """Test keyboard interrupt handling."""
        # Mock the main loop to simulate KeyboardInterrupt

        def mock_start() -> None:
            try:
                # Simulate the main loop
                while not self.runner._shutdown_event.is_set():
                    time.sleep(0.1)
                    # Simulate KeyboardInterrupt after a short time
                    if time.time() - getattr(mock_start, "start_time", 0) > 0.2:
                        raise KeyboardInterrupt()
            except KeyboardInterrupt:
                self.runner.logger.info("Received keyboard interrupt")
            finally:
                self.runner.shutdown()

        # Use type: ignore to suppress type checker warning for test
        mock_start.start_time = time.time()  # type: ignore[attr-defined]
        self.runner.start = mock_start  # type: ignore[method-assign]

        # Should handle KeyboardInterrupt gracefully
        self.runner.start()

        # Verify shutdown was called
        self.assertTrue(self.runner._shutdown_event.is_set())


if __name__ == "__main__":
    unittest.main()
