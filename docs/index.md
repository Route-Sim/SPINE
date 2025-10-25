---
title: "SPINE - Simulation Processing & INteraction Engine"
summary: "Agent-based simulation framework for logistics networks with real-time WebSocket communication and multi-threaded architecture."
source_paths:
  - "README.md"
  - "pyproject.toml"
last_updated: "2025-10-25"
owner: "Mateusz Polis"
tags: ["overview", "architecture"]
links:
  parent: "SUMMARY.md"
  siblings: []
---

# SPINE - Simulation Processing & INteraction Engine

> **Purpose:** A multi-threaded agent-based simulation framework for logistics networks with real-time WebSocket communication, designed for interactive frontend applications.

## Project Overview

SPINE is a sophisticated simulation engine that models logistics networks using autonomous agents. The system provides:

- **Agent-Based Simulation**: Buildings, transports, and other entities as autonomous agents
- **Real-Time Communication**: WebSocket-based bidirectional communication with frontend
- **Multi-Threaded Architecture**: Separate threads for simulation and communication
- **Interactive Control**: Start/stop/pause simulation, add/remove agents in real-time
- **Event Streaming**: Delta-based updates with tick markers for frontend synchronization

## High-Level Architecture

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Frontend      │ ←─────────────→ │  WebSocket      │
│   (Client)      │                │  Server         │
└─────────────────┘                └─────────────────┘
                                           │
                                           │ Queues
                                           ▼
┌─────────────────┐                ┌─────────────────┐
│  Simulation     │ ←─────────────→ │  Command/Event  │
│  Controller     │                │  Queues         │
└─────────────────┘                └─────────────────┘
         │
         │ World.step()
         ▼
┌─────────────────┐
│      World      │
│   (Agents +     │
│    Graph)       │
└─────────────────┘
```

## Key Components

### Core Simulation
- **World**: Main simulation container with agents and graph
- **Agents**: Autonomous entities (buildings, transports) with decision-making
- **Graph**: Network topology with nodes and edges
- **Messages**: Inter-agent communication system

### Communication Layer
- **WebSocket Server**: FastAPI-based real-time communication
- **Queue Infrastructure**: Thread-safe command/event queues
- **Message Validation**: Pydantic-based message validation

### Control Layer
- **Simulation Controller**: Manages simulation loop and command processing
- **Runner**: Orchestrates all components with graceful shutdown
- **State Management**: Thread-safe simulation state tracking

## Technology Stack

- **Python 3.10+**: Core language
- **FastAPI**: WebSocket server and API
- **Pydantic**: Message validation and serialization
- **NetworkX**: Graph operations
- **Uvicorn**: ASGI server
- **pytest**: Testing framework

## Getting Started

### Installation
```bash
# Install dependencies
poetry install

# Run the simulation
python -m world.sim.runner --host localhost --port 8000
```

### WebSocket Communication
```javascript
// Connect to simulation
const ws = new WebSocket('ws://localhost:8000/ws');

// Start simulation
ws.send(JSON.stringify({
  "type": "start",
  "tick_rate": 30.0
}));

// Listen for events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data);
};
```

## Module Map

### Core Modules
- [core/types.md](modules/core/types.md) - Type definitions and IDs
- [core/messages.md](modules/core/messages.md) - Inter-agent messaging
- [core/fsm.md](modules/core/fsm.md) - Finite state machines

### World Modules
- [world/world.md](modules/world/world.md) - Main simulation world
- [world/graph/graph.md](modules/world/graph/graph.md) - Network topology
- [world/sim/controller.md](modules/world/sim/controller.md) - Simulation control
- [world/io/websocket_server.md](modules/world/io/websocket_server.md) - WebSocket communication

### Agent Modules
- [agents/base.md](modules/agents/base.md) - Base agent class
- [agents/buildings/building.md](modules/agents/buildings/building.md) - Building agents
- [agents/transports/base.md](modules/agents/transports/base.md) - Transport agents

## Design Principles

1. **Separation of Concerns**: Clear boundaries between simulation, communication, and control
2. **Thread Safety**: All components designed for concurrent operation
3. **Event-Driven**: Delta-based updates with explicit tick markers
4. **Extensibility**: Plugin architecture for new agent types
5. **Reliability**: Comprehensive error handling and graceful degradation

## Performance Characteristics

- **Simulation Speed**: Configurable tick rate (0.1-100 Hz)
- **Agent Capacity**: Supports thousands of concurrent agents
- **WebSocket Connections**: Multiple concurrent clients
- **Memory Usage**: Efficient delta-based updates
- **Latency**: Sub-millisecond command processing

## References

- [Architecture Decision Records](adr/) - Design decisions and rationale
- [Glossary](glossary.md) - Terms and definitions
- [Module Documentation](modules/) - Detailed component documentation
