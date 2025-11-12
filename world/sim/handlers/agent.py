"""Handler for agent management actions (create, delete, update)."""

import random
from typing import Any

from core.types import AgentID, NodeID
from world.graph.graph import Graph

from ..queues import (
    Signal,
    SignalType,
    create_agent_described_signal,
    create_agent_listed_signal,
    create_error_signal,
)
from .base import HandlerContext


def _emit_error(context: HandlerContext, error_message: str) -> None:
    """Emit an error signal."""
    try:
        context.signal_queue.put(
            create_error_signal(error_message, context.state.current_tick), timeout=1.0
        )
    except Exception as e:
        context.logger.error(f"Failed to emit error signal: {e}")


def _get_random_spawn_node(graph: Graph) -> NodeID:
    """Select a random node from the graph for agent spawning.

    Args:
        graph: Graph to select node from

    Returns:
        Random NodeID from the graph

    Raises:
        ValueError: If graph has no nodes
    """
    if not graph.nodes:
        raise ValueError("Cannot spawn agent: graph has no nodes")
    return random.choice(list(graph.nodes.keys()))


class AgentActionHandler:
    """Handler for agent management actions."""

    @staticmethod
    def handle_create(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle create agent action.

        Args:
            params: Action parameters (required 'agent_id', 'agent_kind', optional 'agent_data')
            context: Handler context

        Raises:
            ValueError: If required parameters are missing
        """
        if "agent_id" not in params:
            raise ValueError("agent_id is required for agent.create action")
        if "agent_kind" not in params:
            raise ValueError("agent_kind is required for agent.create action")

        agent_id_str = params["agent_id"]
        agent_kind = params["agent_kind"]
        agent_data = params.get("agent_data", {})

        if not isinstance(agent_id_str, str):
            raise ValueError("agent_id must be a string")
        if not isinstance(agent_kind, str):
            raise ValueError("agent_kind must be a string")
        if not isinstance(agent_data, dict):
            raise ValueError("agent_data must be a dictionary")

        try:
            agent_id = AgentID(agent_id_str)

            # Import agent classes dynamically based on kind
            from agents.base import AgentBase

            agent_instance: AgentBase

            if agent_kind == "building":
                from agents.buildings.building_agent import BuildingAgent
                from core.buildings.base import Building
                from core.types import BuildingID

                # Create building data structure (convert AgentID to BuildingID)
                building = Building(id=BuildingID(str(agent_id)))
                # Create agent wrapper (BuildingAgent has same interface as AgentBase)
                agent_instance = BuildingAgent(  # type: ignore[assignment]
                    building=building,
                    id=agent_id,
                    kind=agent_kind,
                    **agent_data,
                )
            elif agent_kind == "truck":
                from agents.transports.truck import Truck

                # Extract max_speed_kph with validation
                max_speed_kph = agent_data.get("max_speed_kph", 100.0)
                if not isinstance(max_speed_kph, int | float) or max_speed_kph <= 0:
                    raise ValueError("max_speed_kph must be a positive number")

                # Always spawn on random node
                spawn_node = _get_random_spawn_node(context.world.graph)

                agent_instance = Truck(  # type: ignore[assignment]
                    id=agent_id,
                    kind=agent_kind,
                    max_speed_kph=float(max_speed_kph),
                    current_speed_kph=0.0,
                    current_node=spawn_node,
                    current_edge=None,
                    edge_progress_m=0.0,
                    route=[],
                    destination=None,
                )
            else:
                # Fallback to base agent
                # AgentBase doesn't accept arbitrary kwargs, so store agent_data in tags
                agent_instance = AgentBase(id=agent_id, kind=agent_kind, tags=agent_data.copy())

            context.world.add_agent(agent_id, agent_instance)
            context.logger.info(f"Added agent: {agent_id_str} of kind {agent_kind}")

            # Emit agent.created signal with full agent state
            agent_created_signal = Signal(
                signal=SignalType.AGENT_CREATED.value,
                data=agent_instance.serialize_full(),
            )
            try:
                context.signal_queue.put(agent_created_signal, timeout=1.0)
            except Exception as e:
                context.logger.error(f"Failed to emit agent.created signal: {e}")

        except ImportError as e:
            context.logger.error(f"Failed to import agent class for kind {agent_kind}: {e}")
            _emit_error(context, f"Unknown agent kind: {agent_kind}")
            raise
        except Exception as e:
            context.logger.error(f"Failed to add agent {agent_id_str}: {e}", exc_info=True)
            _emit_error(context, f"Failed to create agent: {e}")
            raise

    @staticmethod
    def handle_delete(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle delete agent action.

        Args:
            params: Action parameters (required 'agent_id')
            context: Handler context

        Raises:
            ValueError: If agent_id is missing or agent not found
        """
        if "agent_id" not in params:
            raise ValueError("agent_id is required for agent.delete action")

        agent_id_str = params["agent_id"]
        if not isinstance(agent_id_str, str):
            raise ValueError("agent_id must be a string")

        try:
            agent_id = AgentID(agent_id_str)
            context.world.remove_agent(agent_id)
            context.logger.info(f"Removed agent: {agent_id_str}")
        except ValueError as e:
            context.logger.warning(f"Agent {agent_id_str} not found: {e}")
            _emit_error(context, f"Agent not found: {agent_id_str}")
            raise
        except Exception as e:
            context.logger.error(f"Failed to remove agent {agent_id_str}: {e}", exc_info=True)
            _emit_error(context, f"Failed to delete agent: {e}")
            raise

    @staticmethod
    def handle_update(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle update agent action.

        Args:
            params: Action parameters (required 'agent_id', 'agent_data')
            context: Handler context

        Raises:
            ValueError: If required parameters are missing or agent not found
        """
        if "agent_id" not in params:
            raise ValueError("agent_id is required for agent.update action")
        if "agent_data" not in params:
            raise ValueError("agent_data is required for agent.update action")

        agent_id_str = params["agent_id"]
        agent_data = params["agent_data"]

        if not isinstance(agent_id_str, str):
            raise ValueError("agent_id must be a string")
        if not isinstance(agent_data, dict):
            raise ValueError("agent_data must be a dictionary")

        try:
            agent_id = AgentID(agent_id_str)
            context.world.modify_agent(agent_id, agent_data)
            context.logger.info(f"Modified agent: {agent_id_str}")
        except ValueError as e:
            context.logger.warning(f"Agent {agent_id_str} not found: {e}")
            _emit_error(context, f"Agent not found: {agent_id_str}")
            raise
        except Exception as e:
            context.logger.error(f"Failed to modify agent {agent_id_str}: {e}", exc_info=True)
            _emit_error(context, f"Failed to update agent: {e}")
            raise

    @staticmethod
    def handle_describe(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle describe agent action by returning the full agent state.

        Args:
            params: Action parameters (required 'agent_id')
            context: Handler context

        Raises:
            ValueError: If simulation is not running or agent_id is missing/unknown
        """
        if "agent_id" not in params:
            raise ValueError("agent_id is required for agent.describe action")

        agent_id_str = params["agent_id"]
        if not isinstance(agent_id_str, str):
            raise ValueError("agent_id must be a string")

        agent_id = AgentID(agent_id_str)
        agent = context.world.agents.get(agent_id)
        if agent is None:
            message = f"Agent not found: {agent_id_str}"
            context.logger.warning(message)
            _emit_error(context, message)
            raise ValueError(message)

        agent_state = agent.serialize_full()

        try:
            context.signal_queue.put(
                create_agent_described_signal(agent_state, context.state.current_tick),
                timeout=1.0,
            )
            context.logger.info(f"Described agent: {agent_id_str}")
        except Exception as exc:
            context.logger.error(
                f"Failed to emit agent.described signal for {agent_id_str}: {exc}",
                exc_info=True,
            )
            _emit_error(context, f"Failed to describe agent: {exc}")
            raise

    @staticmethod
    def handle_list(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle list agent action by returning all matching agent states.

        Args:
            params: Action parameters (optional 'agent_kind')
            context: Handler context

        Raises:
            ValueError: If provided filters are invalid
        """
        agent_kind_filter: str | None = None
        if "agent_kind" in params:
            agent_kind_value = params["agent_kind"]
            if not isinstance(agent_kind_value, str):
                raise ValueError("agent_kind must be a string")
            agent_kind_filter = agent_kind_value

        agents_data: list[dict[str, Any]] = []
        for agent in context.world.agents.values():
            if agent_kind_filter is not None and agent.kind != agent_kind_filter:
                continue
            agent_state = agent.serialize_full()
            agent_state["agent_id"] = str(agent_state.get("id", agent.id))
            agents_data.append(agent_state)

        try:
            context.signal_queue.put(
                create_agent_listed_signal(
                    agents=agents_data,
                    total=len(agents_data),
                    tick=context.state.current_tick,
                ),
                timeout=1.0,
            )
            context.logger.info(
                "Listed %s agents%s",
                len(agents_data),
                f" of kind {agent_kind_filter}" if agent_kind_filter else "",
            )
        except Exception as exc:
            context.logger.error(
                f"Failed to emit agent.listed signal (filter={agent_kind_filter}): {exc}",
                exc_info=True,
            )
            _emit_error(context, f"Failed to list agents: {exc}")
            raise
