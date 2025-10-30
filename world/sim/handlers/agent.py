"""Handler for agent management actions (create, delete, update)."""

from typing import Any

from core.types import AgentID

from ..queues import create_error_signal
from .base import HandlerContext


def _emit_error(context: HandlerContext, error_message: str) -> None:
    """Emit an error signal."""
    try:
        context.signal_queue.put(
            create_error_signal(error_message, context.state.current_tick), timeout=1.0
        )
    except Exception as e:
        context.logger.error(f"Failed to emit error signal: {e}")


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
            elif agent_kind == "transport":
                from agents.transports.base import Transport

                agent_instance = Transport(id=agent_id, kind=agent_kind, **agent_data)
            else:
                # Fallback to base agent
                agent_instance = AgentBase(id=agent_id, kind=agent_kind, **agent_data)

            context.world.add_agent(agent_id, agent_instance)
            context.logger.info(f"Added agent: {agent_id_str} of kind {agent_kind}")

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
