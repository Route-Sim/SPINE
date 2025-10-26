---
title: "Simulation Runner"
summary: "Main entry point that orchestrates the simulation controller and WebSocket server in separate threads with graceful shutdown handling and proper uvicorn server lifecycle management."
source_paths:
  - "world/sim/runner.py"
last_updated: "2025-10-25"
owner: "Mateusz Polis"
tags: ["module", "api", "infra"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["controller.md", "queues.md"]
---

# Simulation Runner

> **Purpose:** Orchestrates the complete SPINE simulation system by starting both the simulation controller and WebSocket server in separate threads, managing their lifecycle and providing graceful shutdown.

## Context & Motivation

The SPINE simulation requires coordination between multiple components:
- **Simulation Thread**: Continuous World.step() loop with command processing
- **WebSocket Thread**: FastAPI server handling client connections
- **Main Thread**: Orchestration, logging, and signal handling
- **Graceful Shutdown**: Clean termination of all threads and resources

This module provides the main entry point and orchestration logic.

## Responsibilities & Boundaries

**In-scope:**
- Thread orchestration (simulation + WebSocket)
- Signal handling (SIGINT/SIGTERM)
- Logging configuration
- Graceful shutdown coordination
- Default world creation for testing
- Command-line interface

**Out-of-scope:**
- Simulation logic (handled by SimulationController)
- WebSocket communication (handled by WebSocketServer)
- World creation logic (handled by World class)

## Architecture & Design

### Thread Architecture

```
Main Thread: Runner orchestration + signal handling
├── Simulation Thread: SimulationController + World.step()
└── WebSocket Thread: FastAPI + Uvicorn server
```

### Component Relationships

```
SimulationRunner
├── SimulationController (simulation thread)
│   ├── World instance
│   ├── CommandQueue (commands from WebSocket)
│   └── EventQueue (events to WebSocket)
└── WebSocketServer (WebSocket thread)
    ├── FastAPI app
    ├── ConnectionManager
    └── Event broadcasting
```

### Signal Handling

```
SIGINT/SIGTERM → Signal Handler → Graceful Shutdown
├── Stop SimulationController
├── Stop WebSocket event broadcasting
└── Wait for thread completion
```

## Algorithms & Complexity

**Thread Management**: O(1) for start/stop operations
- Thread creation and lifecycle management
- Signal handling with graceful shutdown
- Resource cleanup and thread joining

**Shutdown Process**: O(n) where n = number of threads
- Stop all components in reverse order
- Wait for thread completion with timeout
- Resource cleanup and logging

## Public API / Usage

### Command Line Interface
```bash
# Run with default settings
python -m world.sim.runner

# Custom host and port
python -m world.sim.runner --host 0.0.0.0 --port 8080

# Custom log level
python -m world.sim.runner --log-level DEBUG
```

### Programmatic Usage
```python
from world.sim.runner import SimulationRunner, create_default_world

# Create world and runner
world = create_default_world()
runner = SimulationRunner(world, host="localhost", port=8000)

# Start the system
runner.start()  # Blocks until shutdown
```

### Status Monitoring
```python
# Get system status
status = runner.get_status()
print(f"Running: {status['controller_running']}")
print(f"Tick: {status['current_tick']}")
print(f"Agents: {status['agent_count']}")
```

## Implementation Notes

**Thread Safety**: All components designed for thread-safe operation with proper synchronization
**Signal Handling**: Proper SIGINT/SIGTERM handling for graceful shutdown
**Logging**: Configurable logging with structured output
**Error Handling**: Comprehensive error handling with logging
**Uvicorn Integration**: Stores server reference for proper shutdown signaling
**Event Loop Management**: Creates and properly cleans up asyncio event loop in WebSocket thread

### Default World Creation
- Simple graph with 3 nodes and 3 edges
- Warehouse and hub node types
- Road edge types with weights
- Ready for agent placement

### Shutdown Process
1. Set shutdown event
2. Stop simulation controller
3. Signal uvicorn server to exit (`server.should_exit = True`)
4. Cancel WebSocket event broadcasting task
5. Wait for threads to complete with timeout (5 seconds)
6. Clean up event loop resources
7. Log shutdown completion

### Server Lifecycle Management
- **Startup Synchronization**: Uses `_server_ready_event` to ensure uvicorn server reference is set before proceeding
- **Graceful Shutdown**: Signals uvicorn server to exit by setting `should_exit` flag
- **Event Loop Cleanup**: Properly closes asyncio event loop in finally block
- **Thread Safety**: All shutdown operations are thread-safe with proper synchronization

## Tests

Integration tests (`tests/world/test_sim_runner.py`) cover:
- Thread lifecycle management with proper cleanup
- Signal handling and graceful shutdown
- Component coordination between controller and WebSocket server
- Error handling and recovery scenarios
- Server shutdown without hanging (uvicorn server properly exits)
- Multiple shutdown calls idempotency
- WebSocket server initialization and teardown

## Performance

**Startup Time**: ~1-2 seconds for full system initialization (includes server ready synchronization)
**Memory Usage**: ~10MB base + ~1MB per active WebSocket connection
**Thread Overhead**: Minimal, dedicated threads for specific tasks
**Shutdown Time**: <1 second typical, 5 seconds maximum with timeout (improved with proper uvicorn shutdown signaling)
**Test Execution**: Integration tests complete in ~3 seconds without hanging

## Security & Reliability

**Signal Handling**: Proper cleanup on termination signals
**Error Isolation**: Component failures don't crash entire system
**Resource Management**: Proper thread and connection cleanup
**Logging**: Comprehensive logging for debugging and monitoring

## References

- [world/sim/controller.md](controller.md) - Simulation control
- [world/io/websocket_server.md](../io/websocket_server.md) - WebSocket communication
- [world/world.md](../world.md) - World simulation logic
