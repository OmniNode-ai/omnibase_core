"""Core types with minimal dependencies for breaking circular imports.

This module provides fundamental type definitions that are used across
the codebase without introducing circular dependencies. These types
serve as a dependency inversion layer.

Design Principles:
- Zero external dependencies (except typing and dataclasses)
- Simple data structures only (no validation logic)
- Protocol-based interfaces for flexibility
"""

from .basic_error_context import BasicErrorContext
from .protocol_error_context import ProtocolErrorContext
from .protocol_schema_value import ProtocolSchemaValue

__all__ = [
    "BasicErrorContext",
    "ProtocolErrorContext",
    "ProtocolSchemaValue",
]
