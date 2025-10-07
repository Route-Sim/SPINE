"""Tests for FSM states."""

from core.fsm import VehicleState


def test_vehicle_states_exist() -> None:
    """Test that all vehicle states are defined."""
    assert VehicleState.IDLE is not None
    assert VehicleState.BIDDING is not None
    assert VehicleState.ASSIGNED is not None
    assert VehicleState.ENROUTE is not None
    assert VehicleState.AT_NODE is not None
    assert VehicleState.HANDOFF is not None
    assert VehicleState.OUT_OF_SERVICE is not None


def test_vehicle_state_values_are_unique() -> None:
    """Test that all vehicle state values are unique."""
    states = [state.value for state in VehicleState]
    assert len(states) == len(set(states))
