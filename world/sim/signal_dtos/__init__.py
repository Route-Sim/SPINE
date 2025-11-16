"""Signal Data Transfer Objects (DTOs) for type-safe signal data structures.

This package provides Pydantic-based DTOs for signal data structures to ensure
consistency, enable compile-time type checking via mypy, and provide runtime
validation.

The system is designed for incremental migration: each signal type that benefits
from type safety gets its own DTO class in a separate module within this package.

Usage:
    from world.sim.signal_dtos import MapCreatedSignalData, SignalData

    # Create a typed signal
    signal_data = MapCreatedSignalData(
        map_width=100.0,
        map_height=100.0,
        # ... all required fields
    )
"""

from .base import SignalData
from .map_created import MapCreatedSignalData

__all__ = ["SignalData", "MapCreatedSignalData"]
