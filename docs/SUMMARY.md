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
* [Building Base Class](modules/core/buildings/base.md)
* [Occupiable Building Base](modules/core/buildings/occupancy.md)
* [Parking Building](modules/core/buildings/parking.md)
* [Site Building](modules/core/buildings/site.md)
* [Gas Station Building](modules/core/buildings/gas-station.md)
* [Package Data Model](modules/core/packages/package.md)

### World
* [World](modules/world/world.md)
* [Graph](modules/world/graph/graph.md)
* [Node](modules/world/graph/node.md)
* [Edge](modules/world/graph/edge.md)
* [Navigator - A* Pathfinding](modules/world/routing/navigator.md)
* [Map Generation](modules/world/generation.md)
* [World Generator](modules/world/generation/generator.md)
* [Generation Parameters](modules/world/generation/params.md)
* [Simulation Controller](modules/world/sim/controller.md)
* [Simulation Control Handler](modules/world/sim/handlers/simulation.md)
* [Agent Action Handler](modules/world/sim/handlers/agent.md)
* [Building Action Handler](modules/world/sim/handlers/building.md)
* [Map Action Handler](modules/world/sim/handlers/map.md)
* [Queue Infrastructure](modules/world/sim/queues.md) - Canonical action/signal queues
* [Signal DTOs](modules/world/sim/signal-dtos.md) - Type-safe signal data structures
* DTOs
  * [Simulation Parameters DTO](modules/world/sim/dto/simulation-dto.md)
  * [Statistics DTOs](modules/world/sim/dto/statistics-dto.md)
* Actions
  * [Action Parser](modules/world/sim/actions/action-parser.md)
  * [Action Registry](modules/world/sim/actions/action-registry.md)
  * [Action Processor](modules/world/sim/actions/action-processor.md)
* [Simulation Runner](modules/world/sim/runner.md)
* [WebSocket Server](modules/world/io/websocket_server.md)
* [Map Manager](modules/world/io/map-manager.md)

### Agents
* [Base Agent](modules/agents/base.md)
* [Building Agent](modules/agents/buildings/building-agent.md)
* [Truck Transport Agent](modules/agents/transports/truck.md)

### Tests
* [Core/test_fsm](modules/tests/core/test-fsm.md)
* [Core/test_ids](modules/tests/core/test-ids.md)
* [Agents/test_truck](modules/tests/agents/test-truck.md)
* [World/test_sim_runner](modules/tests/world/test-sim-runner.md)
* [World/test_websocket_server](modules/tests/world/test-websocket-server.md)
* [World/test_graph_graphml](modules/tests/world/test-graph-graphml.md)
* [World/test_agent_action_handler](modules/tests/world/test-agent-action-handler.md)

### Scripts
* [Validate Commit](modules/scripts/validate-commit.md)
* [Update Postman Collection](modules/scripts/update-postman-collection.md)

### Infrastructure
* [Docker Containerization](modules/docker.md)
