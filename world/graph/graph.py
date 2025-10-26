import json
import xml.etree.ElementTree as ET

from core.buildings.base import Building
from core.types import EdgeID, NodeID
from world.graph.edge import Edge, Mode
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

    def to_graphml(self, filepath: str) -> None:
        """Export graph to GraphML format."""
        # Create root element
        root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")

        # Define attributes for nodes
        node_x_key = ET.SubElement(root, "key", id="node_x", for_="node", type="double")
        node_x_key.set("attr.name", "x")

        node_y_key = ET.SubElement(root, "key", id="node_y", for_="node", type="double")
        node_y_key.set("attr.name", "y")

        node_buildings_key = ET.SubElement(root, "key", id="node_buildings", for_="node")
        node_buildings_key.set("attr.name", "buildings")

        # Define attributes for edges
        edge_from_key = ET.SubElement(root, "key", id="edge_from", for_="edge")
        edge_from_key.set("attr.name", "from_node")

        edge_to_key = ET.SubElement(root, "key", id="edge_to", for_="edge")
        edge_to_key.set("attr.name", "to_node")

        edge_length_key = ET.SubElement(root, "key", id="edge_length", for_="edge", type="double")
        edge_length_key.set("attr.name", "length_m")

        edge_mode_key = ET.SubElement(root, "key", id="edge_mode", for_="edge", type="int")
        edge_mode_key.set("attr.name", "mode")

        # Create graph element
        graph = ET.SubElement(root, "graph", id="graph", edgedefault="directed")

        # Export nodes
        for node_id, node in self.nodes.items():
            node_elem = ET.SubElement(graph, "node", id=str(node_id))

            # Add x coordinate
            x_data = ET.SubElement(node_elem, "data", key="node_x")
            x_data.text = str(node.x)

            # Add y coordinate
            y_data = ET.SubElement(node_elem, "data", key="node_y")
            y_data.text = str(node.y)

            # Add buildings as JSON string
            buildings_json = json.dumps([b.to_dict() for b in node.buildings])
            buildings_data = ET.SubElement(node_elem, "data", key="node_buildings")
            buildings_data.text = buildings_json

        # Export edges
        for edge_id, edge in self.edges.items():
            edge_elem = ET.SubElement(
                graph, "edge", id=str(edge_id), source=str(edge.from_node), target=str(edge.to_node)
            )

            # Add from_node
            from_data = ET.SubElement(edge_elem, "data", key="edge_from")
            from_data.text = str(edge.from_node)

            # Add to_node
            to_data = ET.SubElement(edge_elem, "data", key="edge_to")
            to_data.text = str(edge.to_node)

            # Add length
            length_data = ET.SubElement(edge_elem, "data", key="edge_length")
            length_data.text = str(edge.length_m)

            # Add mode
            mode_data = ET.SubElement(edge_elem, "data", key="edge_mode")
            mode_data.text = str(edge.mode.value)

        # Create ElementTree and write to file
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(filepath, encoding="utf-8", xml_declaration=True)

    @classmethod
    def from_graphml(cls, filepath: str) -> "Graph":
        """Import graph from GraphML format."""
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Namespace handling
        namespace = {"default": "http://graphml.graphdrawing.org/xmlns"}

        # Create graph instance
        graph = cls()

        # Find graph element
        graph_elem = root.find("default:graph", namespace)
        if graph_elem is None:
            graph_elem = root.find("graph")

        if graph_elem is None:
            raise ValueError("No graph element found in GraphML file")

        # Import nodes
        node_elems = graph_elem.findall("default:node", namespace)
        if not node_elems:
            node_elems = graph_elem.findall("node")

        for node_elem in node_elems:
            node_id_attr = node_elem.get("id")
            if node_id_attr is None:
                raise ValueError("Node missing id attribute")
            node_id = int(node_id_attr)

            # Extract node attributes
            x = None
            y = None
            buildings_json = None

            data_elems = node_elem.findall("default:data", namespace)
            if not data_elems:
                data_elems = node_elem.findall("data")

            for data_elem in data_elems:
                key = data_elem.get("key")

                if key == "node_x":
                    if data_elem.text is not None:
                        x = float(data_elem.text)
                elif key == "node_y":
                    if data_elem.text is not None:
                        y = float(data_elem.text)
                elif key == "node_buildings":
                    buildings_json = data_elem.text

            if x is None or y is None:
                raise ValueError(f"Node {node_id} missing coordinates")

            # Create node
            node = Node(id=NodeID(node_id), x=x, y=y)

            # Parse buildings
            if buildings_json:
                try:
                    buildings_data = json.loads(buildings_json)
                    for b_data in buildings_data:
                        building = Building.from_dict(b_data)
                        node.add_building(building)
                except (json.JSONDecodeError, KeyError) as e:
                    raise ValueError(f"Failed to parse buildings for node {node_id}: {e}")

            graph.add_node(node)

        # Import edges
        edge_elems = graph_elem.findall("default:edge", namespace)
        if not edge_elems:
            edge_elems = graph_elem.findall("edge")

        for edge_elem in edge_elems:
            edge_id_attr = edge_elem.get("id")
            if edge_id_attr is None:
                raise ValueError("Edge missing id attribute")
            edge_id = int(edge_id_attr)

            from_node_attr = edge_elem.get("source")
            if from_node_attr is None:
                raise ValueError("Edge missing source attribute")
            from_node = NodeID(int(from_node_attr))

            to_node_attr = edge_elem.get("target")
            if to_node_attr is None:
                raise ValueError("Edge missing target attribute")
            to_node = NodeID(int(to_node_attr))

            # Extract edge attributes
            length_m = None
            mode_value = None

            data_elems = edge_elem.findall("default:data", namespace)
            if not data_elems:
                data_elems = edge_elem.findall("data")

            for data_elem in data_elems:
                key = data_elem.get("key")

                if key == "edge_length" and data_elem.text is not None:
                    length_m = float(data_elem.text)
                elif key == "edge_mode" and data_elem.text is not None:
                    mode_value = int(data_elem.text)

            if length_m is None or mode_value is None:
                raise ValueError(f"Edge {edge_id} missing required attributes")

            # Create edge with Mode enum
            mode = Mode(mode_value)
            edge = Edge(
                id=EdgeID(edge_id),
                from_node=from_node,
                to_node=to_node,
                length_m=length_m,
                mode=mode,
            )

            graph.add_edge(edge)

        return graph
