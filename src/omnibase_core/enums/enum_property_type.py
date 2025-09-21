"""
Property type enum for environment properties.

This module provides the PropertyTypeEnum for defining supported property types
in environment property storage with proper validation and constraints.
"""

from __future__ import annotations

from enum import Enum


class PropertyTypeEnum(str, Enum):
    """Enum for supported property types."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    STRING_LIST = "string_list"
    INTEGER_LIST = "integer_list"
    FLOAT_LIST = "float_list"
    DATETIME = "datetime"
    UUID = "uuid"
