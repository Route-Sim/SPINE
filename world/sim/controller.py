"""Backend controller for managing the simulation loop and state."""

import logging
import threading
import time
from typing import Any

from world.world import World

from .actions.action_processor import ActionProcessor
from .actions.action_registry import create_default_registry
from .queues import (
    ActionQueue,
    Signal,
    SignalQueue,
    create_agent_update_signal,
    create_error_signal,
    create_package_created_signal,
    create_package_delivered_signal,
    create_package_expired_signal,
    create_package_picked_up_signal,
    create_tick_end_signal,
    create_tick_start_signal,
    create_world_event_signal,
)
from .state import SimulationState


class SimulationController:
    """Controls the Backend simulation loop and processes Actions (Commands)."""

    def __init__(
        self,
        world: World,
        action_queue: ActionQueue,
        signal_queue: SignalQueue,
        logger: logging.Logger | None = None,
    ) -> None:
        self.world = world
        self.action_queue = action_queue
        self.signal_queue = signal_queue
        self.logger = logger or logging.getLogger(__name__)
        self.state = SimulationState()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        # Initialize action processor
        registry = create_default_registry()
        self.action_processor = ActionProcessor(
            registry=registry,
            state=self.state,
            world=self.world,
            signal_queue=self.signal_queue,
            logger=self.logger,
        )

    def start(self) -> None:
        """Start the simulation controller in a separate thread."""
        if self._thread and self._thread.is_alive():
            self.logger.warning("Simulation controller is already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.logger.info("Simulation controller started")

    def stop(self) -> None:
        """Stop the simulation controller."""
        self._stop_event.set()
        self.state.stop()  # Stop the simulation state
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self.logger.info("Simulation controller stopped")

    def _run(self) -> None:
        """Main simulation loop."""
        self.logger.info("Simulation loop started")

        while not self._stop_event.is_set():
            try:
                # Process actions
                self._process_actions()

                # Run simulation step if running and not paused
                if self.state.running and not self.state.paused:
                    self._run_simulation_step()

                # Sleep based on tick rate
                if self.state.running:
                    sleep_time = 1.0 / self.state.tick_rate
                    time.sleep(sleep_time)
                else:
                    # If not running, sleep longer to avoid busy waiting
                    time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in simulation loop: {e}", exc_info=True)
                self._emit_error(f"Simulation error: {e}")
                time.sleep(1.0)  # Wait before retrying

        self.logger.info("Simulation loop ended")

    def _process_actions(self) -> None:
        """Process all available actions from the action queue."""
        while True:
            action_request = self.action_queue.get_nowait()
            if action_request is None:
                break

            try:
                self.action_processor.process(action_request)
            except Exception as e:
                # Errors are already logged and signaled by ActionProcessor
                # Just log here for completeness
                self.logger.debug(f"Action processing completed with exception: {e}")

    def _run_simulation_step(self) -> None:
        """Run a single simulation step."""
        try:
            # Emit tick start signal
            self.state.increment_tick()
            self._emit_signal(create_tick_start_signal(self.state.current_tick))

            # Run world step
            step_result = self.world.step()

            # Process step results and emit signals
            self._process_step_result(step_result)

            # Emit tick end signal
            self._emit_signal(create_tick_end_signal(self.state.current_tick))

        except Exception as e:
            self.logger.error(f"Error in simulation step: {e}", exc_info=True)
            self._emit_error(f"Simulation step error: {e}")

    def _process_step_result(self, step_result: dict[str, Any]) -> None:
        """Process the result of a world step and emit appropriate signals."""
        # Emit world events if any
        if step_result.get("events"):
            for event in step_result["events"]:
                # Handle package-specific events with dedicated signals
                if event.get("type") == "package_created":
                    self._emit_signal(
                        create_package_created_signal(
                            event.get("data", {}), self.state.current_tick
                        )
                    )
                elif event.get("type") == "package_expired":
                    self._emit_signal(
                        create_package_expired_signal(
                            event.get("package_id", ""),
                            event.get("site_id", ""),
                            event.get("value_lost", 0.0),
                            self.state.current_tick,
                        )
                    )
                elif event.get("type") == "package_picked_up":
                    self._emit_signal(
                        create_package_picked_up_signal(
                            event.get("package_id", ""),
                            event.get("agent_id", ""),
                            self.state.current_tick,
                        )
                    )
                elif event.get("type") == "package_delivered":
                    self._emit_signal(
                        create_package_delivered_signal(
                            event.get("package_id", ""),
                            event.get("site_id", ""),
                            event.get("value", 0.0),
                            self.state.current_tick,
                        )
                    )
                else:
                    # Generic world event
                    self._emit_signal(create_world_event_signal(event, self.state.current_tick))

        # Emit agent updates
        if step_result.get("agents"):
            for agent_diff in step_result["agents"]:
                if agent_diff:  # Only emit if there are changes
                    self._emit_signal(
                        create_agent_update_signal(
                            agent_diff.get("id", "unknown"), agent_diff, self.state.current_tick
                        )
                    )

    def _emit_signal(self, signal: Signal) -> None:
        """Emit a signal to the signal queue."""
        try:
            self.signal_queue.put(signal, timeout=1.0)
        except Exception as e:
            self.logger.error(f"Failed to emit signal: {e}")

    def _emit_error(self, error_message: str) -> None:
        """Emit an error signal."""
        self._emit_signal(create_error_signal(error_message, self.state.current_tick))
