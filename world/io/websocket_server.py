"""FastAPI WebSocket server for Frontend-Backend communication."""

import asyncio
import logging
from typing import Any

import orjson
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from ..sim.actions.action_parser import ActionParser
from ..sim.queues import (
    ActionQueue,
    SignalQueue,
    create_full_agent_data_signal,
    create_full_map_data_signal,
    create_state_snapshot_end_signal,
    create_state_snapshot_start_signal,
)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.connection_ids: set[str] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Accept a WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            self.connection_ids.add(connection_id)
        logging.info(f"WebSocket connected: {connection_id}")

    async def disconnect(self, websocket: WebSocket, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            self.connection_ids.discard(connection_id)
        logging.info(f"WebSocket disconnected: {connection_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logging.error(f"Failed to send personal message: {e}")

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected WebSockets."""
        if not self.active_connections:
            return

        # Create a copy of connections to avoid modification during iteration
        connections_to_remove = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logging.error(f"Failed to send broadcast message: {e}")
                connections_to_remove.append(connection)

        # Remove failed connections
        async with self._lock:
            for connection in connections_to_remove:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)


def _ensure_str_keys(obj: Any) -> Any:
    """Recursively convert all dict keys to strings for JSON serialization.

    orjson requires mapping keys to be strings at all nesting levels.
    """
    if isinstance(obj, dict):
        return {str(k): _ensure_str_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_ensure_str_keys(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_ensure_str_keys(v) for v in obj)
    return obj


class WebSocketServer:
    """WebSocket server for Frontend-Backend communication (Actions ↔ Signals)."""

    def __init__(
        self,
        action_queue: ActionQueue,
        signal_queue: SignalQueue,
        controller: Any = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.action_queue = action_queue
        self.signal_queue = signal_queue
        self.controller = controller
        self.logger = logger or logging.getLogger(__name__)
        self.manager = ConnectionManager()
        self.app = FastAPI(title="SPINE Simulation WebSocket API")
        self.action_parser = ActionParser()
        self._setup_routes()
        self._signal_broadcast_task: asyncio.Task[None] | None = None

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        @self.app.websocket("/ws")  # type: ignore[misc]
        async def websocket_endpoint(websocket: WebSocket) -> None:
            """WebSocket endpoint for Frontend-Backend communication."""
            connection_id = f"conn_{id(websocket)}"
            await self.manager.connect(websocket, connection_id)

            # Send state snapshot if simulation is running or paused
            if self.controller and self.controller.state.running:
                self.logger.info(
                    f"Sending state snapshot to new client {connection_id} (simulation running: {self.controller.state.running}, paused: {self.controller.state.paused})"
                )
                await self._send_state_snapshot_to_client(websocket)
            else:
                self.logger.info(
                    f"Not sending state snapshot to new client {connection_id} (controller: {self.controller is not None}, running: {self.controller.state.running if self.controller else 'N/A'})"
                )

            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()
                    await self._handle_client_message(data, connection_id)

            except WebSocketDisconnect:
                await self.manager.disconnect(websocket, connection_id)
            except Exception as e:
                self.logger.error(f"WebSocket error for {connection_id}: {e}", exc_info=True)
                await self.manager.disconnect(websocket, connection_id)

        @self.app.get("/health")  # type: ignore[misc]
        async def health_check() -> dict[str, str]:
            """Health check endpoint."""
            return {"status": "healthy", "service": "spine-websocket"}

    async def _handle_client_message(self, message: str, connection_id: str) -> None:
        """Handle a message received from a client."""
        try:
            # Parse JSON message
            data = orjson.loads(message)

            # Validate and parse action request
            action_request = self.action_parser.parse(data)

            # Send action request to backend
            try:
                self.action_queue.put(action_request, timeout=1.0)
            except Exception as e:
                self.logger.error(f"Failed to queue action from {connection_id}: {e}")
                error_message = orjson.dumps(
                    {
                        "type": "error",
                        "message": "Action queue is full or unavailable",
                        "status": "error",
                    }
                ).decode()
                await self._send_error_to_connection(connection_id, error_message)
                return

            self.logger.debug(f"Received action from {connection_id}: {action_request.action}")

        except (ValidationError, ValueError) as e:
            self.logger.warning(f"Invalid action from {connection_id}: {e}")
            error_message = orjson.dumps(
                {"type": "error", "message": f"Invalid action: {e}", "status": "error"}
            ).decode()
            await self._send_error_to_connection(connection_id, error_message)

        except orjson.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON from {connection_id}: {e}")
            error_message = orjson.dumps(
                {"type": "error", "message": "Invalid JSON format", "status": "error"}
            ).decode()
            await self._send_error_to_connection(connection_id, error_message)

        except Exception as e:
            self.logger.error(f"Error handling message from {connection_id}: {e}", exc_info=True)
            error_message = orjson.dumps(
                {"type": "error", "message": "Internal server error", "status": "error"}
            ).decode()
            await self._send_error_to_connection(connection_id, error_message)

    async def _send_message_to_connection(self, connection_id: str, message: str) -> None:
        """Send a message to a specific connection."""
        try:
            # Find the connection by ID
            connection = None
            for conn in self.manager.active_connections:
                if f"conn_{id(conn)}" == connection_id:
                    connection = conn
                    break

            if connection:
                await self.manager.send_personal_message(message, connection)
            else:
                self.logger.warning(f"Connection {connection_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to send message to {connection_id}: {e}")

    async def _send_error_to_connection(self, connection_id: str, error_message: str) -> None:
        """Send an error message to a specific connection."""
        await self._send_message_to_connection(connection_id, error_message)

    async def start_signal_broadcast(self) -> None:
        """Start the signal broadcast task."""
        if self._signal_broadcast_task and not self._signal_broadcast_task.done():
            return

        self._signal_broadcast_task = asyncio.create_task(self._broadcast_signals())
        self.logger.info("Signal broadcast task started")

    async def stop_signal_broadcast(self) -> None:
        """Stop the signal broadcast task."""
        if self._signal_broadcast_task and not self._signal_broadcast_task.done():
            try:
                self._signal_broadcast_task.cancel()
            except RuntimeError as e:
                # Handle the case where the task is attached to a different loop
                if "attached to a different loop" in str(e):
                    self.logger.warning(
                        "Signal broadcast task attached to different loop, cannot cancel"
                    )
                    return
                else:
                    raise

            try:
                await self._signal_broadcast_task
            except asyncio.CancelledError:
                pass
            except RuntimeError as e:
                # Handle the case where the task is attached to a different loop
                if "attached to a different loop" in str(e):
                    self.logger.warning(
                        "Signal broadcast task attached to different loop, skipping await"
                    )
                else:
                    raise
        self.logger.info("Signal broadcast task stopped")

    async def _broadcast_signals(self) -> None:
        """Continuously broadcast signals from the signal queue."""
        while True:
            try:
                # Get signal from queue (non-blocking)
                signal = self.signal_queue.get_nowait()
                if signal is None:
                    await asyncio.sleep(0.01)  # Short sleep to avoid busy waiting
                    continue

                # Convert signal to JSON (ensure all dict keys are strings)
                # Signal.model_dump() already returns {"signal": "...", "data": {...}}
                signal_dict = signal.model_dump()
                safe_signal_dict = _ensure_str_keys(signal_dict)
                message = orjson.dumps(safe_signal_dict, option=orjson.OPT_NON_STR_KEYS).decode()

                # Broadcast to all connected clients
                await self.manager.broadcast(message)

                self.logger.debug(f"Broadcasted signal: {signal.signal}")

            except Exception as e:
                self.logger.error(f"Error in signal broadcast: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # Wait before retrying

    def get_app(self) -> FastAPI:
        """Get the FastAPI application."""
        return self.app

    async def _send_state_snapshot_to_client(self, websocket: WebSocket) -> None:
        """Send complete state snapshot to a specific client."""
        try:
            self.logger.info("Starting state snapshot transmission to client")

            # Get full state from controller's world
            full_state = self.controller.world.get_full_state()
            self.logger.info(
                f"Retrieved full state: {len(full_state['agents'])} agents, {len(full_state['graph']['nodes'])} nodes, {len(full_state['graph']['edges'])} edges"
            )

            # Send start signal
            start_signal = create_state_snapshot_start_signal()
            await self.manager.send_personal_message(
                orjson.dumps(
                    _ensure_str_keys(start_signal.model_dump()),
                    option=orjson.OPT_NON_STR_KEYS,
                ).decode(),
                websocket,
            )
            self.logger.info("Sent state_snapshot_start signal")

            # Send map data
            map_signal = create_full_map_data_signal(full_state["graph"])
            await self.manager.send_personal_message(
                orjson.dumps(
                    _ensure_str_keys(map_signal.model_dump()),
                    option=orjson.OPT_NON_STR_KEYS,
                ).decode(),
                websocket,
            )
            self.logger.info("Sent full_map_data signal")

            # Send agent data for each agent
            for agent_data in full_state["agents"]:
                agent_signal = create_full_agent_data_signal(agent_data)
                await self.manager.send_personal_message(
                    orjson.dumps(
                        _ensure_str_keys(agent_signal.model_dump()),
                        option=orjson.OPT_NON_STR_KEYS,
                    ).decode(),
                    websocket,
                )
            self.logger.info(f"Sent {len(full_state['agents'])} full_agent_data signals")

            # Send end signal
            end_signal = create_state_snapshot_end_signal()
            await self.manager.send_personal_message(
                orjson.dumps(
                    _ensure_str_keys(end_signal.model_dump()),
                    option=orjson.OPT_NON_STR_KEYS,
                ).decode(),
                websocket,
            )
            self.logger.info("Sent state_snapshot_end signal")

            self.logger.info("State snapshot sent to new client")

        except Exception as e:
            self.logger.error(f"Error sending state snapshot to client: {e}", exc_info=True)


# Convenience function for creating common client messages
def create_start_message(tick_rate: float = 20.0) -> str:
    """Create a start simulation message."""
    message = {"type": "start", "tick_rate": tick_rate}
    return orjson.dumps(message).decode()


def create_stop_message() -> str:
    """Create a stop simulation message."""
    message = {"type": "stop"}
    return orjson.dumps(message).decode()


def create_pause_message() -> str:
    """Create a pause simulation message."""
    message = {"type": "pause"}
    return orjson.dumps(message).decode()


def create_resume_message() -> str:
    """Create a resume simulation message."""
    message = {"type": "resume"}
    return orjson.dumps(message).decode()


def create_set_tick_rate_message(tick_rate: float) -> str:
    """Create a set tick rate message."""
    message = {"type": "set_tick_rate", "tick_rate": tick_rate}
    return orjson.dumps(message).decode()


def create_delete_agent_message(agent_id: str) -> str:
    """Create a delete agent message."""
    message = {"type": "delete_agent", "agent_id": agent_id}
    return orjson.dumps(message).decode()


def create_add_agent_message(agent_id: str, agent_kind: str, agent_data: dict[str, Any]) -> str:
    """Create an add agent message."""
    message = {
        "type": "add_agent",
        "agent_id": agent_id,
        "agent_kind": agent_kind,
        "agent_data": agent_data,
    }
    return orjson.dumps(message).decode()
