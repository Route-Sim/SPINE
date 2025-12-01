"""DTOs for agent creation and management."""

from pydantic import BaseModel


class BuildingCreateDTO(BaseModel):
    """DTO for building agent creation parameters.

    Currently buildings have no specific parameters beyond base agent fields.
    """

    pass
