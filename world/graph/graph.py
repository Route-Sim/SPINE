from core.types import EdgeID, NodeID
from world.graph.edge import Edge
from world.graph.node import Node


class Graph:
    """Graph class that manages nodes and edges for the logistics network."""

    def __init__(self) -> None:
        self.nodes: dict[NodeID, Node] = {}
        self.edges: dict[EdgeID, Edge] = {}
        self.out_adj: dict[NodeID, list[EdgeID]] = {}  # node -> outgoing edges
        self.in_adj: dict[NodeID, list[EdgeID]] = {}  # node -> incoming edges

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        if node.id in self.nodes:
            raise ValueError(f"Node {node.id} already exists")

        self.nodes[node.id] = node
        self.out_adj[node.id] = []
        self.in_adj[node.id] = []

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        if edge.id in self.edges:
            raise ValueError(f"Edge {edge.id} already exists")

        # Validate that both nodes exist
        if edge.from_node not in self.nodes:
            raise ValueError(f"Node {edge.from_node} does not exist")
        if edge.to_node not in self.nodes:
            raise ValueError(f"Node {edge.to_node} does not exist")

        self.edges[edge.id] = edge
        self.out_adj[edge.from_node].append(edge.id)
        self.in_adj[edge.to_node].append(edge.id)

    def remove_node(self, node_id: NodeID) -> None:
        """Remove a node and all its associated edges."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist")

        # Remove all edges connected to this node
        edges_to_remove = []
        for edge_id, edge in self.edges.items():
            if edge.from_node == node_id or edge.to_node == node_id:
                edges_to_remove.append(edge_id)

        for edge_id in edges_to_remove:
            self.remove_edge(edge_id)

        # Remove the node
        del self.nodes[node_id]
        del self.out_adj[node_id]
        del self.in_adj[node_id]

    def remove_edge(self, edge_id: EdgeID) -> None:
        """Remove an edge from the graph."""
        if edge_id not in self.edges:
            raise ValueError(f"Edge {edge_id} does not exist")

        edge = self.edges[edge_id]

        # Remove from adjacency lists
        if edge_id in self.out_adj[edge.from_node]:
            self.out_adj[edge.from_node].remove(edge_id)
        if edge_id in self.in_adj[edge.to_node]:
            self.in_adj[edge.to_node].remove(edge_id)

        del self.edges[edge_id]

    def get_node(self, node_id: NodeID) -> Node | None:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: EdgeID) -> Edge | None:
        """Get an edge by ID."""
        return self.edges.get(edge_id)

    def get_outgoing_edges(self, node_id: NodeID) -> list[Edge]:
        """Get all outgoing edges from a node."""
        edge_ids = self.out_adj.get(node_id, [])
        return [self.edges[edge_id] for edge_id in edge_ids if edge_id in self.edges]

    def get_incoming_edges(self, node_id: NodeID) -> list[Edge]:
        """Get all incoming edges to a node."""
        edge_ids = self.in_adj.get(node_id, [])
        return [self.edges[edge_id] for edge_id in edge_ids if edge_id in self.edges]

    def get_neighbors(self, node_id: NodeID) -> list[NodeID]:
        """Get all neighbor nodes (connected by edges)."""
        neighbors = set()
        for edge in self.get_outgoing_edges(node_id):
            neighbors.add(edge.to_node)
        for edge in self.get_incoming_edges(node_id):
            neighbors.add(edge.from_node)
        return list(neighbors)

    def get_node_count(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self.nodes)

    def get_edge_count(self) -> int:
        """Get the number of edges in the graph."""
        return len(self.edges)

    def is_connected(self) -> bool:
        """Check if the graph is connected (all nodes reachable from any node)."""
        if not self.nodes:
            return True

        # Start DFS from the first node
        start_node = next(iter(self.nodes.keys()))
        visited = set()
        stack = [start_node]

        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)

            # Add all neighbors to stack
            for neighbor in self.get_neighbors(node_id):
                if neighbor not in visited:
                    stack.append(neighbor)

        return len(visited) == len(self.nodes)

    def __str__(self) -> str:
        """String representation of the graph."""
        return f"Graph(nodes={len(self.nodes)}, edges={len(self.edges)})"

    def __repr__(self) -> str:
        """Detailed representation of the graph."""
        return f"Graph(nodes={list(self.nodes.keys())}, edges={list(self.edges.keys())})"
