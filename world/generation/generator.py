"""Hierarchical procedural map generation with realistic road networks."""

import math
import random
from dataclasses import dataclass

import numpy as np
from scipy.spatial import Delaunay, cKDTree

from core.buildings.parking import Parking
from core.buildings.site import Site
from core.types import BuildingID, EdgeID, NodeID, SiteID
from world.generation.params import GenerationParams
from world.graph.edge import Edge, Mode, RoadClass
from world.graph.graph import Graph
from world.graph.node import Node


@dataclass
class Center:
    """Represents a city center (major or minor)."""

    x: float
    y: float
    is_major: bool
    radius: float


@dataclass
class CityNode:
    """Node with city membership information."""

    idx: int
    x: float
    y: float
    center_idx: int
    is_rural: bool


class MapGenerator:
    """Hierarchical generator for realistic road network creation."""

    def __init__(self, params: GenerationParams) -> None:
        """Initialize the map generator.

        Args:
            params: Generation parameters (Pydantic model, validates on instantiation)
        """
        self.params = params
        random.seed(params.seed)
        np.random.seed(params.seed)

        # State tracking
        self.centers: list[Center] = []
        self.city_nodes: list[CityNode] = []
        self.rural_nodes: list[tuple[float, float]] = []
        self.edge_count = 0
        self.site_count = 0
        self.sites: list[tuple[NodeID, bool]] = []  # (node_id, is_urban)
        self.parking_count = 0
        self.parkings: list[NodeID] = []

    def _get_speed_for_road_class(self, road_class: RoadClass, lanes: int, is_urban: bool) -> float:
        """Get the appropriate speed limit for a road class.

        Based on Polish road regulations:
        - Autostrada (A): 140 km/h
        - Droga ekspresowa dwujezdniowa (S, dual): 120 km/h
        - Droga ekspresowa jednojezdniowa (S, single): 100 km/h
        - Droga dwujezdniowa (dual carriageway, 2+ lanes each): 100 km/h
        - Pozostałe drogi poza terenem zabudowanym: 90 km/h
        - Teren zabudowany: 50 km/h
        - Strefa zamieszkania: 20 km/h

        Args:
            road_class: The road classification
            lanes: Number of lanes (helps determine dual vs single carriageway)
            is_urban: Whether the road is in a built-up/urban area

        Returns:
            Speed limit in km/h
        """
        if road_class == RoadClass.A:
            # Autostrada (Motorway)
            return 140.0

        elif road_class == RoadClass.S:
            # Droga ekspresowa (Expressway)
            # Dual carriageway (2+ lanes per direction) vs single carriageway
            if lanes >= 2:
                return 120.0  # Dual carriageway
            else:
                return 100.0  # Single carriageway

        elif road_class == RoadClass.GP:
            # Droga główna ruchu przyspieszonego (Main accelerated traffic road)
            # Outside built-up areas
            return 90.0

        elif road_class == RoadClass.G:
            # Droga główna (Main road)
            if is_urban:
                return 50.0  # Built-up area
            else:
                # Outside built-up, dual carriageway with 2+ lanes
                if lanes >= 2:
                    return 100.0
                else:
                    return 90.0

        elif road_class == RoadClass.Z:
            # Droga zbiorcza (Collector road)
            if is_urban:
                return 50.0  # Built-up area
            else:
                return 90.0  # Outside built-up area

        elif road_class == RoadClass.L:
            # Droga lokalna (Local road)
            return 50.0  # Typically in built-up areas

        elif road_class == RoadClass.D:
            # Droga dojazdowa (Access road / Residential zone)
            return 20.0

    def generate(self) -> Graph:
        """Generate a complete hierarchical graph.

        Returns:
            A fully generated Graph instance with hierarchical structure
        """
        # Step 0: Generate centers (major + minor)
        self._generate_centers()

        # Step 1: Populate nodes (urban + rural + settlements)
        self._populate_nodes()

        # Step 2: Create graph and add all nodes
        graph = self._create_graph_with_nodes()

        # Step 3: Intra-city roads
        self._create_intra_city_roads(graph)

        # Step 4: Inter-city highways
        self._create_inter_city_highways(graph)

        # Step 5: Ring roads
        self._create_ring_roads(graph)

        # Step 6: Cleanup and ensure connectivity
        self._cleanup_and_connect(graph)

        # Step 7: Reassign edge IDs to be sequential
        self._reassign_edge_ids(graph)

        # Step 8: Place buildings (sites)
        self._place_buildings(graph)

        return graph

    def _generate_centers(self) -> None:
        """Generate major and minor centers using Poisson disk sampling."""
        # Generate major centers with Poisson disk sampling
        major_centers = self._poisson_disk_sampling(
            width=self.params.map_width,
            height=self.params.map_height,
            min_distance=self.params.center_separation,
            max_attempts=30,
            target_count=self.params.num_major_centers,
        )

        # Add major centers
        for x, y in major_centers:
            radius = np.random.normal(self.params.urban_sprawl, 0.3 * self.params.urban_sprawl)
            radius = max(radius, self.params.urban_sprawl * 0.5)  # Minimum radius
            self.centers.append(Center(x=x, y=y, is_major=True, radius=radius))

        # Generate minor centers around each major center
        for major_center in [c for c in self.centers if c.is_major]:
            num_minors = int(np.random.poisson(self.params.minor_per_major))

            for _ in range(num_minors):
                # Place minor centers in a ring around major center
                angle = random.uniform(0, 2 * math.pi)
                distance = np.random.normal(major_center.radius * 2.5, major_center.radius * 0.5)
                distance = max(distance, major_center.radius * 1.5)

                x = major_center.x + distance * math.cos(angle)
                y = major_center.y + distance * math.sin(angle)

                # Check bounds
                if 0 <= x < self.params.map_width and 0 <= y < self.params.map_height:
                    radius = np.random.normal(
                        self.params.urban_sprawl * 0.4, self.params.urban_sprawl * 0.1
                    )
                    radius = max(radius, self.params.urban_sprawl * 0.2)
                    self.centers.append(Center(x=x, y=y, is_major=False, radius=radius))

    def _populate_nodes(self) -> None:
        """Populate nodes in urban areas, rural areas, and settlements."""
        # Generate nodes for each center
        for center_idx, center in enumerate(self.centers):
            city_nodes = self._generate_city_nodes(center, center_idx)
            self.city_nodes.extend(city_nodes)

        # Generate rural nodes
        if self.params.rural_density > 0:
            self._generate_rural_nodes()

        # Generate rural settlements
        if self.params.rural_settlement_prob > 0:
            self._generate_rural_settlements()

    def _generate_city_nodes(self, center: Center, center_idx: int) -> list[CityNode]:
        """Generate nodes within a city using radial Poisson disk sampling."""
        # Calculate spacing from density (nodes per km²)
        area_km2 = math.pi * (center.radius / 1000.0) ** 2
        target_nodes = int(area_km2 * self.params.local_density)
        target_nodes = max(target_nodes, 5)  # Minimum nodes per city

        # Calculate minimum spacing
        min_spacing = center.radius / math.sqrt(target_nodes) * 0.8

        # Generate positions within circle
        positions = self._poisson_disk_in_circle(
            cx=center.x,
            cy=center.y,
            radius=center.radius,
            min_distance=min_spacing,
            max_attempts=30,
        )

        # Apply gridness
        if self.params.gridness > 0:
            positions = self._apply_gridness(positions, center.x, center.y)

        # Create CityNode objects
        city_nodes: list[CityNode] = []
        for x, y in positions:
            node = CityNode(
                idx=len(self.city_nodes) + len(city_nodes),
                x=x,
                y=y,
                center_idx=center_idx,
                is_rural=False,
            )
            city_nodes.append(node)

        return city_nodes

    def _generate_rural_nodes(self) -> None:
        """Generate sparse rural waypoint nodes."""
        # Calculate rural area (total - urban areas)
        urban_area_km2 = sum(math.pi * (c.radius / 1000.0) ** 2 for c in self.centers)
        total_area_km2 = (self.params.map_width * self.params.map_height) / 1_000_000
        rural_area_km2 = max(0, total_area_km2 - urban_area_km2)

        target_rural = int(rural_area_km2 * self.params.rural_density)

        if target_rural == 0:
            return

        # Calculate spacing
        min_spacing = (
            math.sqrt((self.params.map_width * self.params.map_height) / target_rural) * 0.8
        )

        # Generate rural nodes avoiding urban areas
        attempts = 0
        max_attempts = target_rural * 100

        while len(self.rural_nodes) < target_rural and attempts < max_attempts:
            attempts += 1
            x = random.uniform(0, self.params.map_width)
            y = random.uniform(0, self.params.map_height)

            # Check if in urban area
            if self._is_in_urban_area(x, y):
                continue

            # Check minimum distance from other rural nodes
            if self._is_too_close_to_rural(x, y, min_spacing):
                continue

            self.rural_nodes.append((x, y))

    def _generate_rural_settlements(self) -> None:
        """Generate small rural settlements probabilistically."""
        # For each rural node, probabilistically create a small settlement
        settlements_to_add: list[CityNode] = []

        for rural_x, rural_y in self.rural_nodes:
            if random.random() < self.params.rural_settlement_prob:
                # Create a small cluster around this rural node
                settlement_radius = self.params.urban_sprawl * 0.15
                num_settlement_nodes = random.randint(3, 8)
                min_spacing = settlement_radius / math.sqrt(num_settlement_nodes)

                positions = self._poisson_disk_in_circle(
                    cx=rural_x,
                    cy=rural_y,
                    radius=settlement_radius,
                    min_distance=min_spacing,
                    max_attempts=20,
                )

                # Add as city nodes with a special center index
                settlement_center_idx = len(self.centers)
                for x, y in positions[:num_settlement_nodes]:
                    node = CityNode(
                        idx=len(self.city_nodes) + len(settlements_to_add),
                        x=x,
                        y=y,
                        center_idx=settlement_center_idx,
                        is_rural=False,
                    )
                    settlements_to_add.append(node)

        self.city_nodes.extend(settlements_to_add)

    def _create_graph_with_nodes(self) -> Graph:
        """Create graph and add all nodes."""
        graph = Graph()

        # Add city nodes
        for city_node in self.city_nodes:
            node = Node(id=NodeID(city_node.idx), x=city_node.x, y=city_node.y)
            graph.add_node(node)

        # Add rural nodes
        base_idx = len(self.city_nodes)
        for i, (x, y) in enumerate(self.rural_nodes):
            node = Node(id=NodeID(base_idx + i), x=x, y=y)
            graph.add_node(node)

        return graph

    def _create_intra_city_roads(self, graph: Graph) -> None:
        """Create roads within each city using Delaunay → Gabriel/RNG → MST."""
        # Group nodes by center
        nodes_by_center: dict[int, list[CityNode]] = {}
        for city_node in self.city_nodes:
            if city_node.center_idx not in nodes_by_center:
                nodes_by_center[city_node.center_idx] = []
            nodes_by_center[city_node.center_idx].append(city_node)

        # Process each city
        for center_idx, nodes in nodes_by_center.items():
            if len(nodes) < 3:
                # Too few nodes for Delaunay, just connect them linearly
                for i in range(len(nodes) - 1):
                    self._add_city_edge(graph, nodes[i], nodes[i + 1], center_idx)
                continue

            # Build Delaunay triangulation
            points = np.array([(n.x, n.y) for n in nodes])
            tri = Delaunay(points)

            # Extract edges from triangulation
            edge_set: set[tuple[int, int]] = set()
            for simplex in tri.simplices:
                for i in range(3):
                    p1, p2 = simplex[i], simplex[(i + 1) % 3]
                    edge_key = (min(p1, p2), max(p1, p2))
                    edge_set.add(edge_key)

            # Convert to Gabriel graph (remove long edges)
            gabriel_edges = self._to_gabriel_graph(points, edge_set)

            # Build MST for connectivity
            mst_edges = self._compute_mst(points, gabriel_edges)

            # Add additional edges up to intra_connectivity
            target_edge_count = int(len(mst_edges) * (1 + self.params.intra_connectivity))
            remaining_edges = gabriel_edges - mst_edges
            sorted_remaining = sorted(
                remaining_edges,
                key=lambda e: np.linalg.norm(points[e[0]] - points[e[1]]),
            )

            final_edges = mst_edges.copy()
            for edge in sorted_remaining:
                if len(final_edges) >= target_edge_count:
                    break
                final_edges.add(edge)

            # Classify edges as arterial or local
            arterial_edges = self._select_arterial_edges(
                points, final_edges, self.params.arterial_ratio
            )

            # Add edges to graph
            for local_i, local_j in final_edges:
                node_i = nodes[local_i]
                node_j = nodes[local_j]
                is_arterial = (local_i, local_j) in arterial_edges or (
                    local_j,
                    local_i,
                ) in arterial_edges

                self._add_city_edge(graph, node_i, node_j, center_idx, is_arterial)

    def _create_inter_city_highways(self, graph: Graph) -> None:
        """Create highways between city centers."""
        if len(self.centers) < 2:
            return

        # Build centroid graph
        centroids = np.array([(c.x, c.y) for c in self.centers])

        # Compute MST on centroids
        mst_edges = self._compute_mst_indices(centroids, list(range(len(self.centers))))

        # Add k-nearest neighbors for redundancy
        tree = cKDTree(centroids)
        k = min(self.params.inter_connectivity + 1, len(self.centers))

        highway_edges: set[tuple[int, int]] = set()
        for i in range(len(self.centers)):
            distances, neighbors = tree.query(centroids[i], k=k)
            for j in neighbors:
                if i != j:
                    edge_key = (min(i, j), max(i, j))
                    highway_edges.add(edge_key)

        # Combine MST with k-nearest
        highway_edges.update(mst_edges)

        # Realize each highway as a path through waypoints
        for center_i, center_j in highway_edges:
            self._add_highway_path(graph, center_i, center_j)

    def _create_ring_roads(self, graph: Graph) -> None:
        """Create ring roads around major centers."""
        for _center_idx, center in enumerate(self.centers):
            if not center.is_major:
                continue

            if random.random() > self.params.ring_road_prob:
                continue

            # Create ring at ~0.7 * radius
            ring_radius = center.radius * 0.7
            num_ring_points = max(8, int(2 * math.pi * ring_radius / 200))  # ~200m spacing

            ring_nodes = []
            for i in range(num_ring_points):
                angle = (2 * math.pi * i) / num_ring_points
                x = center.x + ring_radius * math.cos(angle)
                y = center.y + ring_radius * math.sin(angle)

                # Check bounds
                if not (0 <= x < self.params.map_width and 0 <= y < self.params.map_height):
                    continue

                # Create node
                node_id = NodeID(len(graph.nodes))
                node = Node(id=node_id, x=x, y=y)
                graph.add_node(node)
                ring_nodes.append(node_id)

            # Connect ring nodes
            for i in range(len(ring_nodes)):
                from_node = ring_nodes[i]
                to_node = ring_nodes[(i + 1) % len(ring_nodes)]

                from_pos = (graph.nodes[from_node].x, graph.nodes[from_node].y)
                to_pos = (graph.nodes[to_node].x, graph.nodes[to_node].y)
                distance = math.hypot(to_pos[0] - from_pos[0], to_pos[1] - from_pos[1])

                # Ring roads are collectors (class Z) outside built-up area
                road_class = RoadClass.Z
                lanes = random.randint(2, 4)
                speed = self._get_speed_for_road_class(road_class, lanes, is_urban=False)

                # Bidirectional
                edge1 = Edge(
                    id=EdgeID(self.edge_count),
                    from_node=from_node,
                    to_node=to_node,
                    length_m=distance,
                    mode=Mode.ROAD,
                    road_class=road_class,
                    lanes=lanes,
                    max_speed_kph=speed,
                    weight_limit_kg=None,
                )
                graph.add_edge(edge1)
                self.edge_count += 1

                edge2 = Edge(
                    id=EdgeID(self.edge_count),
                    from_node=to_node,
                    to_node=from_node,
                    length_m=distance,
                    mode=Mode.ROAD,
                    road_class=road_class,
                    lanes=lanes,
                    max_speed_kph=speed,
                    weight_limit_kg=None,
                )
                graph.add_edge(edge2)
                self.edge_count += 1

    def _cleanup_and_connect(self, graph: Graph) -> None:
        """Prune long edges, remove dead ends, ensure connectivity."""
        # Remove very long edges (outliers)
        edges_to_remove = []
        edge_lengths = [e.length_m for e in graph.edges.values()]
        if edge_lengths:
            mean_length = np.mean(edge_lengths)
            std_length = np.std(edge_lengths)
            threshold = mean_length + 3 * std_length

            for edge_id, edge in graph.edges.items():
                if edge.length_m > threshold:
                    edges_to_remove.append(edge_id)

            for edge_id in edges_to_remove:
                graph.remove_edge(edge_id)

        # Remove short dead-ends (degree-1 nodes with short edges)
        dead_end_threshold = 50.0  # meters
        removed_any = True
        while removed_any:
            removed_any = False
            for node_id in list(graph.nodes.keys()):
                if node_id not in graph.nodes:
                    continue

                out_edges = graph.get_outgoing_edges(node_id)
                in_edges = graph.get_incoming_edges(node_id)

                if len(out_edges) + len(in_edges) == 1:
                    # Degree-1 node
                    edge = out_edges[0] if out_edges else in_edges[0]
                    if edge.length_m < dead_end_threshold:
                        graph.remove_node(node_id)
                        removed_any = True

        # Ensure connectivity
        if not graph.is_connected():
            self._ensure_connectivity(graph)

    def _ensure_connectivity(self, graph: Graph) -> None:
        """Connect disconnected components with shortest feasible edges."""
        # Find all connected components
        components = self._find_components(graph)

        if len(components) <= 1:
            return

        # Connect components pairwise
        while len(components) > 1:
            # Find closest pair of components
            best_distance = float("inf")
            best_pair = (0, 0)
            best_nodes = (NodeID(0), NodeID(0))

            for i in range(len(components)):
                for j in range(i + 1, len(components)):
                    for node_i in components[i]:
                        for node_j in components[j]:
                            pos_i = (graph.nodes[node_i].x, graph.nodes[node_i].y)
                            pos_j = (graph.nodes[node_j].x, graph.nodes[node_j].y)
                            dist = math.hypot(pos_j[0] - pos_i[0], pos_j[1] - pos_i[1])

                            if dist < best_distance:
                                best_distance = dist
                                best_pair = (i, j)
                                best_nodes = (node_i, node_j)

            # Connect the closest pair
            node_i, node_j = best_nodes
            pos_i = (graph.nodes[node_i].x, graph.nodes[node_i].y)
            pos_j = (graph.nodes[node_j].x, graph.nodes[node_j].y)
            distance = math.hypot(pos_j[0] - pos_i[0], pos_j[1] - pos_i[1])

            # Add bidirectional connection (main road)
            road_class = RoadClass.G
            lanes = 2
            speed = self._get_speed_for_road_class(road_class, lanes, is_urban=False)

            edge1 = Edge(
                id=EdgeID(self.edge_count),
                from_node=node_i,
                to_node=node_j,
                length_m=distance,
                mode=Mode.ROAD,
                road_class=road_class,
                lanes=lanes,
                max_speed_kph=speed,
                weight_limit_kg=None,
            )
            graph.add_edge(edge1)
            self.edge_count += 1

            edge2 = Edge(
                id=EdgeID(self.edge_count),
                from_node=node_j,
                to_node=node_i,
                length_m=distance,
                mode=Mode.ROAD,
                road_class=road_class,
                lanes=lanes,
                max_speed_kph=speed,
                weight_limit_kg=None,
            )
            graph.add_edge(edge2)
            self.edge_count += 1

            # Merge components
            components[best_pair[0]].update(components[best_pair[1]])
            components.pop(best_pair[1])

    # Helper methods

    def _poisson_disk_sampling(
        self,
        width: float,
        height: float,
        min_distance: float,
        max_attempts: int,
        target_count: int | None = None,
    ) -> list[tuple[float, float]]:
        """Poisson disk sampling in a rectangle."""
        positions: list[tuple[float, float]] = []
        active_list: list[tuple[float, float]] = []

        # Initial point
        first_x = random.uniform(0, width)
        first_y = random.uniform(0, height)
        positions.append((first_x, first_y))
        active_list.append((first_x, first_y))

        # Grid for acceleration
        cell_size = min_distance / math.sqrt(2)
        cols = int(width / cell_size) + 1
        rows = int(height / cell_size) + 1
        grid: list[list[int | None]] = [[None for _ in range(cols)] for _ in range(rows)]

        def get_cell(x: float, y: float) -> tuple[int, int]:
            return (int(x / cell_size), int(y / cell_size))

        def is_valid(x: float, y: float) -> bool:
            if not (0 <= x < width and 0 <= y < height):
                return False

            cell_x, cell_y = get_cell(x, y)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = cell_x + dx, cell_y + dy
                    if 0 <= nx < cols and 0 <= ny < rows:
                        idx = grid[ny][nx]
                        if idx is not None:
                            pos = positions[idx]
                            if math.hypot(x - pos[0], y - pos[1]) < min_distance:
                                return False
            return True

        # Mark initial point in grid
        cx, cy = get_cell(first_x, first_y)
        grid[cy][cx] = 0

        # Generate points
        attempts = 0
        max_total_attempts = 10000

        while active_list and attempts < max_total_attempts:
            if target_count and len(positions) >= target_count:
                break

            attempts += 1
            seed_idx = random.randint(0, len(active_list) - 1)
            seed = active_list[seed_idx]

            found = False
            for _ in range(max_attempts):
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(min_distance, 2 * min_distance)

                x = seed[0] + radius * math.cos(angle)
                y = seed[1] + radius * math.sin(angle)

                if is_valid(x, y):
                    positions.append((x, y))
                    cx, cy = get_cell(x, y)
                    grid[cy][cx] = len(positions) - 1
                    active_list.append((x, y))
                    found = True
                    break

            if not found:
                active_list.pop(seed_idx)

        return positions

    def _poisson_disk_in_circle(
        self,
        cx: float,
        cy: float,
        radius: float,
        min_distance: float,
        max_attempts: int,
    ) -> list[tuple[float, float]]:
        """Poisson disk sampling within a circle."""
        positions: list[tuple[float, float]] = []
        active_list: list[tuple[float, float]] = []

        # Initial point at center
        positions.append((cx, cy))
        active_list.append((cx, cy))

        def is_in_circle(x: float, y: float) -> bool:
            return math.hypot(x - cx, y - cy) <= radius

        def is_valid(x: float, y: float) -> bool:
            # Check map bounds
            if not (0 <= x < self.params.map_width and 0 <= y < self.params.map_height):
                return False

            if not is_in_circle(x, y):
                return False

            return all(math.hypot(x - pos[0], y - pos[1]) >= min_distance for pos in positions)

        attempts = 0
        max_total_attempts = 5000

        while active_list and attempts < max_total_attempts:
            attempts += 1
            seed_idx = random.randint(0, len(active_list) - 1)
            seed = active_list[seed_idx]

            found = False
            for _ in range(max_attempts):
                angle = random.uniform(0, 2 * math.pi)
                r = random.uniform(min_distance, 2 * min_distance)

                x = seed[0] + r * math.cos(angle)
                y = seed[1] + r * math.sin(angle)

                if is_valid(x, y):
                    positions.append((x, y))
                    active_list.append((x, y))
                    found = True
                    break

            if not found:
                active_list.pop(seed_idx)

        return positions

    def _apply_gridness(
        self, positions: list[tuple[float, float]], cx: float, cy: float
    ) -> list[tuple[float, float]]:
        """Apply gridness to positions by snapping angles."""
        result = []
        for x, y in positions:
            dx = x - cx
            dy = y - cy

            if dx == 0 and dy == 0:
                result.append((x, y))
                continue

            # Current angle
            angle = math.atan2(dy, dx)

            # Snap to nearest 45-degree increment with probability = gridness
            if random.random() < self.params.gridness:
                snap_angle = round(angle / (math.pi / 4)) * (math.pi / 4)
                distance = math.hypot(dx, dy)
                new_x = cx + distance * math.cos(snap_angle)
                new_y = cy + distance * math.sin(snap_angle)

                # Clamp to map bounds
                new_x = max(0, min(new_x, self.params.map_width))
                new_y = max(0, min(new_y, self.params.map_height))
                result.append((new_x, new_y))
            else:
                result.append((x, y))

        return result

    def _is_in_urban_area(self, x: float, y: float) -> bool:
        """Check if point is within any urban area."""
        for center in self.centers:
            dist = math.hypot(x - center.x, y - center.y)
            if dist <= center.radius:
                return True
        return False

    def _is_too_close_to_rural(self, x: float, y: float, min_spacing: float) -> bool:
        """Check if point is too close to existing rural nodes."""
        return any(math.hypot(x - rx, y - ry) < min_spacing for rx, ry in self.rural_nodes)

    def _to_gabriel_graph(
        self, points: np.ndarray, edges: set[tuple[int, int]]
    ) -> set[tuple[int, int]]:
        """Convert edge set to Gabriel graph (remove edges with closer points in circle)."""
        gabriel_edges = set()

        for i, j in edges:
            p1 = points[i]
            p2 = points[j]
            midpoint = (p1 + p2) / 2
            radius = np.linalg.norm(p1 - p2) / 2

            # Check if any other point is inside the circle
            is_gabriel = True
            for k in range(len(points)):
                if k in (i, j):
                    continue
                if np.linalg.norm(points[k] - midpoint) < radius:
                    is_gabriel = False
                    break

            if is_gabriel:
                gabriel_edges.add((i, j))

        return gabriel_edges

    def _compute_mst(self, points: np.ndarray, edges: set[tuple[int, int]]) -> set[tuple[int, int]]:
        """Compute minimum spanning tree using Kruskal's algorithm."""
        # Sort edges by length
        sorted_edges = sorted(edges, key=lambda e: np.linalg.norm(points[e[0]] - points[e[1]]))

        # Union-find
        parent = list(range(len(points)))

        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: int, y: int) -> bool:
            px, py = find(x), find(y)
            if px == py:
                return False
            parent[px] = py
            return True

        mst_edges = set()
        for i, j in sorted_edges:
            if union(i, j):
                mst_edges.add((i, j))

        return mst_edges

    def _compute_mst_indices(self, points: np.ndarray, indices: list[int]) -> set[tuple[int, int]]:
        """Compute MST on a subset of points."""
        if len(indices) < 2:
            return set()

        # Build all edges
        edges = []
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                dist = np.linalg.norm(points[indices[i]] - points[indices[j]])
                edges.append((dist, indices[i], indices[j]))

        edges.sort()

        # Union-find
        parent = {idx: idx for idx in indices}

        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: int, y: int) -> bool:
            px, py = find(x), find(y)
            if px == py:
                return False
            parent[px] = py
            return True

        mst_edges = set()
        for _, i, j in edges:
            if union(i, j):
                mst_edges.add((min(i, j), max(i, j)))

        return mst_edges

    def _select_arterial_edges(
        self, points: np.ndarray, edges: set[tuple[int, int]], ratio: float
    ) -> set[tuple[int, int]]:
        """Select arterial edges (longest edges up to ratio)."""
        sorted_edges = sorted(
            edges, key=lambda e: np.linalg.norm(points[e[0]] - points[e[1]]), reverse=True
        )

        num_arterials = int(len(edges) * ratio)
        return set(sorted_edges[:num_arterials])

    def _add_city_edge(
        self,
        graph: Graph,
        node_i: CityNode,
        node_j: CityNode,
        center_idx: int,
        is_arterial: bool = False,
    ) -> None:
        """Add a bidirectional or unidirectional city edge with classification."""
        from_node = NodeID(node_i.idx)
        to_node = NodeID(node_j.idx)

        distance = math.hypot(node_j.x - node_i.x, node_j.y - node_i.y)

        # Determine road class
        if is_arterial:
            if center_idx < len(self.centers) and self.centers[center_idx].is_major:
                road_class = RoadClass.G  # Main road in major city
                lanes = random.randint(2, 4)
            else:
                road_class = RoadClass.Z  # Collector in minor city
                lanes = random.randint(2, 3)
            weight_limit = None
        else:
            # Local or access road
            if random.random() < 0.5:
                road_class = RoadClass.L
                lanes = random.randint(1, 2)
            else:
                road_class = RoadClass.D
                lanes = 1

            # Probabilistic weight limit for small roads
            weight_limit = random.uniform(3500, 7500) if random.random() < 0.3 else None

        # Get appropriate speed for road class (all city roads are in urban areas)
        speed = self._get_speed_for_road_class(road_class, lanes, is_urban=True)

        # 95% bidirectional, 5% one-way in cities
        is_bidirectional = random.random() < 0.95

        edge1 = Edge(
            id=EdgeID(self.edge_count),
            from_node=from_node,
            to_node=to_node,
            length_m=distance,
            mode=Mode.ROAD,
            road_class=road_class,
            lanes=lanes,
            max_speed_kph=speed,
            weight_limit_kg=weight_limit,
        )
        graph.add_edge(edge1)
        self.edge_count += 1

        if is_bidirectional:
            edge2 = Edge(
                id=EdgeID(self.edge_count),
                from_node=to_node,
                to_node=from_node,
                length_m=distance,
                mode=Mode.ROAD,
                road_class=road_class,
                lanes=lanes,
                max_speed_kph=speed,
                weight_limit_kg=weight_limit,
            )
            graph.add_edge(edge2)
            self.edge_count += 1

    def _add_highway_path(self, graph: Graph, center_i: int, center_j: int) -> None:
        """Add highway path between two centers through rural waypoints."""
        c1 = self.centers[center_i]
        c2 = self.centers[center_j]

        # Determine highway class based on distance and importance
        distance = math.hypot(c2.x - c1.x, c2.y - c1.y)

        if c1.is_major and c2.is_major and distance > 5000:
            road_class = RoadClass.A  # Motorway
            lanes = random.randint(4, 6)
        elif (c1.is_major or c2.is_major) and distance > 3000:
            road_class = RoadClass.S  # Expressway
            lanes = random.randint(3, 5)
        else:
            road_class = RoadClass.GP  # Main accelerated road
            lanes = random.randint(2, 4)

        # Get appropriate speed for road class (highways are outside urban areas)
        speed = self._get_speed_for_road_class(road_class, lanes, is_urban=False)

        # Find nodes near centers to connect
        city_nodes_i = [n for n in self.city_nodes if n.center_idx == center_i]
        city_nodes_j = [n for n in self.city_nodes if n.center_idx == center_j]

        if not city_nodes_i or not city_nodes_j:
            return

        # Pick nodes closest to the other center
        node_i = min(city_nodes_i, key=lambda n: math.hypot(n.x - c2.x, n.y - c2.y))
        node_j = min(city_nodes_j, key=lambda n: math.hypot(n.x - c1.x, n.y - c1.y))

        # Simple direct connection (can be enhanced with waypoint routing)
        from_node = NodeID(node_i.idx)
        to_node = NodeID(node_j.idx)
        dist = math.hypot(node_j.x - node_i.x, node_j.y - node_i.y)

        # Highways are always bidirectional and have no weight limits
        edge1 = Edge(
            id=EdgeID(self.edge_count),
            from_node=from_node,
            to_node=to_node,
            length_m=dist,
            mode=Mode.ROAD,
            road_class=road_class,
            lanes=lanes,
            max_speed_kph=speed,
            weight_limit_kg=None,
        )
        graph.add_edge(edge1)
        self.edge_count += 1

        edge2 = Edge(
            id=EdgeID(self.edge_count),
            from_node=to_node,
            to_node=from_node,
            length_m=dist,
            mode=Mode.ROAD,
            road_class=road_class,
            lanes=lanes,
            max_speed_kph=speed,
            weight_limit_kg=None,
        )
        graph.add_edge(edge2)
        self.edge_count += 1

    def _find_components(self, graph: Graph) -> list[set[NodeID]]:
        """Find all connected components in the graph."""
        visited: set[NodeID] = set()
        components: list[set[NodeID]] = []

        for node_id in graph.nodes:
            if node_id in visited:
                continue

            # BFS to find component
            component: set[NodeID] = set()
            queue = [node_id]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue

                visited.add(current)
                component.add(current)

                # Add neighbors
                for neighbor in graph.get_neighbors(current):
                    if neighbor not in visited:
                        queue.append(neighbor)

            components.append(component)

        return components

    def _reassign_edge_ids(self, graph: Graph) -> None:
        """Reassign edge IDs to be sequential after cleanup."""
        # Get all edges sorted by current ID
        edges_list = sorted(graph.edges.items(), key=lambda x: x[0])

        # Remove all edges temporarily
        for edge_id in list(graph.edges.keys()):
            edge = graph.edges[edge_id]
            # Remove from adjacency lists
            if edge_id in graph.out_adj[edge.from_node]:
                graph.out_adj[edge.from_node].remove(edge_id)
            if edge_id in graph.in_adj[edge.to_node]:
                graph.in_adj[edge.to_node].remove(edge_id)
            del graph.edges[edge_id]

        # Re-add edges with sequential IDs
        for new_id, (_, edge) in enumerate(edges_list):
            new_edge = Edge(
                id=EdgeID(new_id),
                from_node=edge.from_node,
                to_node=edge.to_node,
                length_m=edge.length_m,
                mode=edge.mode,
                road_class=edge.road_class,
                lanes=edge.lanes,
                max_speed_kph=edge.max_speed_kph,
                weight_limit_kg=edge.weight_limit_kg,
            )
            graph.edges[EdgeID(new_id)] = new_edge
            graph.out_adj[edge.from_node].append(EdgeID(new_id))
            graph.in_adj[edge.to_node].append(EdgeID(new_id))

    def _select_site_nodes(self, graph: Graph, is_urban: bool) -> list[NodeID]:
        """Select valid nodes for site placement.

        Args:
            graph: The graph to select nodes from
            is_urban: If True, select urban nodes; if False, select rural nodes

        Returns:
            List of valid node IDs for site placement
        """
        valid_nodes: list[NodeID] = []

        for node_id in graph.nodes:
            # Get all edges connected to this node
            outgoing = graph.get_outgoing_edges(node_id)
            incoming = graph.get_incoming_edges(node_id)
            all_edges = outgoing + incoming

            if not all_edges:
                # Isolated node, skip
                continue

            # Check if node connects only to highways (A) or expressways (S)
            non_highway_edges = [
                e for e in all_edges if e.road_class not in (RoadClass.A, RoadClass.S)
            ]

            if not non_highway_edges:
                # Node only connects to highways/expressways, skip
                continue

            # Check if node is in urban area
            node = graph.nodes[node_id]
            node_is_urban = self._is_in_urban_area(node.x, node.y)

            if is_urban and node_is_urban or not is_urban and not node_is_urban:
                valid_nodes.append(node_id)

        return valid_nodes

    def _create_site(self, node_id: NodeID, is_urban: bool) -> Site:
        """Create a Site instance with appropriate configuration.

        Args:
            node_id: The node where the site will be placed
            is_urban: Whether this is an urban or rural site

        Returns:
            A new Site instance
        """

        node_suffix = int(node_id)
        site_identifier = f"node{node_suffix}_site_{self.site_count}"
        site_id = SiteID(site_identifier)
        self.site_count += 1

        # Determine activity rate based on urban/rural
        if is_urban:
            min_rate, max_rate = self.params.urban_activity_rate_range
            # Add a baseline boost for urban sites
            baseline = max_rate * 0.3
            activity_rate = baseline + random.uniform(min_rate, max_rate)
        else:
            min_rate, max_rate = self.params.rural_activity_rate_range
            # Rural sites can occasionally be very active
            if random.random() < 0.1:  # 10% chance of high activity rural site
                activity_rate = random.uniform(max_rate * 0.8, max_rate * 1.5)
            else:
                activity_rate = random.uniform(min_rate, max_rate)

        site = Site(
            id=BuildingID(site_id),
            name=f"Site {node_suffix}",
            activity_rate=activity_rate,
        )

        return site

    def _place_buildings(self, graph: Graph) -> None:
        """Place Site buildings on the graph nodes.

        Args:
            graph: The graph to place buildings on
        """

        # Calculate urban area
        urban_area_km2 = sum(math.pi * (c.radius / 1000.0) ** 2 for c in self.centers)

        # Calculate rural area
        total_area_km2 = (self.params.map_width * self.params.map_height) / 1_000_000
        rural_area_km2 = max(0, total_area_km2 - urban_area_km2)

        # Calculate target number of sites
        target_urban_sites = int(urban_area_km2 * self.params.urban_sites_per_km2)
        target_rural_sites = int(rural_area_km2 * self.params.rural_sites_per_km2)

        # Get valid nodes for urban and rural sites
        urban_nodes = self._select_site_nodes(graph, is_urban=True)
        rural_nodes = self._select_site_nodes(graph, is_urban=False)

        # Place urban sites
        if urban_nodes and target_urban_sites > 0:
            # Randomly select nodes for urban sites
            num_urban = min(target_urban_sites, len(urban_nodes))
            selected_urban = random.sample(urban_nodes, num_urban)

            for node_id in selected_urban:
                site = self._create_site(node_id, is_urban=True)
                graph.nodes[node_id].add_building(site)
                self.sites.append((node_id, True))

        # Place rural sites
        if rural_nodes and target_rural_sites > 0:
            # Randomly select nodes for rural sites
            num_rural = min(target_rural_sites, len(rural_nodes))
            selected_rural = random.sample(rural_nodes, num_rural)

            for node_id in selected_rural:
                site = self._create_site(node_id, is_urban=False)
                graph.nodes[node_id].add_building(site)
                self.sites.append((node_id, False))

        # Place parking facilities
        self._place_parking(graph)

        # Assign destination weights
        self._assign_destination_weights(graph)

    def _assign_destination_weights(self, graph: Graph) -> None:
        """Assign destination weights to all sites based on location and city importance.

        Args:
            graph: The graph containing the sites
        """

        # Collect all sites with their properties
        all_sites: list[tuple[SiteID, NodeID, bool]] = []  # (site_id, node_id, is_urban)

        for node_id, is_urban in self.sites:
            node = graph.nodes[node_id]
            for building in node.buildings:
                if isinstance(building, Site):
                    all_sites.append((SiteID(building.id), node_id, is_urban))

        if len(all_sites) < 2:
            # Not enough sites for destination weights
            return

        # For each site, calculate weights to other sites
        for site_id, node_id, is_urban in all_sites:
            node = graph.nodes[node_id]
            site: Site | None = None
            for building in node.buildings:
                if isinstance(building, Site) and str(building.id) == str(site_id):
                    site = building
                    break

            if site is None:
                continue

            weights: dict[SiteID, float] = {}

            for target_site_id, target_node_id, target_is_urban in all_sites:
                if target_site_id == site_id:
                    # Don't assign weight to self
                    continue

                # Determine base weight based on source and target type
                if is_urban:
                    # Urban site
                    if target_is_urban:
                        # Urban -> Urban: moderate weight, influenced by city importance
                        # Try to find which center this belongs to
                        city_importance = 1.0
                        for city_node in self.city_nodes:
                            if city_node.idx == target_node_id and city_node.center_idx < len(
                                self.centers
                            ):
                                if self.centers[city_node.center_idx].is_major:
                                    city_importance = 2.0
                                break
                        base_weight = random.uniform(0.8, 1.5) * city_importance
                    else:
                        # Urban -> Rural: small weight
                        base_weight = random.uniform(0.1, 0.3)
                else:
                    # Rural site
                    if target_is_urban:
                        # Rural -> Urban: high weight (70-80% of total)
                        # Higher weight for major cities
                        city_importance = 1.0
                        for city_node in self.city_nodes:
                            if city_node.idx == target_node_id and city_node.center_idx < len(
                                self.centers
                            ):
                                if self.centers[city_node.center_idx].is_major:
                                    city_importance = 2.5
                                else:
                                    city_importance = 1.5
                                break
                        base_weight = random.uniform(2.0, 4.0) * city_importance
                    else:
                        # Rural -> Rural: low weight (10-20% of total)
                        base_weight = random.uniform(0.2, 0.5)

                weights[target_site_id] = base_weight

            # Normalize weights
            total_weight = sum(weights.values())
            if total_weight > 0:
                site.destination_weights = {
                    dest_id: weight / total_weight for dest_id, weight in weights.items()
                }

    def _place_parking(self, graph: Graph) -> None:
        """Create parking buildings based on connected road classes at each node."""
        for node_id, node in graph.nodes.items():
            road_classes = self._get_node_road_classes(graph, node_id)
            capacity = self._determine_parking_capacity(road_classes, graph, node_id)
            if capacity is None:
                continue

            parking_id = BuildingID(f"parking_{int(node_id)}_{self.parking_count}")
            parking = Parking(id=parking_id, capacity=capacity)
            node.add_building(parking)
            self.parking_count += 1
            self.parkings.append(node_id)

    def _get_node_road_classes(self, graph: Graph, node_id: NodeID) -> set[RoadClass]:
        """Collect all road classes connected to a node."""
        connected_edges = graph.get_outgoing_edges(node_id) + graph.get_incoming_edges(node_id)
        return {edge.road_class for edge in connected_edges}

    def _determine_parking_capacity(
        self, road_classes: set[RoadClass], graph: Graph, node_id: NodeID
    ) -> int | None:
        """Derive parking capacity based on the road classes connected to a node."""
        connected_edges = graph.get_outgoing_edges(node_id) + graph.get_incoming_edges(node_id)
        if len(connected_edges) < 2:
            # Skip dead-ends and isolated nodes
            return None

        priority_capacity: list[tuple[RoadClass, int]] = [
            (RoadClass.A, 80),
            (RoadClass.S, 60),
            (RoadClass.GP, 40),
            (RoadClass.G, 25),
            (RoadClass.Z, 15),
            (RoadClass.L, 10),
            (RoadClass.D, 6),
        ]

        for road_class, capacity in priority_capacity:
            if road_class in road_classes:
                return capacity

        return None
