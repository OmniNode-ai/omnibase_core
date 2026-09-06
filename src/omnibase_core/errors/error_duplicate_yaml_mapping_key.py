# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed failure for a duplicate key in a strict YAML mapping parse."""

from __future__ import annotations


class DuplicateYamlMappingKeyError(ValueError):
    """A YAML mapping repeats a key that SafeLoader would otherwise overwrite."""

    def __init__(
        self,
        *,
        source: str,
        key: object,
        line: int,
        column: int,
        mapping_line: int,
        mapping_column: int,
    ) -> None:
        self.source = source
        self.key = key
        self.line = line
        self.column = column
        self.mapping_line = mapping_line
        self.mapping_column = mapping_column
        super().__init__(
            f"{source}:{line}:{column}: duplicate key {key!r} in YAML mapping "
            f"(mapping starts at {mapping_line}:{mapping_column})",
        )


__all__ = ["DuplicateYamlMappingKeyError"]
