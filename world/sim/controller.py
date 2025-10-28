"""Backend controller for managing the simulation loop and state."""

import logging
import threading
import time
from typing import Any

from core.types import AgentID
from world.world import World

from .queues import (
    Action,
    ActionQueue,
    ActionType,
    Signal,
    SignalQueue,
    create_agent_update_signal,
    create_error_signal,
    create_full_agent_data_signal,
    create_full_map_data_signal,
    create_map_exported_signal,
    create_map_imported_signal,
    create_simulation_paused_signal,
    create_simulation_resumed_signal,
    create_simulation_started_signal,
    create_simulation_stopped_signal,
    create_state_snapshot_end_signal,
    create_state_snapshot_start_signal,
    create_tick_end_signal,
    create_tick_start_signal,
    create_world_event_signal,
)


class SimulationState:
    """Thread-safe simulation state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._paused = False
        self._tick_rate = 20.0  # ticks per second
        self._current_tick = 0

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    @property
    def tick_rate(self) -> float:
        with self._lock:
            return self._tick_rate

    @property
    def current_tick(self) -> int:
        with self._lock:
            return self._current_tick

    def start(self) -> None:
        with self._lock:
            self._running = True
            self._paused = False

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._paused = False

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def set_tick_rate(self, rate: float) -> None:
        with self._lock:
            self._tick_rate = max(0.1, min(100.0, rate))  # Clamp between 0.1 and 100 Hz

    def increment_tick(self) -> None:
        with self._lock:
            self._current_tick += 1


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
            action = self.action_queue.get_nowait()
            if action is None:
                break

            try:
                self._handle_action(action)
            except Exception as e:
                self.logger.error(f"Error processing action {action.type}: {e}", exc_info=True)
                self._emit_error(f"Action processing error: {e}")

    def _handle_action(self, action: Action) -> None:
        """Handle a single command."""
        self.logger.debug(f"Processing action: {action.type}")

        if action.type == ActionType.START:
            self._handle_start_action(action)
        elif action.type == ActionType.STOP:
            self._handle_stop_action()
        elif action.type == ActionType.PAUSE:
            self._handle_pause_action()
        elif action.type == ActionType.RESUME:
            self._handle_resume_action()
        elif action.type == ActionType.SET_TICK_RATE:
            self._handle_set_tick_rate_action(action)
        elif action.type == ActionType.ADD_AGENT:
            self._handle_add_agent_action(action)
        elif action.type == ActionType.DELETE_AGENT:
            self._handle_delete_agent_action(action)
        elif action.type == ActionType.MODIFY_AGENT:
            self._handle_modify_agent_action(action)
        elif action.type == ActionType.EXPORT_MAP:
            self._handle_export_map_action(action)
        elif action.type == ActionType.IMPORT_MAP:
            self._handle_import_map_action(action)
        elif action.type == ActionType.REQUEST_STATE:
            self._handle_request_state_action()
        else:
            self.logger.warning(f"Unknown action type: {action.type}")

    def _handle_start_action(self, action: Action) -> None:
        """Handle start simulation action."""
        if action.tick_rate is not None:
            self.state.set_tick_rate(action.tick_rate)

        self.state.start()
        self._emit_signal(create_simulation_started_signal())

        # Emit state snapshot when simulation starts
        self._emit_state_snapshot()

        self.logger.info(f"Simulation started with tick rate: {self.state.tick_rate}")

    def _handle_stop_action(self) -> None:
        """Handle stop simulation action."""
        self.state.stop()
        self._emit_signal(create_simulation_stopped_signal())
        self.logger.info("Simulation stopped")

    def _handle_pause_action(self) -> None:
        """Handle pause simulation action."""
        if self.state.running:
            self.state.pause()
            self._emit_signal(create_simulation_paused_signal())
            self.logger.info("Simulation paused")

    def _handle_resume_action(self) -> None:
        """Handle resume simulation action."""
        if self.state.running and self.state.paused:
            self.state.resume()
            self._emit_signal(create_simulation_resumed_signal())
            self.logger.info("Simulation resumed")

    def _handle_set_tick_rate_action(self, action: Action) -> None:
        """Handle set tick rate action."""
        if action.tick_rate is not None:
            self.state.set_tick_rate(action.tick_rate)
            self.logger.info(f"Tick rate set to: {self.state.tick_rate}")

    def _handle_add_agent_action(self, action: Action) -> None:
        """Handle add agent action."""
        if not action.agent_id or not action.agent_kind:
            self.logger.warning("Add agent action missing required fields")
            self._emit_error("Add agent action missing agent_id or agent_kind")
            return

        try:
            agent_id = AgentID(action.agent_id)

            # Import agent classes dynamically based on kind
            from agents.base import AgentBase

            agent_instance: AgentBase

            if action.agent_kind == "building":
                from agents.buildings.building_agent import BuildingAgent
                from core.buildings.base import Building
                from core.types import BuildingID

                # Create building data structure (convert AgentID to BuildingID)
                building = Building(id=BuildingID(str(agent_id)))
                # Create agent wrapper (BuildingAgent has same interface as AgentBase)
                agent_instance = BuildingAgent(  # type: ignore[assignment]
                    building=building,
                    id=agent_id,
                    kind=action.agent_kind,
                    **action.agent_data or {},
                )
            elif action.agent_kind == "transport":
                from agents.transports.base import Transport

                agent_instance = Transport(
                    id=agent_id, kind=action.agent_kind, **action.agent_data or {}
                )
            else:
                # Fallback to base agent
                agent_instance = AgentBase(
                    id=agent_id, kind=action.agent_kind, **action.agent_data or {}
                )

            self.world.add_agent(agent_id, agent_instance)
            self.logger.info(f"Added agent: {action.agent_id} of kind {action.agent_kind}")

        except ImportError as e:
            self.logger.error(f"Failed to import agent class for kind {action.agent_kind}: {e}")
            self._emit_error(f"Unknown agent kind: {action.agent_kind}")
        except Exception as e:
            self.logger.error(f"Failed to add agent {action.agent_id}: {e}", exc_info=True)
            self._emit_error(f"Failed to add agent: {e}")

    def _handle_delete_agent_action(self, action: Action) -> None:
        """Handle delete agent action."""
        if not action.agent_id:
            self.logger.warning("Delete agent action missing agent_id")
            self._emit_error("Delete agent action missing agent_id")
            return

        try:
            agent_id = AgentID(action.agent_id)
            self.world.remove_agent(agent_id)
            self.logger.info(f"Removed agent: {action.agent_id}")
        except ValueError as e:
            self.logger.warning(f"Agent {action.agent_id} not found: {e}")
            self._emit_error(f"Agent not found: {action.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to remove agent {action.agent_id}: {e}", exc_info=True)
            self._emit_error(f"Failed to remove agent: {e}")

    def _handle_modify_agent_action(self, action: Action) -> None:
        """Handle modify agent action."""
        if not action.agent_id or not action.agent_data:
            self.logger.warning("Modify agent action missing required fields")
            self._emit_error("Modify agent action missing agent_id or agent_data")
            return

        try:
            agent_id = AgentID(action.agent_id)
            self.world.modify_agent(agent_id, action.agent_data)
            self.logger.info(f"Modified agent: {action.agent_id}")
        except ValueError as e:
            self.logger.warning(f"Agent {action.agent_id} not found: {e}")
            self._emit_error(f"Agent not found: {action.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to modify agent {action.agent_id}: {e}", exc_info=True)
            self._emit_error(f"Failed to modify agent: {e}")

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

    def _handle_export_map_action(self, action: Action) -> None:
        """Handle export map action."""
        if not action.metadata or "map_name" not in action.metadata:
            self.logger.warning("Export map action missing map_name in metadata")
            self._emit_error("Export map action missing map_name")
            return

        # Reject if simulation is running
        if self.state.running:
            self.logger.warning("Cannot export map while simulation is running")
            self._emit_error("Cannot export map while simulation is running")
            return

        map_name = action.metadata["map_name"]

        try:
            self.world.export_graph(map_name)
            self._emit_signal(create_map_exported_signal(map_name))
            self.logger.info(f"Map exported: {map_name}")
        except ValueError as e:
            self.logger.error(f"Failed to export map {map_name}: {e}")
            self._emit_error(f"Failed to export map: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error exporting map {map_name}: {e}", exc_info=True)
            self._emit_error(f"Unexpected error exporting map: {e}")

    def _handle_import_map_action(self, action: Action) -> None:
        """Handle import map action."""
        if not action.metadata or "map_name" not in action.metadata:
            self.logger.warning("Import map action missing map_name in metadata")
            self._emit_error("Import map action missing map_name")
            return

        # Reject if simulation is running
        if self.state.running:
            self.logger.warning("Cannot import map while simulation is running")
            self._emit_error("Cannot import map while simulation is running")
            return

        map_name = action.metadata["map_name"]

        try:
            self.world.import_graph(map_name)
            self._emit_signal(create_map_imported_signal(map_name))
            self.logger.info(f"Map imported: {map_name}")
        except FileNotFoundError as e:
            self.logger.error(f"Map file not found: {e}")
            self._emit_error(f"Map file not found: {map_name}")
        except ValueError as e:
            self.logger.error(f"Failed to import map {map_name}: {e}")
            self._emit_error(f"Failed to import map: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error importing map {map_name}: {e}", exc_info=True)
            self._emit_error(f"Unexpected error importing map: {e}")

    def _emit_state_snapshot(self) -> None:
        """Emit complete state snapshot signals."""
        try:
            # Emit start signal
            self._emit_signal(create_state_snapshot_start_signal())

            # Get full state from world
            full_state = self.world.get_full_state()

            # Emit map data
            self._emit_signal(create_full_map_data_signal(full_state["graph"]))

            # Emit agent data for each agent
            for agent_data in full_state["agents"]:
                self._emit_signal(create_full_agent_data_signal(agent_data))

            # Emit end signal
            self._emit_signal(create_state_snapshot_end_signal())

            self.logger.info("State snapshot emitted successfully")

        except Exception as e:
            self.logger.error(f"Error emitting state snapshot: {e}", exc_info=True)
            self._emit_error(f"Failed to emit state snapshot: {e}")

    def _handle_request_state_action(self) -> None:
        """Handle request state action."""
        self._emit_state_snapshot()
        self.logger.info("State snapshot requested and emitted")
