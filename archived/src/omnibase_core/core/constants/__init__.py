"""Core constants module for ONEX system.

This module provides core constants used throughout the ONEX ecosystem,
including event types, system constants, and configuration values.
"""

from .event_types import CoreEventTypes, normalize_legacy_event_type

__all__ = [
    "CoreEventTypes",
    "normalize_legacy_event_type",
]
