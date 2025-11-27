"""
Generic Field Converter Pattern.

Provides a reusable, extensible pattern for converting string-based data
to typed fields, replacing large conditional logic with a strategy pattern.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from omnibase_core.utils.util_field_converter import FieldConverter

from .model_field_converter_registry import ModelFieldConverterRegistry

# Export all types
__all__ = [
    "FieldConverter",
    "ModelFieldConverterRegistry",
]
