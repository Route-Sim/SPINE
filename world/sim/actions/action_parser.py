"""Action parser for validating and parsing action requests from the Frontend."""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ActionRequest(BaseModel):
    """Action request with domain-based action format."""

    action: str  # Format: "domain.action"
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action")
    @classmethod
    def validate_action_format(cls, v: str) -> str:
        """Validate that action follows 'domain.action' format."""
        if not isinstance(v, str):
            raise ValueError("action must be a string")
        if not re.match(r"^[a-z_]+\.[a-z_]+$", v):
            raise ValueError(
                f"action must follow 'domain.action' format (e.g., 'simulation.start'), got: {v}"
            )
        return v


class ActionParser:
    """Parser for validating and parsing action requests."""

    def parse(self, raw: dict[str, Any]) -> ActionRequest:
        """Parse and validate a raw action request dictionary.

        Args:
            raw: Raw dictionary from JSON message containing 'action' and 'params'

        Returns:
            Validated ActionRequest

        Raises:
            ValueError: If action format is invalid or required fields are missing
            ValidationError: If Pydantic validation fails
        """
        # Ensure we have the required top-level fields
        if "action" not in raw:
            raise ValueError("Missing required field: 'action'")

        # 'params' is optional and defaults to empty dict
        if "params" not in raw:
            raw["params"] = {}

        # Validate params is a dictionary
        if not isinstance(raw["params"], dict):
            raise ValueError("'params' must be a dictionary")

        # Validate using Pydantic model
        return ActionRequest(**raw)
