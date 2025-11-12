from __future__ import annotations

import pytest

from agents.transports.truck import Truck
from core.buildings.parking import Parking
from core.types import AgentID, BuildingID, NodeID
from world.graph.graph import Graph
from world.graph.node import Node
from world.world import World


def _build_world_with_parking(
    node_id: NodeID, parking_id: BuildingID, capacity: int = 2
) -> tuple[World, Parking]:
    graph = Graph()
    node = Node(id=node_id, x=0.0, y=0.0)
    parking = Parking(id=parking_id, capacity=capacity)
    node.add_building(parking)
    graph.add_node(node)
    world = World(graph=graph, router=None, traffic=None, dt_s=1.0)
    return world, parking


def _make_truck(node_id: NodeID | None) -> Truck:
    truck = Truck(
        id=AgentID("truck-1"),
        kind="truck",
    )
    truck.current_node = node_id
    return truck


def test_truck_parking_registers_building_and_updates_state() -> None:
    node_id = NodeID(1)
    parking_id = BuildingID("parking-1")
    world, parking = _build_world_with_parking(node_id, parking_id)
    truck = _make_truck(node_id)

    initial_state = truck.serialize_diff()
    assert initial_state is not None
    assert initial_state["current_building_id"] is None

    truck.park_in_building(world, parking_id)
    assert truck.current_building_id == parking_id
    assert AgentID("truck-1") in parking.current_agents

    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_building_id"] == str(parking_id)


def test_truck_leave_parking_releases_building() -> None:
    node_id = NodeID(2)
    parking_id = BuildingID("parking-2")
    world, parking = _build_world_with_parking(node_id, parking_id)
    truck = _make_truck(node_id)

    truck.serialize_diff()
    truck.park_in_building(world, parking_id)
    truck.serialize_diff()

    truck.leave_parking(world)
    assert truck.current_building_id is None
    assert AgentID("truck-1") not in parking.current_agents

    diff = truck.serialize_diff()
    assert diff is not None
    assert diff["current_building_id"] is None


def test_truck_parking_requires_same_node() -> None:
    parking_node = NodeID(3)
    other_node = NodeID(4)
    parking_id = BuildingID("parking-3")
    world, _ = _build_world_with_parking(parking_node, parking_id)

    other = Node(id=other_node, x=1.0, y=1.0)
    world.graph.add_node(other)

    truck = _make_truck(other_node)

    with pytest.raises(ValueError):
        truck.park_in_building(world, parking_id)


def test_truck_parking_respects_capacity() -> None:
    node_id = NodeID(5)
    parking_id = BuildingID("parking-5")
    world, parking = _build_world_with_parking(node_id, parking_id, capacity=1)
    parking.park(AgentID("other-truck"))

    truck = _make_truck(node_id)

    with pytest.raises(ValueError):
        truck.park_in_building(world, parking_id)
