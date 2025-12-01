"""Tests for GasStation building class."""

import pytest

from core.buildings.base import Building
from core.buildings.gas_station import GasStation
from core.types import AgentID, BuildingID


class TestGasStationCreation:
    """Tests for GasStation construction and validation."""

    def test_create_valid_gas_station(self) -> None:
        """Test creating a valid gas station."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=4,
            cost_factor=1.15,
        )
        assert gas_station.id == BuildingID("gas-1")
        assert gas_station.capacity == 4
        assert gas_station.cost_factor == 1.15
        assert gas_station.TYPE == "gas_station"

    def test_create_with_zero_capacity_raises(self) -> None:
        """Test that zero capacity raises ValueError."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            GasStation(
                id=BuildingID("gas-1"),
                capacity=0,
                cost_factor=1.0,
            )

    def test_create_with_negative_capacity_raises(self) -> None:
        """Test that negative capacity raises ValueError."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            GasStation(
                id=BuildingID("gas-1"),
                capacity=-5,
                cost_factor=1.0,
            )

    def test_create_with_zero_cost_factor_raises(self) -> None:
        """Test that zero cost_factor raises ValueError."""
        with pytest.raises(ValueError, match="cost_factor must be positive"):
            GasStation(
                id=BuildingID("gas-1"),
                capacity=4,
                cost_factor=0.0,
            )

    def test_create_with_negative_cost_factor_raises(self) -> None:
        """Test that negative cost_factor raises ValueError."""
        with pytest.raises(ValueError, match="cost_factor must be positive"):
            GasStation(
                id=BuildingID("gas-1"),
                capacity=4,
                cost_factor=-0.5,
            )


class TestGasStationPricing:
    """Tests for GasStation fuel price calculation."""

    def test_get_fuel_price_base_factor(self) -> None:
        """Test price calculation with cost_factor of 1.0."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=4,
            cost_factor=1.0,
        )
        assert gas_station.get_fuel_price(5.0) == 5.0
        assert gas_station.get_fuel_price(10.0) == 10.0

    def test_get_fuel_price_premium(self) -> None:
        """Test price calculation with premium cost_factor."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=4,
            cost_factor=1.2,  # 20% premium
        )
        assert abs(gas_station.get_fuel_price(5.0) - 6.0) < 0.001
        assert abs(gas_station.get_fuel_price(10.0) - 12.0) < 0.001

    def test_get_fuel_price_discount(self) -> None:
        """Test price calculation with discount cost_factor."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=4,
            cost_factor=0.8,  # 20% discount
        )
        assert abs(gas_station.get_fuel_price(5.0) - 4.0) < 0.001
        assert abs(gas_station.get_fuel_price(10.0) - 8.0) < 0.001


