# SPINE Documentation

## Overview
* [Project Overview](index.md)

## API Reference
* [WebSocket API Reference](api-reference.md)
* [Postman Collection](postman-collection.json) - Complete Postman collection with all WebSocket examples
* [Postman Quick Reference](postman-quick-reference.md)

## Glossary
* [Glossary](glossary.md)

## Architecture Decision Records
* [ADRs](adr/)

## Modules

### Core
* [Types](modules/core/types.md)
* [Messages](modules/core/messages.md)
* [FSM](modules/core/fsm.md)
* [Building](modules/core/buildings/base.md)

### World
* [World](modules/world/world.md)
* [Graph](modules/world/graph/graph.md)
* [Node](modules/world/graph/node.md)
* [Edge](modules/world/graph/edge.md)
* [Simulation Controller](modules/world/sim/controller.md)
* [Queue Infrastructure](modules/world/sim/queues.md)
* [Simulation Runner](modules/world/sim/runner.md)
* [WebSocket Server](modules/world/io/websocket_server.md)

### Agents
* [Base Agent](modules/agents/base.md)
* [Building Agent](modules/agents/buildings/building-agent.md)
* [Transport Agent](modules/agents/transports/base.md)

### Tests
* [Core/test_fsm](modules/tests/core/test-fsm.md)
* [Core/test_ids](modules/tests/core/test-ids.md)
* [World/test_sim_runner](modules/tests/world/test-sim-runner.md)
* [World/test_websocket_server](modules/tests/world/test-websocket-server.md)
* [World/test_graph_graphml](modules/tests/world/test-graph-graphml.md)

### Scripts
* [Validate Commit](modules/scripts/validate-commit.md)
* [Update Postman Collection](modules/scripts/update-postman-collection.md)

### Infrastructure
* [Docker Containerization](modules/docker.md)
