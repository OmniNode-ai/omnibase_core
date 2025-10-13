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
