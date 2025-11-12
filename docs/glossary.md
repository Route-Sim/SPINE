---
title: "Glossary"
summary: "Definitions and abbreviations used throughout the SPINE project."
source_paths: []
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["glossary"]
links:
  parent: "SUMMARY.md"
  siblings: []
---

# Glossary

## A

**A (Autostrada)**: Polish road classification for motorways. Highest class roads with 4-6 lanes, speeds of 120-140 km/h, and no weight limits. Used for major inter-city connections.

**A* Pathfinding**: Heuristic search algorithm for computing optimal routes through a graph. Uses both actual cost from start (g-score) and estimated cost to goal (h-score) to efficiently find shortest paths. Used by the Navigator service for truck routing.

**Action**: A canonical command envelope sent from the frontend to the simulation in the form `{"action": "<domain>.<action>", "params": {...}}`. Actions express user commands such as starting the simulation, managing agents, or modifying map assets.

**ActionQueue**: Thread-safe queue that transports validated `ActionRequest` envelopes from the WebSocket server to the simulation controller.

**ActionRequest**: Pydantic model representing the canonical action envelope (`action` string plus `params` dictionary) produced by the parser and consumed by the queue infrastructure.

**ActionType**: Enumeration of supported `<domain>.<action>` identifiers (e.g., `simulation.start`, `agent.create`, `map.export`) used by helpers and processors to avoid identifier drift.

**ActionParser**: Component within `world.sim.actions` responsible for validating raw WebSocket payloads and producing typed `ActionRequest` envelopes.

**ActionRegistry**: Central mapping in `world.sim.actions` that binds canonical action identifiers to their handler functions.

**ActionProcessor**: Execution orchestrator in `world.sim.actions` that resolves handlers from the registry, invokes them with context, and emits error signals when necessary.

**agent.describe**: Canonical action requesting a full serialized snapshot of a specific agent. Emits an `agent.described` signal on success, or an `error` signal if validation fails.

**agent.described**: Canonical signal emitted in response to `agent.describe`, carrying the agent's full serialized state together with the current simulation tick.

**agent.list**: Canonical action requesting aggregated serialized snapshots for every agent, optionally filtered by `agent_kind`. Returns an `agent.listed` signal containing `total`, `agents`, and `tick`.

**agent.listed**: Canonical signal emitted after `agent.list`, bundling all matching agent payloads alongside the current tick for synchronized UI updates.

**Agent**: An autonomous entity within the simulation that perceives its environment and acts according to defined behavioral rules. Agents may represent mobile entities (moving along the Edges), stationary entities (Buildings located at Nodes), or external entities not directly represented on the Map (e.g. a Broker agent coordinating routes). Each agent type possesses its own set of attributes and decision-making logic, allowing for dynamic interactions and emergent behaviors within the simulated Logistics Network.

**Agentic System**: A multi-agent environment operating within the Logistics Network, composed of autonomous Agents that perceive their surroundings, make decisions and act according to predefined or adaptive behavioral rules. The Agentic System governs the interactions between Agents such as Vehicles, Buildings or Brokers and their responses to Events occurring across the Map.

**AgentID**: Unique identifier for agents, implemented as a string type.

**Arterial Road**: A major road within a city that carries significant traffic. In the generator, arterial roads are classified as G (main roads) or Z (collectors) with higher lane counts and speeds than local roads.

**ASGI**: Asynchronous Server Gateway Interface, used by FastAPI and Uvicorn for WebSocket communication.

## B

**Backend**: A server-side system responsible for executing the Agentic Simulation and managing the overall logic of the Logistics Network. The Backend maintains the state of all Agents, processes Events, and produces Actions that describe updates to be reflected in the Frontend. It communicates with the Frontend through a WebSocket connection, continuously sending Signals and receiving Actions that represent user commands or parameter changes.

**Building**: A physical facility located at a Node within the Map. Buildings represent logistic infrastructure such as warehouses, depots or retail outlets. A Building may function as an Agent, actively participating in the simulation (e.g. managing inventory, dispatching vehicles), but it does not have to. Some may serve as passive locations or resources.

## C

**Command**: A message sent from frontend to simulation requesting an action (start, stop, add agent, etc.). *Note: This is the technical implementation term; see "Action" for the user-facing term.*

**CommandQueue**: Legacy name for the `ActionQueue`. Retained only in historical discussions; new code uses the canonical action terminology.

