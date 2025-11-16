"""Base class for all signal data DTOs.

This module provides the abstract base class that all signal DTOs must inherit from.
Each concrete DTO should be defined in its own module within this package.
"""

from abc import ABC
from typing import Any

from pydantic import BaseModel, ConfigDict


class SignalData(BaseModel, ABC):
    """Abstract base class for all signal data DTOs.

    Signal data DTOs:
    - Provide compile-time type checking (mypy --strict)
    - Enable runtime validation (Pydantic)
    - Self-document signal structures
    - Allow incremental migration from untyped dicts

    All signal DTOs should inherit from this class and define their specific fields.
    Each DTO should be in its own module within the signal_dtos package.
    """

    model_config = ConfigDict(
        # Allow arbitrary types for flexibility with complex structures
        arbitrary_types_allowed=True,
        # Validate on assignment for immediate feedback
        validate_assignment=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert DTO to dictionary for signal emission.

        This method can be overridden by subclasses for custom serialization,
        but the default implementation uses Pydantic's model_dump.

        Returns:
            Dictionary representation suitable for Signal.data field
        """
        return self.model_dump()
