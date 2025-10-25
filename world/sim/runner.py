"""Main entry point for running the Backend with WebSocket server."""

import asyncio
import logging
import signal
import sys
import threading
import time
from typing import Any

import uvicorn

from core.types import EdgeID, NodeID
from world.graph.edge import Edge, Mode
from world.graph.graph import Graph
from world.graph.node import Node
from world.io.websocket_server import WebSocketServer
from world.world import World

from .controller import SimulationController
from .queues import ActionQueue, SignalQueue


class SimulationRunner:
    """Orchestrates the Backend simulation and WebSocket server."""

    def __init__(
        self,
        world: World,
        host: str = "localhost",
        port: int = 8000,
        log_level: str = "INFO",
    ) -> None:
        self.world = world
        self.host = host
        self.port = port

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger(__name__)

        # Create queues
        self.action_queue = ActionQueue()
        self.signal_queue = SignalQueue()

        # Create controller and WebSocket server
        self.controller = SimulationController(
            world=self.world,
            action_queue=self.action_queue,
            signal_queue=self.signal_queue,
            logger=self.logger,
        )

        self.websocket_server = WebSocketServer(
            action_queue=self.action_queue,
            signal_queue=self.signal_queue,
            logger=self.logger,
        )

        # Thread management
        self._controller_thread: threading.Thread | None = None
        self._websocket_thread: threading.Thread | None = None
        self._signal_broadcast_task: asyncio.Task[None] | None = None
        self._shutdown_event = threading.Event()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, _frame: Any) -> None:
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()

    def start(self) -> None:
        """Start both the Backend simulation controller and WebSocket server."""
        self.logger.info("Starting SPINE Backend runner...")

        # Start simulation controller
        self.controller.start()
        self._controller_thread = self.controller._thread

        # Start WebSocket server
        self._start_websocket_server()

        self.logger.info(f"Backend runner started on {self.host}:{self.port}")
        self.logger.info("Press Ctrl+C to stop")

        try:
            # Keep main thread alive
            while not self._shutdown_event.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.shutdown()

    def _start_websocket_server(self) -> None:
        """Start the WebSocket server in a separate thread."""

        def run_server() -> None:
            # Start event broadcast task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Start the signal broadcast task and store reference
            loop.run_until_complete(self.websocket_server.start_signal_broadcast())
            self._signal_broadcast_task = self.websocket_server._signal_broadcast_task

            # Run the server
            config = uvicorn.Config(
                app=self.websocket_server.get_app(),
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False,
            )
            server = uvicorn.Server(config)
            loop.run_until_complete(server.serve())

        self._websocket_thread = threading.Thread(target=run_server, daemon=True)
        self._websocket_thread.start()

    def shutdown(self) -> None:
        """Shutdown the simulation runner gracefully."""
        self.logger.info("Shutting down simulation runner...")

        # Set shutdown event
        self._shutdown_event.set()

        # Stop simulation controller
        if self.controller:
            self.controller.stop()

        # Stop WebSocket server signal broadcast
        if self.websocket_server and self._signal_broadcast_task:
            try:
                # Cancel the task if it's still running
                if not self._signal_broadcast_task.done():
                    self._signal_broadcast_task.cancel()
            except Exception as e:
                self.logger.warning(f"Error cancelling signal broadcast task: {e}")

        # Wait for threads to finish
        if self._controller_thread and self._controller_thread.is_alive():
            self._controller_thread.join(timeout=5.0)

        if self._websocket_thread and self._websocket_thread.is_alive():
            self._websocket_thread.join(timeout=5.0)

        self.logger.info("Simulation runner shutdown complete")

    def get_status(self) -> dict[str, Any]:
        """Get the current status of the Backend simulation."""
        return {
            "controller_running": self.controller.state.running,
            "controller_paused": self.controller.state.paused,
            "current_tick": self.controller.state.current_tick,
            "tick_rate": self.controller.state.tick_rate,
            "action_queue_size": self.action_queue.qsize(),
            "signal_queue_size": self.signal_queue.qsize(),
            "agent_count": len(self.world.agents),
        }


def create_default_world() -> World:
    """Create a default world for testing."""
    # Create a simple graph
    graph = Graph()

    # Add some nodes
    node1 = Node(id=NodeID(1), x=0, y=0)
    node2 = Node(id=NodeID(2), x=100, y=0)
    node3 = Node(id=NodeID(3), x=50, y=50)

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)

    # Add some edges
    edge1 = Edge(id=EdgeID(1), from_node=NodeID(1), to_node=NodeID(2), length_m=100, mode=Mode.ROAD)
    edge2 = Edge(id=EdgeID(2), from_node=NodeID(1), to_node=NodeID(3), length_m=50, mode=Mode.ROAD)
    edge3 = Edge(id=EdgeID(3), from_node=NodeID(3), to_node=NodeID(2), length_m=50, mode=Mode.ROAD)

    graph.add_edge(edge1)
    graph.add_edge(edge2)
    graph.add_edge(edge3)

    # Create world with dummy router and traffic
    world = World(graph=graph, router=None, traffic=None)

    return world


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SPINE Simulation Runner")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args()

    # Create world
    world = create_default_world()

    # Create and start runner
    runner = SimulationRunner(
        world=world,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )

    try:
        runner.start()
    except Exception as e:
        logging.error(f"Error in simulation runner: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
