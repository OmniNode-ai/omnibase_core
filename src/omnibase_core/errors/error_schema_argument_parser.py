# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Schema argument parser error for the registry-driven CLI.

Raised by ServiceSchemaArgumentParser when a JSON Schema cannot be converted
to an argparse.ArgumentParser.

.. versionadded:: 0.19.0  (OMN-2553)
"""

from __future__ import annotations

__all__ = [
    "SchemaParseError",
]


class SchemaParseError(Exception):
    """Raised when a JSON Schema cannot be converted to an argparse parser.

    This indicates a malformed or unsupported schema structure, such as:
    - The schema is not of type ``object``.
    - A property schema is not a dict.
    - A property uses an unsupported JSON Schema type.

    Callers should validate the schema structure before calling
    ``ServiceSchemaArgumentParser.from_schema()``.

    .. versionadded:: 0.19.0  (OMN-2553)
    """
