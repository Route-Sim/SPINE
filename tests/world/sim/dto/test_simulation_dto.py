"""Tests for SimulationParamsDTO."""

import pytest
from pydantic import ValidationError

from world.sim.dto.simulation_dto import SimulationParamsDTO


class TestSimulationParamsDTO:
    """Test suite for SimulationParamsDTO."""

    def test_create_with_both_params(self) -> None:
        """Test creating DTO with both tick_rate and speed."""
        dto = SimulationParamsDTO(tick_rate=30, speed=0.1)
        assert dto.tick_rate == 30
        assert dto.speed == 0.1

    def test_create_with_tick_rate_only(self) -> None:
        """Test creating DTO with only tick_rate."""
        dto = SimulationParamsDTO(tick_rate=50)
        assert dto.tick_rate == 50
        assert dto.speed is None

    def test_create_with_speed_only(self) -> None:
        """Test creating DTO with only speed."""
        dto = SimulationParamsDTO(speed=0.2)
        assert dto.tick_rate is None
        assert dto.speed == 0.2

    def test_create_with_no_params(self) -> None:
        """Test creating DTO with no parameters (both None)."""
        dto = SimulationParamsDTO()
        assert dto.tick_rate is None
        assert dto.speed is None

    def test_tick_rate_validation_min(self) -> None:
        """Test tick_rate minimum value validation."""
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            SimulationParamsDTO(tick_rate=0)

    def test_tick_rate_validation_max(self) -> None:
        """Test tick_rate maximum value validation."""
        with pytest.raises(ValidationError, match="less than or equal to 100"):
            SimulationParamsDTO(tick_rate=101)

    def test_speed_validation_min(self) -> None:
        """Test speed minimum value validation."""
        with pytest.raises(ValidationError, match="greater than 0"):
            SimulationParamsDTO(speed=0.0)

    def test_speed_validation_max(self) -> None:
        """Test speed maximum value validation."""
        with pytest.raises(ValidationError, match="less than or equal to 10"):
            SimulationParamsDTO(speed=10.1)

    def test_to_dict_with_both_params(self) -> None:
        """Test to_dict with both parameters."""
        dto = SimulationParamsDTO(tick_rate=40, speed=0.15)
        result = dto.to_dict()
        assert result == {"tick_rate": 40, "speed": 0.15}

    def test_to_dict_with_tick_rate_only(self) -> None:
        """Test to_dict with only tick_rate."""
        dto = SimulationParamsDTO(tick_rate=35)
        result = dto.to_dict()
        assert result == {"tick_rate": 35}
        assert "speed" not in result

    def test_to_dict_with_speed_only(self) -> None:
        """Test to_dict with only speed."""
        dto = SimulationParamsDTO(speed=0.25)
        result = dto.to_dict()
        assert result == {"speed": 0.25}
        assert "tick_rate" not in result

    def test_to_dict_with_no_params(self) -> None:
        """Test to_dict with no parameters."""
        dto = SimulationParamsDTO()
        result = dto.to_dict()
        assert result == {}

    def test_from_dict_with_both_params(self) -> None:
        """Test from_dict with both parameters."""
        dto = SimulationParamsDTO.from_dict({"tick_rate": 45, "speed": 0.3})
        assert dto.tick_rate == 45
        assert dto.speed == 0.3

    def test_from_dict_with_tick_rate_only(self) -> None:
        """Test from_dict with only tick_rate."""
        dto = SimulationParamsDTO.from_dict({"tick_rate": 55})
        assert dto.tick_rate == 55
        assert dto.speed is None

    def test_from_dict_with_speed_only(self) -> None:
        """Test from_dict with only speed."""
        dto = SimulationParamsDTO.from_dict({"speed": 0.4})
        assert dto.tick_rate is None
        assert dto.speed == 0.4

    def test_from_dict_with_empty_dict(self) -> None:
        """Test from_dict with empty dictionary."""
        dto = SimulationParamsDTO.from_dict({})
        assert dto.tick_rate is None
        assert dto.speed is None

    def test_valid_tick_rate_range(self) -> None:
        """Test valid tick_rate range boundaries."""
        dto_min = SimulationParamsDTO(tick_rate=1)
        assert dto_min.tick_rate == 1

        dto_max = SimulationParamsDTO(tick_rate=100)
        assert dto_max.tick_rate == 100

    def test_valid_speed_range(self) -> None:
        """Test valid speed range boundaries."""
        dto_min = SimulationParamsDTO(speed=0.01)
        assert dto_min.speed == 0.01

        dto_max = SimulationParamsDTO(speed=10.0)
        assert dto_max.speed == 10.0
