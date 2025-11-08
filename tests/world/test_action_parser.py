"""Tests for action parser."""

import pytest

from world.sim.actions.action_parser import ActionParser, ActionRequest
from world.sim.queues import ActionType


class TestActionRequest:
    """Test ActionRequest model."""

    def test_valid_action_request(self) -> None:
        """Test valid action request creation."""
        request = ActionRequest(action=ActionType.START.value, params={"tick_rate": 30})
        assert request.action == ActionType.START.value
        assert request.params == {"tick_rate": 30}

    def test_action_request_with_empty_params(self) -> None:
        """Test action request with empty params."""
        request = ActionRequest(action=ActionType.STOP.value)
        assert request.action == ActionType.STOP.value
        assert request.params == {}

    def test_invalid_action_format(self) -> None:
        """Test invalid action format."""
        with pytest.raises(ValueError, match="action must follow 'domain.action' format"):
            ActionRequest(action="invalid_format")

    def test_action_with_uppercase(self) -> None:
        """Test action format with uppercase."""
        with pytest.raises(ValueError, match="action must follow 'domain.action' format"):
            ActionRequest(action="Simulation.Start")

    def test_action_with_spaces(self) -> None:
        """Test action format with spaces."""
        with pytest.raises(ValueError, match="action must follow 'domain.action' format"):
            ActionRequest(action="simulation start")

    def test_params_must_be_dict(self) -> None:
        """Test that params must be a dictionary."""
        with pytest.raises(ValueError, match="'params' must be a dictionary"):
            ActionParser().parse({"action": ActionType.START.value, "params": "not_a_dict"})

    def test_missing_action_field(self) -> None:
        """Test missing action field."""
        with pytest.raises(ValueError, match="Missing required field: 'action'"):
            ActionParser().parse({"params": {}})


class TestActionParser:
    """Test ActionParser."""

    def test_parse_valid_request(self) -> None:
        """Test parsing valid request."""
        parser = ActionParser()
        request = parser.parse({"action": ActionType.START.value, "params": {"tick_rate": 30}})
        assert request.action == ActionType.START.value
        assert request.params == {"tick_rate": 30}

    def test_parse_with_missing_params(self) -> None:
        """Test parsing request with missing params field."""
        parser = ActionParser()
        request = parser.parse({"action": ActionType.STOP.value})
        assert request.action == ActionType.STOP.value
        assert request.params == {}

    def test_parse_invalid_format(self) -> None:
        """Test parsing invalid format."""
        parser = ActionParser()
        with pytest.raises(ValueError):
            parser.parse({"action": "invalid"})
