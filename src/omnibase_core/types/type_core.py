"""Core types with minimal dependencies for breaking circular imports.

This module provides fundamental type definitions that are used across
the codebase without introducing circular dependencies. These types
serve as a dependency inversion layer.

Design Principles:
- Zero external dependencies (except typing and dataclasses)
- Simple data structures only (no validation logic)
- Protocol-based interfaces for flexibility
"""

from omnibase_core.protocols import ProtocolSchemaValue

from .typed_dict_basic_error_context import TypedDictBasicErrorContext

__all__ = [
    "TypedDictBasicErrorContext",
    "ProtocolSchemaValue",
]
