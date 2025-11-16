"""Utility functions for simulation handlers."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world.world import World


def collect_agents_data(
    world: "World", agent_kind_filter: str | None = None
) -> list[dict[str, Any]]:
    """Collect and serialize all agents from world, optionally filtered by kind.

    Args:
        world: World instance containing agents
        agent_kind_filter: Optional agent kind to filter by

    Returns:
        List of serialized agent dictionaries with agent_id field added
    """
    agents_data: list[dict[str, Any]] = []
    for agent in world.agents.values():
        if agent_kind_filter is not None and agent.kind != agent_kind_filter:
            continue
        agent_state = agent.serialize_full()
        agent_state["agent_id"] = str(
            agent_state.get("id", agent.id)
        )  # TODO: Remove the unnecessary agent_id
        agents_data.append(agent_state)
    return agents_data
