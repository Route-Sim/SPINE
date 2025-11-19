"""Tests for agent DTOs."""

import pytest
from pydantic import ValidationError

from core.types import AgentID, NodeID
from world.sim.dto.agent_dto import TruckCreateDTO


def test_truck_create_dto_defaults() -> None:
    """Test TruckCreateDTO with default values."""
    dto = TruckCreateDTO()
    assert dto.max_speed_kph == 100.0
    assert dto.risk_factor == 0.5
    assert dto.initial_balance_ducats == 0.0


def test_truck_create_dto_custom_values() -> None:
    """Test TruckCreateDTO with custom values."""
    dto = TruckCreateDTO(max_speed_kph=120.0, risk_factor=0.8, initial_balance_ducats=1000.0)
    assert dto.max_speed_kph == 120.0
    assert dto.risk_factor == 0.8
    assert dto.initial_balance_ducats == 1000.0


def test_truck_create_dto_validates_max_speed() -> None:
    """Test that max_speed_kph must be positive."""
    with pytest.raises(ValidationError) as exc_info:
        TruckCreateDTO(max_speed_kph=0.0)
    errors = exc_info.value.errors()
    assert any("max_speed_kph" in str(err["loc"]) for err in errors)

    with pytest.raises(ValidationError) as exc_info:
        TruckCreateDTO(max_speed_kph=-50.0)
    errors = exc_info.value.errors()
    assert any("max_speed_kph" in str(err["loc"]) for err in errors)


def test_truck_create_dto_validates_risk_factor_range() -> None:
    """Test that risk_factor must be between 0.0 and 1.0."""
    # Below minimum
    with pytest.raises(ValidationError) as exc_info:
        TruckCreateDTO(risk_factor=-0.1)
    errors = exc_info.value.errors()
    assert any("risk_factor" in str(err["loc"]) for err in errors)

    # Above maximum
    with pytest.raises(ValidationError) as exc_info:
        TruckCreateDTO(risk_factor=1.5)
    errors = exc_info.value.errors()
    assert any("risk_factor" in str(err["loc"]) for err in errors)

    # Edge cases should work
    dto_min = TruckCreateDTO(risk_factor=0.0)
    assert dto_min.risk_factor == 0.0

    dto_max = TruckCreateDTO(risk_factor=1.0)
    assert dto_max.risk_factor == 1.0


def test_truck_create_dto_to_truck() -> None:
    """Test conversion from DTO to Truck instance."""
    dto = TruckCreateDTO(max_speed_kph=150.0, risk_factor=0.7, initial_balance_ducats=500.0)

    agent_id = AgentID("test-truck-1")
    spawn_node = NodeID(42)

    truck = dto.to_truck(agent_id=agent_id, kind="truck", spawn_node=spawn_node)

    assert truck.id == agent_id
    assert truck.kind == "truck"
    assert truck.max_speed_kph == 150.0
    assert truck.risk_factor == 0.7
    assert truck.balance_ducats == 500.0
    assert truck.current_node == spawn_node
    assert truck.current_edge is None
    assert truck.current_speed_kph == 0.0
    assert truck.edge_progress_m == 0.0
    assert truck.route == []
    assert truck.destination is None


def test_truck_create_dto_accepts_numeric_types() -> None:
    """Test that DTO accepts both int and float for numeric fields."""
    # Test with integers
    dto_int = TruckCreateDTO(max_speed_kph=120, initial_balance_ducats=1000)
    assert dto_int.max_speed_kph == 120.0
    assert dto_int.initial_balance_ducats == 1000.0

    # Test with floats
    dto_float = TruckCreateDTO(max_speed_kph=120.5, initial_balance_ducats=1000.5)
    assert dto_float.max_speed_kph == 120.5
    assert dto_float.initial_balance_ducats == 1000.5


def test_truck_create_dto_from_dict() -> None:
    """Test creating DTO from dictionary (simulating API input)."""
    data = {"max_speed_kph": 110.0, "risk_factor": 0.6, "initial_balance_ducats": 750.0}

    dto = TruckCreateDTO(**data)

    assert dto.max_speed_kph == 110.0
    assert dto.risk_factor == 0.6
    assert dto.initial_balance_ducats == 750.0


def test_truck_create_dto_partial_data() -> None:
    """Test creating DTO with partial data (uses defaults)."""
    data = {"max_speed_kph": 130.0}

    dto = TruckCreateDTO(**data)

    assert dto.max_speed_kph == 130.0
    assert dto.risk_factor == 0.5  # default
    assert dto.initial_balance_ducats == 0.0  # default
