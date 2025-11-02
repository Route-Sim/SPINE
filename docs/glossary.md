---
title: "Glossary"
summary: "Definitions and abbreviations used throughout the SPINE project."
source_paths: []
last_updated: "2025-11-02"
owner: "Mateusz Polis"
tags: ["glossary"]
links:
  parent: "SUMMARY.md"
  siblings: []
---

# Glossary

## A

**A (Autostrada)**: Polish road classification for motorways. Highest class roads with 4-6 lanes, speeds of 120-140 km/h, and no weight limits. Used for major inter-city connections.

**Action**: A message sent from the Frontend to the Backend through the WebSocket connection to influence the simulation. Actions represent user commands or parameter changes, such as modifying an Agent's behavior, removing an Element, or controlling the simulation state (e.g. play, pause, reset).

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

**CommandQueue**: Thread-safe queue for commands from frontend to simulation.

## D

**D (Droga dojazdowa)**: Polish road classification for access roads. Lowest class roads with 1 lane, speeds of 20-40 km/h. May have weight limits. Used for local access.

**Delaunay Triangulation**: Computational geometry algorithm used to create initial connectivity between nodes in cities. Produces triangles where no point is inside the circumcircle of any triangle.

**Delivery Deadline**: The latest tick by which a package must be delivered to its destination site. Packages that exceed this deadline are considered overdue but not expired.

**Delivery Urgency**: Classification of package delivery speed requirements, including STANDARD, EXPRESS, and SAME_DAY levels that affect pricing and handling priority.

## E

**Edge**: A connection between two Nodes in the Map's graph, representing a traversable route (e.g. road). Edges are directed, defining the allowed direction of movement between Nodes. Each edge includes attributes relevant to the simulation of traffic flow – such as distance, capacity and maximum speed – along with any additional parameters necessary to capture route-specific conditions.

**EdgeID**: Unique identifier for edges, implemented as an integer type.

**Element**: An interactive object represented on the Map that can be selected by the user to inspect its details. Elements include all simulation relevant components such as Buildings, Vehicles, and other Agents that influence or participate in the Logistics Network. Each Element contains information describing its current state, parameters and recent Events.

**Event**: An occurrence within the simulation that represent a change of state in the Logistics Network. Events may take place at Nodes, within Buildings, along Edges, or for specific Agents. They capture dynamic phenomena such as vehicle arrivals, loading and unloading operations, traffic delays, equipment failures or decision triggers.

**EventQueue**: Thread-safe queue for events from simulation to frontend.

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

## N

**Node**: A vertex in the Map's graph. Nodes mark where Edges meet. A node can correspond to one or more physical locations – Buildings – such as warehouses, depots etc. Each node carries geographic coordinates.

**NodeID**: Unique identifier for nodes, implemented as an integer type.

## P

**Pydantic**: Python library for data validation and serialization, used for message validation.

## Q

**Queue**: Thread-safe data structure for inter-thread communication.

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

## S

**S (Droga ekspresowa)**: Polish road classification for expressways. High-speed roads with 3-5 lanes, speeds of 100-120 km/h, no weight limits. Used for major inter-city connections.

**Signal**: A message sent from the Backend to the Frontend describing state changes or events within the simulation. Signals inform the Frontend what has occurred – such as an Agent moving, an Event being triggered, or metrics being updated, so that it can update the 3D visualization accordingly.

**SPINE**: Simulation Processing & INteraction Engine - the main project name.

**Simulation Controller**: Component that manages the simulation loop and processes commands.

**Simulation Runner**: Main entry point that orchestrates all components.

**Site**: A specialized building type representing pickup and delivery locations in the logistics network. Sites generate packages using Poisson processes and track comprehensive statistics about package lifecycle events.

**SiteID**: Unique identifier for sites, implemented as a string type (alias for BuildingID).

**Site Statistics**: Comprehensive metrics tracked by sites including packages generated, picked up, delivered, expired, and associated monetary values for business intelligence and performance analysis.

## T

**Tick**: A single simulation step, representing a unit of time in the simulation.

**Tick Rate**: Number of simulation ticks per second, configurable from 0.1 to 100 Hz.

## W

**WebSocket**: Real-time bidirectional communication protocol for frontend-simulation communication.

**Weight Limit**: Maximum vehicle weight allowed on a road segment, measured in kilograms. Some local and access roads have weight restrictions (typically 3.5-7.5 tons) to prevent heavy truck traffic.

**World**: Main simulation container that holds agents, graph, and manages the simulation state. *Note: This is the technical implementation term; see "Logistics Network" for the conceptual term.*

## Z

**Z (Droga zbiorcza)**: Polish road classification for collector roads. Medium-capacity roads with 2-4 lanes, speeds of 40-80 km/h, no weight limits. Used for arterial roads in minor cities and ring roads.