## D

**D (Droga dojazdowa)**: Polish road classification for access roads. Lowest class roads with 1 lane, speeds of 20-40 km/h. May have weight limits. Used for local access.

**Delaunay Triangulation**: Computational geometry algorithm used to create initial connectivity between nodes in cities. Produces triangles where no point is inside the circumcircle of any triangle.

**Delivery Deadline**: The latest tick by which a package must be delivered to its destination site. Packages that exceed this deadline are considered overdue but not expired.

**Delivery Urgency**: Classification of package delivery speed requirements, including STANDARD, EXPRESS, and SAME_DAY levels that affect pricing and handling priority.

## E

**Edge**: A connection between two Nodes in the Map's graph, representing a traversable route (e.g. road). Edges are directed, defining the allowed direction of movement between Nodes. Each edge includes attributes relevant to the simulation of traffic flow – such as distance, capacity and maximum speed – along with any additional parameters necessary to capture route-specific conditions.

**EdgeID**: Unique identifier for edges, implemented as an integer type.

**Edge Progress**: Distance traveled along the current edge in meters. Used by transport agents to track their position as they traverse edges between nodes.

**Element**: An interactive object represented on the Map that can be selected by the user to inspect its details. Elements include all simulation relevant components such as Buildings, Vehicles, and other Agents that influence or participate in the Logistics Network. Each Element contains information describing its current state, parameters and recent Events.

**Event**: An occurrence within the simulation that represent a change of state in the Logistics Network. Events may take place at Nodes, within Buildings, along Edges, or for specific Agents. They capture dynamic phenomena such as vehicle arrivals, loading and unloading operations, traffic delays, equipment failures or decision triggers.

**EventQueue**: Legacy name for the `SignalQueue`. New implementations rely on canonical signal terminology.

## F

**FastAPI**: Modern Python web framework used for the WebSocket server.

**Fleet**: A collection of mobile Agents within the simulation, typically representing vehicles, such as trucks, that move along the Edges of the Map. The Fleet forms the dynamic component of the Logistics Network responsible for executing transport and delivery operations.

**Frontend**: A web-based interface responsible for visualizing and interacting with the simulation. It renders the 3D environment using Three.js and provides and interactive overlay built with React for controls, information panels, and event details. The Frontend communicates with the Backend through a WebSocket connection, sending Actions that can influence the simulation and receiving Signals that describe state changes and events to be displayed.

**FSM**: Finite State Machine, used for modeling agent behavior states.

## G

**G (Droga główna)**: Polish road classification for main roads. Major roads with 2-4 lanes, speeds of 50-70 km/h, no weight limits. Used for arterial roads in major cities.

**Gabriel Graph**: A geometric graph where an edge exists between two points only if no other point lies within the circle having that edge as diameter. Used to filter Delaunay triangulation for more realistic road networks.

**GP (Droga główna ruchu przyspieszonego)**: Polish road classification for main accelerated traffic roads. High-speed roads with 2-4 lanes, speeds of 90-110 km/h, no weight limits. Used for inter-city connections.

**Graph**: Network topology consisting of nodes and edges representing the logistics network. *Note: See "Map" for the user-facing term.*

**Gridness**: Parameter (0-1) controlling street pattern in generated maps. 0 produces organic, curved streets; 1 produces grid-like, orthogonal streets.

## L

**L (Droga lokalna)**: Polish road classification for local roads. Residential roads with 1-2 lanes, speeds of 30-50 km/h. May have weight limits. Used for local traffic within cities.

**LegID**: Unique identifier for transportation legs, implemented as a string type.

**Logistics Network**: The environment in which all simulation activity takes place, representing the interconnected system of transportation routes, facilities and operational entities responsible for the movement of goods. The Logistics Network is composed of Nodes, Edges, and Buildings, forming the structural backbone of the simulation's Map.

## M

**Map**: A data structure representing the complete logistics network modeled as a directed multigraph. The Map serves as the structural foundation of the Logistics Network, defining the spatial relationships and connectivity between all simulation components.

**Max Speed**: A truck's maximum speed capability in kilometers per hour. This is an inherent property of the transport agent that may be limited by road conditions (edge max_speed_kph) during actual movement.

## N

**Node**: A vertex in the Map's graph. Nodes mark where Edges meet. A node can correspond to one or more physical locations – Buildings – such as warehouses, depots etc. Each node carries geographic coordinates.

