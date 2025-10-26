"""Tests for WebSocket server."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from world.io.websocket_server import ConnectionManager, WebSocketServer
from world.sim.queues import ActionQueue, ActionType, Signal, SignalQueue


class TestConnectionManager:
    """Test ConnectionManager functionality."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_connect_disconnect(self) -> None:
        """Test connection and disconnection."""
        manager = ConnectionManager()
        websocket = AsyncMock()

        # Test connect
        await manager.connect(websocket, "test_conn")
        assert len(manager.active_connections) == 1
        assert "test_conn" in manager.connection_ids

        # Test disconnect
        await manager.disconnect(websocket, "test_conn")
        assert len(manager.active_connections) == 0
        assert "test_conn" not in manager.connection_ids

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_send_personal_message(self) -> None:
        """Test sending personal message."""
        manager = ConnectionManager()
        websocket = AsyncMock()

        await manager.connect(websocket, "test_conn")
        await manager.send_personal_message("test message", websocket)

        websocket.send_text.assert_called_once_with("test message")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_broadcast(self) -> None:
        """Test broadcasting to all connections."""
        manager = ConnectionManager()
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()

        await manager.connect(websocket1, "conn1")
        await manager.connect(websocket2, "conn2")

        await manager.broadcast("broadcast message")

        websocket1.send_text.assert_called_once_with("broadcast message")
        websocket2.send_text.assert_called_once_with("broadcast message")


class TestWebSocketServer:
    """Test WebSocketServer functionality."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.action_queue = ActionQueue()
        self.signal_queue = SignalQueue()
        self.server = WebSocketServer(
            action_queue=self.action_queue,
            signal_queue=self.signal_queue,
        )

    def test_initialization(self) -> None:
        """Test server initialization."""
        assert self.server.action_queue is self.action_queue
        assert self.server.signal_queue is self.signal_queue
        assert self.server.app is not None
        assert isinstance(self.server.manager, ConnectionManager)

    def test_get_app(self) -> None:
        """Test getting FastAPI app."""
        app = self.server.get_app()
        assert app is not None
        assert app == self.server.app

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_handle_valid_action(self) -> None:
        """Test handling valid action."""
        websocket = AsyncMock()
        connection_id = "test_conn"

        # Mock the connection manager
        self.server.manager.active_connections = [websocket]

        # Create valid action message
        action_data = {"type": "start", "tick_rate": 30.0}
        message = json.dumps(action_data)

        await self.server._handle_client_message(message, connection_id)

        # Verify action was queued
        assert not self.action_queue.empty()
        action = self.action_queue.get_nowait()
        assert action is not None
        assert action.type == ActionType.START
        assert action.tick_rate == 30.0

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_handle_invalid_json(self) -> None:
        """Test handling invalid JSON."""
        websocket = AsyncMock()
        connection_id = "test_conn"

        # Mock the connection manager
        self.server.manager.active_connections = [websocket]

        # Invalid JSON message
        message = "invalid json {"

        await self.server._handle_client_message(message, connection_id)

        # Verify no action was queued
        assert self.action_queue.empty()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_handle_invalid_command(self) -> None:
        """Test handling invalid command."""
        websocket = AsyncMock()
        connection_id = "test_conn"

        # Mock the connection manager
        self.server.manager.active_connections = [websocket]

        # Invalid command (missing required fields)
        command_data = {
            "type": "add_agent"
            # Missing agent_id and agent_kind
        }
        message = json.dumps(command_data)

        await self.server._handle_client_message(message, connection_id)

        # Verify no action was queued
        assert self.action_queue.empty()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_send_message_to_connection(self) -> None:
        """Test sending message to specific connection."""
        websocket = AsyncMock()
        connection_id = "conn_123"

        # Mock the connection manager
        self.server.manager.active_connections = [websocket]

        # Mock the websocket ID
        with patch("builtins.id", return_value=123):
            await self.server._send_message_to_connection(connection_id, "test message")

        websocket.send_text.assert_called_once_with("test message")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_send_error_to_connection(self) -> None:
        """Test sending error to specific connection."""
        websocket = AsyncMock()
        connection_id = "conn_123"

        # Mock the connection manager
        self.server.manager.active_connections = [websocket]

        # Mock the websocket ID
        with patch("builtins.id", return_value=123):
            await self.server._send_error_to_connection(connection_id, "error message")

        websocket.send_text.assert_called_once_with("error message")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_start_stop_signal_broadcast(self) -> None:
        """Test starting and stopping signal broadcast."""
        # Start signal broadcast
        await self.server.start_signal_broadcast()
        assert self.server._signal_broadcast_task is not None
        assert not self.server._signal_broadcast_task.done()

        # Stop signal broadcast
        await self.server.stop_signal_broadcast()
        assert self.server._signal_broadcast_task is not None
        assert self.server._signal_broadcast_task.cancelled()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_broadcast_signals(self) -> None:
        """Test broadcasting signals from queue."""
        # Add signal to queue
        from world.sim.queues import SignalType

        signal = Signal(type=SignalType.TICK_START, tick=100)
        self.signal_queue.put(signal)

        # Mock broadcast method
        self.server.manager.broadcast = AsyncMock()  # type: ignore[method-assign]

        # Start broadcast task
        await self.server.start_signal_broadcast()

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Stop broadcast task
        await self.server.stop_signal_broadcast()

        # Verify broadcast was called
        self.server.manager.broadcast.assert_called()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_signal_broadcast_task_cancellation(self) -> None:
        """Test that signal broadcast task is properly cancelled."""
        # Start signal broadcast
        await self.server.start_signal_broadcast()
        task = self.server._signal_broadcast_task

        # Cancel the task
        assert task is not None
        task.cancel()

        # Try to stop signal broadcast (should handle cancellation gracefully)
        await self.server.stop_signal_broadcast()

        # Task should be cancelled
        assert task.cancelled()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_signal_broadcast_different_loop_error(self) -> None:
        """Test handling of different loop error in signal broadcast."""
        # Start signal broadcast
        await self.server.start_signal_broadcast()
        task = self.server._signal_broadcast_task

        # Mock a RuntimeError for different loop
        with patch.object(task, "cancel", side_effect=RuntimeError("attached to a different loop")):
            # Should handle the error gracefully
            await self.server.stop_signal_broadcast()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_multiple_start_signal_broadcast(self) -> None:
        """Test that multiple start calls don't create multiple tasks."""
        # Start signal broadcast twice
        await self.server.start_signal_broadcast()
        first_task = self.server._signal_broadcast_task

        await self.server.start_signal_broadcast()
        second_task = self.server._signal_broadcast_task

        # Should be the same task
        assert first_task is second_task

        # Clean up
        await self.server.stop_signal_broadcast()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_websocket_endpoint(self) -> None:
        """Test WebSocket endpoint handling."""
        from fastapi import WebSocketDisconnect

        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        # First call returns a message, second call raises disconnect
        websocket.receive_text = AsyncMock(
            side_effect=[
                '{"type": "start", "tick_rate": 25.0}',
                WebSocketDisconnect(),
            ]
        )

        # Mock the endpoint function
        endpoint_func = None
        for route in self.server.app.routes:
            if hasattr(route, "path") and route.path == "/ws":
                endpoint_func = route.endpoint
                break

        assert endpoint_func is not None

        # Test the endpoint
        await endpoint_func(websocket)

        # Verify websocket was accepted
        websocket.accept.assert_called_once()

    def test_health_endpoint(self) -> None:
        """Test health check endpoint."""
        # Get the health endpoint function
        health_func = None
        for route in self.server.app.routes:
            if hasattr(route, "path") and route.path == "/health":
                health_func = route.endpoint
                break

        assert health_func is not None

        # Test the endpoint
        response = asyncio.run(health_func())
        assert response == {"status": "healthy", "service": "spine-websocket"}


