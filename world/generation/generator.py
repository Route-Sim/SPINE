"""Procedural map generation module using Poisson disk sampling and Delaunay triangulation."""

import math
import random
from dataclasses import dataclass

import numpy as np
from scipy.spatial import Delaunay

from core.types import EdgeID, NodeID
from world.graph.edge import Edge, Mode
from world.graph.graph import Graph
from world.graph.node import Node


@dataclass
class GenerationParams:
    """Parameters for procedural map generation."""

    width: float
    height: float
    nodes: int  # 0-100 density factor
    density: int  # 0-100 clustering factor
    urban_areas: int  # Number of cities/villages

    def __post_init__(self) -> None:
        """Validate parameters after initialization."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Width and height must be positive")
        if not 0 <= self.nodes <= 100:
            raise ValueError("nodes parameter must be between 0 and 100")
        if not 0 <= self.density <= 100:
            raise ValueError("density parameter must be between 0 and 100")
        if self.urban_areas <= 0:
            raise ValueError("urban_areas must be positive")


class MapGenerator:
    """Generator for procedural map creation using realistic algorithms."""

    def __init__(self, params: GenerationParams) -> None:
        """Initialize the map generator.

        Args:
            params: Generation parameters
        """
        self.params = params
        self._validate_params()

    def _validate_params(self) -> None:
        """Validate generation parameters."""
        self.params.__post_init__()

    def generate(self) -> Graph:
        """Generate a complete graph with nodes and edges.

        Returns:
            A fully generated Graph instance
        """
        # Step 1: Generate node positions using Poisson disk sampling
        node_positions = self._generate_node_positions()

        # Step 2: Cluster nodes into urban areas (cities/villages)
        clusters = self._cluster_nodes(node_positions)

        # Step 3: Create graph with nodes
        graph = self._create_nodes(node_positions)

        # Step 4: Create edges using Delaunay triangulation
        self._create_edges(graph, node_positions, clusters)

        return graph

    def _generate_node_positions(self) -> list[tuple[float, float]]:
        """Generate node positions using Poisson disk sampling.

        Returns:
            List of (x, y) coordinates for nodes
        """
        # Calculate number of nodes based on density parameter
        # Formula: approximately (density/100) * area / min_distance^2
        area = self.params.width * self.params.height

        # Minimum distance scales with density parameter
        # density=0 -> large spacing, density=100 -> tight spacing
        base_distance = min(self.params.width, self.params.height) * 0.05  # 5% of smaller dimension
        min_distance = base_distance * (1.0 - self.params.density / 100.0 * 0.8)

        # Calculate target node count
        if self.params.nodes == 0:
            target_nodes = 10  # Minimum nodes
        elif self.params.nodes == 100:
            target_nodes = int(area / (min_distance * min_distance / 4))  # Tokyo-dense
        else:
            # Interpolate between minimum and maximum
            sparse_count = max(10, int(area / (base_distance * base_distance)))
            dense_count = int(area / (min_distance * min_distance / 4))
            target_nodes = int(
                sparse_count + (self.params.nodes / 100.0) * (dense_count - sparse_count)
            )

        # Poisson disk sampling with Bridson's algorithm
        positions: list[tuple[float, float]] = []
        active_list: list[tuple[float, float]] = []

        # Initial random point
        first_x = random.uniform(0, self.params.width)
        first_y = random.uniform(0, self.params.height)
        positions.append((first_x, first_y))
        active_list.append((first_x, first_y))

        # Grid cell size for acceleration
        cell_size = min_distance / math.sqrt(2)
        cols = int(self.params.width / cell_size) + 1
        rows = int(self.params.height / cell_size) + 1

        # Initialize grid
        grid: list[list[int | None]] = [[None for _ in range(cols)] for _ in range(rows)]

        def get_cell(x: float, y: float) -> tuple[int, int]:
            """Get grid cell indices for a point."""
            return (int(x / cell_size), int(y / cell_size))

        def get_cell_neighbors(cx: int, cy: int) -> list[tuple[int, int]]:
            """Get neighboring grid cells."""
            neighbors = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < cols and 0 <= ny < rows:
                        neighbors.append((nx, ny))
            return neighbors

        def is_valid_point(x: float, y: float) -> bool:
            """Check if a point is valid (far enough from others)."""
            cell_x, cell_y = get_cell(x, y)
            for nx, ny in get_cell_neighbors(cell_x, cell_y):
                idx = grid[ny][nx]
                if idx is not None:
                    pos = positions[idx]
                    dist = math.hypot(x - pos[0], y - pos[1])
                    if dist < min_distance:
                        return False
            return True

        # Generate points
        attempts = 0
        max_attempts = 30

        while active_list and len(positions) < target_nodes and attempts < 10000:
            attempts += 1
            if attempts % 1000 == 0 and len(positions) >= 10:
                # If we can't generate enough points, accept what we have
                break

            # Pick random active point
            seed_idx = random.randint(0, len(active_list) - 1)
            seed = active_list[seed_idx]

            # Try to generate new point near seed
            found = False
            for _ in range(max_attempts):
                # Generate point in annulus around seed
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(min_distance, 2 * min_distance)

                x = seed[0] + radius * math.cos(angle)
                y = seed[1] + radius * math.sin(angle)

                # Check bounds
                if not (0 <= x < self.params.width and 0 <= y < self.params.height):
                    continue

                # Check minimum distance
                if is_valid_point(x, y):
                    positions.append((x, y))
                    cell_x, cell_y = get_cell(x, y)
                    grid[cell_y][cell_x] = len(positions) - 1
                    active_list.append((x, y))
                    found = True
                    break

            # Remove seed if no valid point found
            if not found:
                active_list.pop(seed_idx)

        return positions

    def _cluster_nodes(self, positions: list[tuple[float, float]]) -> list[list[int]]:
        """Cluster nodes into urban areas using K-means.

        Args:
            positions: List of (x, y) node positions

        Returns:
            List of clusters, where each cluster is a list of node indices
        """
        if len(positions) < self.params.urban_areas:
            # Not enough nodes to cluster, return one cluster per node
            return [[i] for i in range(len(positions))]

        # Convert to numpy array for clustering
        points = np.array(positions)

        # Initialize centroids randomly
        np.random.seed(42)  # For reproducibility
        random.seed(42)

        centroids = np.random.uniform(
            low=[0, 0],
            high=[self.params.width, self.params.height],
            size=(self.params.urban_areas, 2),
        )

        # K-means iterations
        max_iterations = 100
        for _ in range(max_iterations):
            # Assign points to nearest centroid
            distances = np.sqrt(((points[:, np.newaxis] - centroids) ** 2).sum(axis=2))
            assignments = np.argmin(distances, axis=1)

            # Update centroids
            new_centroids = np.array(
                [
                    points[assignments == k].mean(axis=0)
                    if np.any(assignments == k)
                    else centroids[k]
                    for k in range(self.params.urban_areas)
                ]
            )

            # Check convergence
            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids

        # Build cluster lists
        clusters: list[list[int]] = [[] for _ in range(self.params.urban_areas)]
        for i, cluster_id in enumerate(assignments):
            clusters[cluster_id].append(i)

        # Filter out empty clusters
        return [c for c in clusters if c]

    def _create_nodes(self, positions: list[tuple[float, float]]) -> Graph:
        """Create graph with nodes.

        Args:
            positions: List of (x, y) node positions

        Returns:
            Graph instance with nodes added
        """
        graph = Graph()
        for i, (x, y) in enumerate(positions):
            node = Node(id=NodeID(i), x=x, y=y)
            graph.add_node(node)
        return graph

    def _create_edges(
        self, graph: Graph, positions: list[tuple[float, float]], clusters: list[list[int]]
    ) -> None:
        """Create edges using Delaunay triangulation.

        Args:
            graph: Graph instance to add edges to
            positions: List of (x, y) node positions
            clusters: List of clusters, each containing node indices
        """
        # Build reverse mapping: node_index -> cluster_id
        node_to_cluster: dict[int, int] = {}
        for cluster_id, cluster in enumerate(clusters):
            for node_idx in cluster:
                node_to_cluster[node_idx] = cluster_id

        # Compute Delaunay triangulation
        points = np.array(positions)
        tri = Delaunay(points)

        # Set up random state for bidirectional decisions
        random.seed(42)

        # Create edges from triangulation
        edge_count = 0
        edge_set: set[tuple[int, int]] = set()  # Track edges to avoid duplicates

        for simplex in tri.simplices:
            # Each simplex has 3 edges
            for i in range(3):
                p1, p2 = simplex[i], simplex[(i + 1) % 3]

                # Ensure consistent ordering to avoid duplicates
                edge_key = (min(p1, p2), max(p1, p2))

                if edge_key in edge_set:
                    continue
                edge_set.add(edge_key)

                # Calculate distance
                pos1 = positions[p1]
                pos2 = positions[p2]
                distance = math.hypot(pos1[0] - pos2[0], pos1[1] - pos2[1])

                # Determine if nodes are in the same cluster
                same_cluster = (
                    p1 in node_to_cluster
                    and p2 in node_to_cluster
                    and node_to_cluster[p1] == node_to_cluster[p2]
                )

                # Create edges based on location
                if same_cluster:
                    # Within cities: 95% bidirectional, 5% one-way
                    if random.random() < 0.95:
                        # Bidirectional
                        edge1 = Edge(
                            id=EdgeID(edge_count),
                            from_node=NodeID(p1),
                            to_node=NodeID(p2),
                            length_m=distance,
                            mode=Mode.ROAD,
                        )
                        graph.add_edge(edge1)
                        edge_count += 1

                        edge2 = Edge(
                            id=EdgeID(edge_count),
                            from_node=NodeID(p2),
                            to_node=NodeID(p1),
                            length_m=distance,
                            mode=Mode.ROAD,
                        )
                        graph.add_edge(edge2)
                        edge_count += 1
                    else:
                        # One-way
                        edge = Edge(
                            id=EdgeID(edge_count),
                            from_node=NodeID(p1),
                            to_node=NodeID(p2),
                            length_m=distance,
                            mode=Mode.ROAD,
                        )
                        graph.add_edge(edge)
                        edge_count += 1
                else:
                    # Between cities (highways): all bidirectional
                    edge1 = Edge(
                        id=EdgeID(edge_count),
                        from_node=NodeID(p1),
                        to_node=NodeID(p2),
                        length_m=distance,
                        mode=Mode.ROAD,
                    )
                    graph.add_edge(edge1)
                    edge_count += 1

                    edge2 = Edge(
                        id=EdgeID(edge_count),
                        from_node=NodeID(p2),
                        to_node=NodeID(p1),
                        length_m=distance,
                        mode=Mode.ROAD,
                    )
                    graph.add_edge(edge2)
                    edge_count += 1