**NodeID**: Unique identifier for nodes, implemented as an integer type.

**Navigator**: Service providing A* pathfinding for agent navigation through the graph network. Computes optimal time-based routes respecting both edge speed limits and agent capabilities.

## P

**Pydantic**: Python library for data validation and serialization, used for message validation.

## Q

**Queue**: Thread-safe data structure for inter-thread communication. In SPINE the primary queues are `ActionQueue` (commands in) and `SignalQueue` (events out), both backed by Python's `queue.Queue`.

**Expired Package**: A package that has passed its pickup deadline without being picked up by an agent. Expired packages are automatically removed from the simulation and generate failure metrics.

## P

**Package**: A delivery item within the simulation with attributes including origin, destination, size, value, priority, urgency, and tick-based deadlines. Packages progress through lifecycle states from creation to delivery or expiry.

**PackageID**: Unique identifier for packages, implemented as a string type.

**Package Status**: The current state of a package in its lifecycle: WAITING_PICKUP, IN_TRANSIT, DELIVERED, or EXPIRED.

**Pickup Deadline**: The latest tick by which a package must be picked up from its origin site. Packages that exceed this deadline are considered expired and removed from the simulation.

**Poisson Disk Sampling**: Algorithm for generating evenly-spaced random points with minimum distance constraints. Used for realistic node placement in map generation.

**Poisson Process**: A statistical model used for package spawning at sites, simulating natural arrival patterns with configurable activity rates.

**Polish Road Classification**: System of road categories (A, S, GP, G, Z, L, D) based on Polish technical regulations, used to classify roads by function, capacity, and design standards.

**Priority**: Classification of package importance levels (LOW, MEDIUM, HIGH, URGENT) that affect pricing, handling priority, and delivery requirements.

## R

**Route**: Ordered list of NodeIDs representing a planned path through the graph network. Transport agents follow routes computed by the Navigator service to reach their destinations.

## S

**S (Droga ekspresowa)**: Polish road classification for expressways. High-speed roads with 3-5 lanes, speeds of 100-120 km/h, no weight limits. Used for major inter-city connections.

**Signal**: A canonical event envelope sent from the simulation to the frontend in the form `{"signal": "<domain>.<signal>", "data": {...}}`. Signals report state changes (agent updates, tick markers, package lifecycle events) that the frontend renders or stores.

**SignalQueue**: Thread-safe queue that carries `Signal` envelopes from the simulation controller to the WebSocket broadcaster.

**SignalType**: Enumeration capturing the supported `<domain>.<signal>` identifiers (e.g., `tick.start`, `simulation.started`, `package.delivered`) to keep publisher and subscriber code aligned.

**SPINE**: Simulation Processing & INteraction Engine - the main project name.

**Simulation Controller**: Component that manages the simulation loop and processes commands.

**Simulation Runner**: Main entry point that orchestrates all components.

**Site**: A specialized building type representing pickup and delivery locations in the logistics network. Sites generate packages using Poisson processes and track comprehensive statistics about package lifecycle events.

**SiteID**: Unique identifier for sites, implemented as a string type (alias for BuildingID).

**Site Statistics**: Comprehensive metrics tracked by sites including packages generated, picked up, delivered, expired, and associated monetary values for business intelligence and performance analysis.

## T

**Tick**: A single simulation step, representing a unit of time in the simulation.

**Tick Rate**: Number of simulation ticks per second, configurable from 0.1 to 100 Hz.

**Truck**: Autonomous transport agent that navigates through the graph network following A* computed routes. Trucks maintain position state (current node or edge), speed constraints, and continuously move to randomly selected destinations.

## W

**WebSocket**: Real-time bidirectional communication protocol for frontend-simulation communication.

**Weight Limit**: Maximum vehicle weight allowed on a road segment, measured in kilograms. Some local and access roads have weight restrictions (typically 3.5-7.5 tons) to prevent heavy truck traffic.

**World**: Main simulation container that holds agents, graph, and manages the simulation state. *Note: This is the technical implementation term; see "Logistics Network" for the conceptual term.*

## Z

**Z (Droga zbiorcza)**: Polish road classification for collector roads. Medium-capacity roads with 2-4 lanes, speeds of 40-80 km/h, no weight limits. Used for arterial roads in minor cities and ring roads.