class TestGasStationOccupancy:
    """Tests for GasStation occupancy management."""

    def test_has_space_empty(self) -> None:
        """Test has_space on empty gas station."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=2,
            cost_factor=1.0,
        )
        assert gas_station.has_space() is True

    def test_has_space_partial(self) -> None:
        """Test has_space with partial occupancy."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=2,
            cost_factor=1.0,
        )
        gas_station.enter(AgentID("truck-1"))
        assert gas_station.has_space() is True

    def test_has_space_full(self) -> None:
        """Test has_space when at capacity."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=2,
            cost_factor=1.0,
        )
        gas_station.enter(AgentID("truck-1"))
        gas_station.enter(AgentID("truck-2"))
        assert gas_station.has_space() is False

    def test_enter_agent(self) -> None:
        """Test entering an agent."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=2,
            cost_factor=1.0,
        )
        gas_station.enter(AgentID("truck-1"))
        assert AgentID("truck-1") in gas_station.current_agents

    def test_enter_duplicate_raises(self) -> None:
        """Test that entering same agent twice raises ValueError."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=2,
            cost_factor=1.0,
        )
        gas_station.enter(AgentID("truck-1"))
        with pytest.raises(ValueError, match="already in"):
            gas_station.enter(AgentID("truck-1"))

    def test_enter_at_capacity_raises(self) -> None:
        """Test that entering when at capacity raises ValueError."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=1,
            cost_factor=1.0,
        )
        gas_station.enter(AgentID("truck-1"))
        with pytest.raises(ValueError, match="at full capacity"):
            gas_station.enter(AgentID("truck-2"))

    def test_leave_agent(self) -> None:
        """Test leaving an agent."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=2,
            cost_factor=1.0,
        )
        gas_station.enter(AgentID("truck-1"))
        gas_station.leave(AgentID("truck-1"))
        assert AgentID("truck-1") not in gas_station.current_agents

    def test_leave_nonexistent_raises(self) -> None:
        """Test that leaving nonexistent agent raises ValueError."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=2,
            cost_factor=1.0,
        )
        with pytest.raises(ValueError, match="not in"):
            gas_station.leave(AgentID("truck-1"))

    def test_assign_occupants(self) -> None:
        """Test assigning occupants."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=3,
            cost_factor=1.0,
        )
        gas_station.assign_occupants([AgentID("truck-1"), AgentID("truck-2")])
        assert AgentID("truck-1") in gas_station.current_agents
        assert AgentID("truck-2") in gas_station.current_agents
        assert len(gas_station.current_agents) == 2

    def test_assign_occupants_exceeds_capacity_raises(self) -> None:
        """Test that assigning more than capacity raises ValueError."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=2,
            cost_factor=1.0,
        )
        with pytest.raises(ValueError, match="exceeds.*capacity"):
            gas_station.assign_occupants(
                [AgentID("truck-1"), AgentID("truck-2"), AgentID("truck-3")]
            )


class TestGasStationSerialization:
    """Tests for GasStation serialization."""

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=4,
            cost_factor=1.15,
        )
        gas_station.enter(AgentID("truck-1"))

        data = gas_station.to_dict()
        assert data["id"] == "gas-1"
        assert data["type"] == "gas_station"
        assert data["capacity"] == 4
        assert data["cost_factor"] == 1.15
        assert data["current_agents"] == ["truck-1"]

    def test_to_dict_sorted_agents(self) -> None:
        """Test that current_agents are sorted in serialization."""
        gas_station = GasStation(
            id=BuildingID("gas-1"),
            capacity=4,
            cost_factor=1.0,
        )
        gas_station.enter(AgentID("truck-c"))
        gas_station.enter(AgentID("truck-a"))
        gas_station.enter(AgentID("truck-b"))

        data = gas_station.to_dict()
        assert data["current_agents"] == ["truck-a", "truck-b", "truck-c"]

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "id": "gas-1",
            "type": "gas_station",
            "capacity": 4,
            "cost_factor": 1.15,
            "current_agents": ["truck-1", "truck-2"],
        }
        gas_station = GasStation.from_dict(data)
        assert gas_station.id == BuildingID("gas-1")
        assert gas_station.capacity == 4
        assert gas_station.cost_factor == 1.15
        assert AgentID("truck-1") in gas_station.current_agents
        assert AgentID("truck-2") in gas_station.current_agents

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = GasStation(
            id=BuildingID("gas-1"),
            capacity=4,
            cost_factor=1.15,
        )
        original.enter(AgentID("truck-1"))

        data = original.to_dict()
        restored = GasStation.from_dict(data)

        assert restored.id == original.id
        assert restored.capacity == original.capacity
        assert restored.cost_factor == original.cost_factor
        assert restored.current_agents == original.current_agents

    def test_building_factory_creates_gas_station(self) -> None:
        """Test that Building.from_dict creates GasStation for gas_station type."""
        data = {
            "id": "gas-1",
            "type": "gas_station",
            "capacity": 4,
            "cost_factor": 1.0,
            "current_agents": [],
        }
        building = Building.from_dict(data)
        assert isinstance(building, GasStation)
        assert building.id == BuildingID("gas-1")
        assert building.cost_factor == 1.0
