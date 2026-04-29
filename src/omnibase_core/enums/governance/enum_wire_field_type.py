# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Allowed field types in wire schema contracts."""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumWireFieldType(str, Enum):
    """Allowed field types in wire schema contracts."""

    UUID = "uuid"
    STRING = "string"
    FLOAT = "float"
    INTEGER = "integer"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"

    def __str__(self) -> str:
        return self.value