class TestWebSocketIntegration:
    """Test WebSocket server integration."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_full_communication_flow(self) -> None:
        """Test full communication flow between client and server."""
        action_queue = ActionQueue()
        signal_queue = SignalQueue()
        server = WebSocketServer(action_queue, signal_queue)

        # Mock websocket
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock(
            side_effect=[
                '{"type": "start", "tick_rate": 30.0}',
                '{"type": "add_agent", "agent_id": "agent1", "agent_kind": "transport"}',
                '{"type": "stop"}',
            ]
        )
        websocket.send_text = AsyncMock()

        # Mock connection manager
        server.manager.active_connections = [websocket]

        # Simulate receiving messages
        connection_id = "test_conn"

        # Start action
        await server._handle_client_message('{"type": "start", "tick_rate": 30.0}', connection_id)
        assert not action_queue.empty()
        action = action_queue.get_nowait()
        assert action is not None
        assert action.type == ActionType.START
        assert action.tick_rate == 30.0

        # Add agent action
        await server._handle_client_message(
            '{"type": "add_agent", "agent_id": "agent1", "agent_kind": "transport"}', connection_id
        )
        assert not action_queue.empty()
        action = action_queue.get_nowait()
        assert action is not None
        assert action.type == ActionType.ADD_AGENT
        assert action.agent_id == "agent1"
        assert action.agent_kind == "transport"

        # Stop action
        await server._handle_client_message('{"type": "stop"}', connection_id)
        assert not action_queue.empty()
        action = action_queue.get_nowait()
        assert action is not None
        assert action.type == ActionType.STOP

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_error_handling_flow(self) -> None:
        """Test error handling in communication flow."""
        action_queue = ActionQueue()
        signal_queue = SignalQueue()
        server = WebSocketServer(action_queue, signal_queue)

        # Mock websocket
        websocket = AsyncMock()
        server.manager.active_connections = [websocket]

        connection_id = "test_conn"

        # Test invalid JSON
        await server._handle_client_message("invalid json", connection_id)
        assert action_queue.empty()  # No action should be queued

        # Test invalid action
        await server._handle_client_message('{"type": "invalid_type"}', connection_id)
        assert action_queue.empty()  # No action should be queued

        # Test missing required fields
        await server._handle_client_message('{"type": "add_agent"}', connection_id)
        assert action_queue.empty()  # No action should be queued
