"""
ONEX Type System

Centralized type definitions to eliminate Any types across the codebase.
"""

from typing import Any

from .model_onex_common_types import (
    CliValue,
    ConfigValue,
    EnvValue,
    JsonSerializable,
    MetadataValue,
    ParameterValue,
    PropertyValue,
    ResultValue,
    ValidationValue,
)

# model_json_serializable.py contains a PEP 695 recursive type statement version of JsonSerializable
# For the recursive definition, import directly:
# from omnibase_core.models.types.model_json_serializable import JsonSerializable as JsonSerializableRecursive

__all__ = [
    "CliValue",
    "ConfigValue",
    "EnvValue",
    "JsonSerializable",
    "MetadataValue",
    "ParameterValue",
    "PropertyValue",
    "ResultValue",
    "ValidationValue",
]
