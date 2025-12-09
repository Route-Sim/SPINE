"""Backend controller for managing the simulation loop and state."""

import json
import logging
import queue
import threading
import time
from pathlib import Path
from typing import Any

from world.world import World

from .actions.action_processor import ActionProcessor
from .actions.action_registry import create_default_registry
from .dto.statistics_dto import StatisticsBatchDTO, TickStatisticsDTO
from .dto.step_result_dto import StepResultDTO
from .queues import (
    ActionQueue,
    Signal,
    SignalQueue,
    create_agent_event_signal,
    create_agent_update_signal,
    create_building_updated_signal,
    create_error_signal,
    create_package_created_signal,
    create_package_delivered_signal,
    create_package_expired_signal,
    create_package_picked_up_signal,
    create_simulation_tick_rate_warning_signal,
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
        stats_dir: str | Path | None = None,
        stats_batch_size: int = 1000,
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
        # Statistics collection
        self._stats_batch_size = stats_batch_size
        self._stats_dir = Path(stats_dir) if stats_dir else Path("stats")
        self._stats_dir.mkdir(parents=True, exist_ok=True)
        self._stats_queue: queue.Queue[StatisticsBatchDTO] = queue.Queue(maxsize=10)
        self._stats_batch: list[TickStatisticsDTO] = []
        self._stats_batch_id = 0
        self._stats_writer_thread: threading.Thread | None = None
        self._stats_writer_stop_event = threading.Event()

    def start(self) -> None:
        """Start the simulation controller in a separate thread."""
        if self._thread and self._thread.is_alive():
            self.logger.warning("Simulation controller is already running")
            return

        self._stop_event.clear()
        self._stats_writer_stop_event.clear()
        # Start statistics writer thread
        self._stats_writer_thread = threading.Thread(target=self._stats_writer_loop, daemon=True)
        self._stats_writer_thread.start()
        # Start main simulation thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.logger.info("Simulation controller started")

    def stop(self) -> None:
        """Stop the simulation controller."""
        self._stop_event.set()
        self.state.stop()  # Stop the simulation state
        # Flush remaining statistics
        self._flush_statistics_batch()
        # Stop statistics writer
        self._stats_writer_stop_event.set()
        if self._stats_writer_thread and self._stats_writer_thread.is_alive():
            self._stats_writer_thread.join(timeout=5.0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self.logger.info("Simulation controller stopped")

    def _run(self) -> None:
        """Main simulation loop."""
        self.logger.info("Simulation loop started")

        while not self._stop_event.is_set():
            try:
                loop_start = time.perf_counter()

                # Process actions and measure time
                action_start = time.perf_counter()
                self._process_actions()
                action_time_ms = (time.perf_counter() - action_start) * 1000.0

                # Run simulation step if running and not paused
                step_time_ms = 0.0
                if self.state.running and not self.state.paused:
                    step_start = time.perf_counter()
                    self._run_simulation_step()
                    step_time_ms = (time.perf_counter() - step_start) * 1000.0

                # Calculate total processing time
                total_time_ms = (time.perf_counter() - loop_start) * 1000.0

                # Collect statistics if running
                if self.state.running and not self.state.paused:
                    self._collect_statistics(
                        action_time_ms=action_time_ms,
                        step_time_ms=step_time_ms,
                        total_time_ms=total_time_ms,
                    )

                # Calculate adjusted sleep time to maintain exact tick rate
                if self.state.running:
                    target_time_per_tick = 1.0 / self.state.tick_rate
                    sleep_time = max(0.0, target_time_per_tick - (total_time_ms / 1000.0))

                    # Check if we can maintain tick rate
                    if total_time_ms / 1000.0 > target_time_per_tick:
                        self._emit_tick_rate_warning(
                            total_time_ms=total_time_ms,
                            target_time_ms=target_time_per_tick * 1000.0,
                        )

                    if sleep_time > 0.0:
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

    def _process_step_result(self, step_result: StepResultDTO) -> None:
        """Process the result of a world step and emit appropriate signals.

        Args:
            step_result: DTO containing all state changes from the simulation step.
        """
        # Emit world events if any
        if step_result.has_events():
            for event in step_result.get_events():
                self._emit_event_signal(event)

        # Emit agent updates
        if step_result.has_agent_updates():
            for agent_diff in step_result.get_agent_diffs():
                self._emit_signal(
                    create_agent_update_signal(
                        agent_diff.get("id", "unknown"), agent_diff, self.state.current_tick
                    )
                )

        # Emit building updates
        if step_result.has_building_updates():
            for building_data in step_result.get_building_updates():
                self._emit_signal(
                    create_building_updated_signal(
                        building_data.get("id", "unknown"),
                        building_data,
                        self.state.current_tick,
                    )
                )

    def _emit_event_signal(self, event: dict[str, Any]) -> None:
        """Emit the appropriate signal for a world event.

        Args:
            event: Event dictionary with 'type' field and event-specific data.
        """
        event_type = event.get("type", "")

        if event_type == "package_created":
            self._emit_signal(
                create_package_created_signal(event.get("data", {}), self.state.current_tick)
            )
        elif event_type == "package_expired":
            self._emit_signal(
                create_package_expired_signal(
                    event.get("package_id", ""),
                    event.get("site_id", ""),
                    event.get("value_lost", 0.0),
                    self.state.current_tick,
                )
            )
        elif event_type == "package_picked_up":
            self._emit_signal(
                create_package_picked_up_signal(
                    event.get("package_id", ""),
                    event.get("agent_id", ""),
                    self.state.current_tick,
                )
            )
        elif event_type == "package_delivered":
            self._emit_signal(
                create_package_delivered_signal(
                    event.get("package_id", ""),
                    event.get("site_id", ""),
                    event.get("value", 0.0),
                    self.state.current_tick,
                )
            )
        elif event_type == "agent_event":
            event_data = {
                k: v
                for k, v in event.items()
                if k not in ("type", "event_type", "agent_id", "agent_type")
            }
            self._emit_signal(
                create_agent_event_signal(
                    event.get("event_type", ""),
                    event.get("agent_id", ""),
                    event.get("agent_type", ""),
                    event_data,
                    self.state.current_tick,
                )
            )
        else:
            # Generic world event
            self._emit_signal(create_world_event_signal(event, self.state.current_tick))

    def _emit_signal(self, signal: Signal) -> None:
        """Emit a signal to the signal queue."""
        try:
            self.signal_queue.put(signal, timeout=1.0)
        except Exception as e:
            self.logger.error(f"Failed to emit signal: {e}")

    def _emit_error(self, error_message: str) -> None:
        """Emit an error signal."""
        self._emit_signal(create_error_signal(error_message, self.state.current_tick))

    def _emit_tick_rate_warning(self, total_time_ms: float, target_time_ms: float) -> None:
        """Emit a tick rate warning signal when processing time exceeds available time.

        Args:
            total_time_ms: Total processing time in milliseconds
            target_time_ms: Target time per tick in milliseconds
        """
        self._emit_signal(
            create_simulation_tick_rate_warning_signal(
                target_tick_rate=self.state.tick_rate,
                actual_processing_time_ms=total_time_ms,
                required_time_ms=target_time_ms,
                tick=self.state.current_tick,
            )
        )

    def _collect_statistics(
        self, action_time_ms: float, step_time_ms: float, total_time_ms: float
    ) -> None:
        """Collect statistics for the current tick.

        Args:
            action_time_ms: Time spent processing actions (milliseconds)
            step_time_ms: Time spent running simulation step (milliseconds)
            total_time_ms: Total processing time (milliseconds)
        """
        achieved_rate = 1000.0 / total_time_ms if total_time_ms > 0.0 else 0.0

        tick_stats = TickStatisticsDTO(
            tick=self.state.current_tick,
            action_time_ms=action_time_ms,
            step_time_ms=step_time_ms,
            total_time_ms=total_time_ms,
            target_tick_rate=self.state.tick_rate,
            achieved_rate=achieved_rate,
        )

        self._stats_batch.append(tick_stats)

        # Flush batch when it reaches the configured size
        if len(self._stats_batch) >= self._stats_batch_size:
            self._flush_statistics_batch()

    def _flush_statistics_batch(self) -> None:
        """Flush the current statistics batch to the writer queue."""
        if not self._stats_batch:
            return

        batch = StatisticsBatchDTO(
            batch_id=self._stats_batch_id,
            timestamp=time.time(),
            ticks=self._stats_batch.copy(),
        )
        self._stats_batch_id += 1
        self._stats_batch.clear()

        try:
            self._stats_queue.put(batch, timeout=0.1)
        except queue.Full:
            self.logger.warning("Statistics queue is full, dropping batch")

    def _stats_writer_loop(self) -> None:
        """Background thread loop for writing statistics batches to file."""
        self.logger.info("Statistics writer thread started")

        while not self._stats_writer_stop_event.is_set():
            try:
                # Get batch from queue with timeout
                batch = self._stats_queue.get(timeout=1.0)
                self._write_statistics_batch(batch)
                self._stats_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in statistics writer: {e}", exc_info=True)

        # Write any remaining batches
        while not self._stats_queue.empty():
            try:
                batch = self._stats_queue.get_nowait()
                self._write_statistics_batch(batch)
                self._stats_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                self.logger.error(f"Error writing final statistics batch: {e}", exc_info=True)

        self.logger.info("Statistics writer thread stopped")

    def _write_statistics_batch(self, batch: StatisticsBatchDTO) -> None:
        """Write a statistics batch to a JSON file.

        Args:
            batch: Statistics batch to write
        """
        filename = f"stats_batch_{batch.batch_id:06d}_{int(batch.timestamp)}.json"
        filepath = self._stats_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(batch.to_dict(), f, indent=2)
            self.logger.debug(f"Wrote statistics batch {batch.batch_id} to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to write statistics batch {batch.batch_id}: {e}")
