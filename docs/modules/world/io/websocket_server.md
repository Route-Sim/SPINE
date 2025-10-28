---
title: "WebSocket Server"
summary: "FastAPI WebSocket server for bidirectional communication between frontend and simulation with connection management, event broadcasting, and robust error handling."
source_paths:
  - "world/io/websocket_server.py"
last_updated: "2025-10-26"
owner: "Mateusz Polis"
tags: ["module", "api", "infra"]
links:
  parent: "../../SUMMARY.md"
  siblings: []
---

# WebSocket Server

> **Purpose:** Provides bidirectional WebSocket communication between frontend clients and the simulation, handling command routing and event broadcasting.

## Context & Motivation

The SPINE simulation requires real-time communication with frontend clients for:
- **Command Reception**: Start/stop/pause simulation, agent management
- **Event Broadcasting**: Tick markers, agent updates, world events
- **Multiple Clients**: Support for concurrent WebSocket connections
- **Error Handling**: Graceful handling of malformed messages and connection issues

This module implements a FastAPI-based WebSocket server with connection management and event broadcasting.

## Responsibilities & Boundaries

**In-scope:**
- WebSocket connection management and routing
- Command validation and queuing to simulation
- Event broadcasting to all connected clients
- Error handling and client feedback
- Health check endpoint

**Out-of-scope:**
- Simulation logic (handled by SimulationController)
- Message validation (handled by Pydantic models)
- Frontend UI logic (handled by client)

## Architecture & Design

### Core Components

**WebSocketServer**: Main server class
- FastAPI application with WebSocket endpoints
- Connection management and message routing
- Event broadcasting to all clients

**ConnectionManager**: WebSocket connection management
- Active connection tracking
- Personal and broadcast messaging
- Connection lifecycle management

### Message Flow

```
Frontend → WebSocket → JSON Validation → CommandQueue → Simulation
Simulation → EventQueue → Event Broadcasting → WebSocket → Frontend
```

### Connection Management

```
Client Connect → ConnectionManager → Active Connections
Client Disconnect → ConnectionManager → Remove from Active
Message → Validation → CommandQueue → Acknowledgment
```

## Algorithms & Complexity

**Connection Management**: O(n) where n = number of active connections
- Linear scan for connection lookup
- Broadcast to all connections
- Connection cleanup on disconnect

**Message Processing**: O(1) per message
- JSON parsing and validation
- Command queuing with timeout
- Error response generation

**Event Broadcasting**: O(n) where n = number of active connections
- Non-blocking broadcast to all connections
- Failed connection cleanup
- Event queue polling

## Public API / Usage

### Server Lifecycle
```python
server = WebSocketServer(command_queue, event_queue)
app = server.get_app()  # Get FastAPI app
await server.start_event_broadcast()  # Start event broadcasting
await server.stop_event_broadcast()  # Stop event broadcasting
```

### WebSocket Endpoints
- `ws://localhost:8000/ws` - Main WebSocket endpoint
- `GET /health` - Health check endpoint

### Message Format
```json
// Commands (Frontend → Server)
{
  "type": "start",
  "tick_rate": 30.0
}

// Events (Server → Frontend)
{
  "type": "tick_start",
  "tick": 123
}
```

### Connection Management
```python
# Automatic connection tracking
# Personal messaging to specific connections
# Broadcast messaging to all connections
```

## Implementation Notes

**FastAPI Integration**: Uses FastAPI WebSocket endpoints

**Connection Tracking**: Maintains list of active connections with unique identifiers

**Error Handling**: Comprehensive error handling with client feedback
- JSON parsing errors handled gracefully
- Validation errors result in error messages to client
- Connection errors isolated from simulation

**Event Broadcasting**: Continuous event streaming from simulation
- Background task for signal broadcasting
- Robust task cancellation handling for different event loop scenarios

### State Snapshot on Client Connection

The WebSocket server automatically sends complete state snapshots to new clients when appropriate:

**When State Snapshots Are Sent**:
- When a new client connects during running or paused simulation
- NOT sent when simulation is pre-started (stopped state)

**State Snapshot Process**:
1. Client connects to WebSocket endpoint
2. Server checks if simulation is running or paused
3. If true, sends complete state snapshot directly to that client
4. Client receives state before any regular tick signals

**State Snapshot Sequence**:
1. `state_snapshot_start` - Marks beginning
2. `full_map_data` - Complete map structure
3. `full_agent_data` - One signal per agent
4. `state_snapshot_end` - Marks completion

This ensures new clients joining mid-simulation receive complete context before incremental updates.

### Supported Commands
- `start`: Begin simulation with optional tick rate
- `stop`: Stop simulation
- `pause`/`resume`: Pause/resume simulation
- `set_tick_rate`: Change simulation speed
- `add_agent`/`delete_agent`/`modify_agent`: Agent management
- `export_map`/`import_map`: Map management
- `request_state`: Request complete state snapshot

### Event Types
- `tick_start`/`tick_end`: Tick boundary markers
- `agent_update`: Agent state changes
- `world_event`: General world events
- `error`: Error notifications
- `command_ack`: Command acknowledgments
- `simulation_*`: Simulation state changes
- `map_exported`/`map_imported`: Map operation confirmations
- `state_snapshot_start`/`state_snapshot_end`: State snapshot boundaries
- `full_map_data`: Complete map structure
- `full_agent_data`: Complete agent state

## Tests

Comprehensive test coverage includes:
- Connection management (connect/disconnect)
- Message handling (valid/invalid commands)
- Event broadcasting
- Error handling and client feedback
- WebSocket endpoint functionality
- Integration with command/event queues

## Performance

**Connection Overhead**: ~1KB per active connection
**Message Throughput**: ~1000 messages/second per connection
**Broadcast Performance**: O(n) where n = number of connections
**Memory Usage**: Minimal per connection, event queue buffering

## Security & Reliability

**Input Validation**: All messages validated with Pydantic
**Error Isolation**: Connection errors don't affect simulation
**Graceful Degradation**: Failed connections removed automatically
**Resource Management**: Configurable connection limits
**Signal Handling**: Robust task cancellation with different event loop handling

## References

- [world/sim/controller.md](../sim/controller.md) - Simulation control
- [world/sim/queues.md](../sim/queues.md) - Message infrastructure
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
