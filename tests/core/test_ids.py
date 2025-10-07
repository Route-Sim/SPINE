"""Tests for core ID types."""

from core.ids import AgentID, EdgeID, LegID


def test_agent_id_creation() -> None:
    """Test AgentID creation."""
    agent_id = AgentID("agent_1")
    assert agent_id == "agent_1"


def test_edge_id_creation() -> None:
    """Test EdgeID creation."""
    edge_id = EdgeID(42)
    assert edge_id == 42


def test_leg_id_creation() -> None:
    """Test LegID creation."""
    leg_id = LegID("leg_1")
    assert leg_id == "leg_1"
