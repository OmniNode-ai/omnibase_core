# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Parameters of the contract's source vocabulary row (OMN-22011).

Every field is a key of the row: a key the contract carries and nothing reads is data
nobody enforces, and a field the contract lacks fails the load.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dep_provenance_shape import EnumDepProvenanceShape
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dep_provenance.model_dep_provenance_package import (
    ModelDepProvenancePackage,
)

__all__ = ["ModelDepProvenanceVocabulary"]


def _invalid(detail: str) -> ModelOnexError:
    return ModelOnexError(
        message=f"dep_provenance source_vocabulary: {detail}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


class ModelDepProvenanceVocabulary(BaseModel):
    """The names, patterns and package table the checker reads, all from the contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    sources_table: tuple[str, ...]
    table_header_pattern: str
    key_pattern: str
    git_keys: tuple[str, ...]
    git_key: str
    tag_key: str
    local_keys: tuple[str, ...]
    workspace_key: str
    github_org: str
    repository_urls: tuple[str, ...]
    packages: tuple[str, ...]
    package_row_pattern: str
    shape_separator: str
    exempt_packages: tuple[str, ...]
    normalize_pattern: str
    normalize_replacement: str
    lineage_hook: str

    @model_validator(mode="after")
    def _reject_unreadable_values(self) -> ModelDepProvenanceVocabulary:
        for key in (
            "git_key",
            "tag_key",
            "workspace_key",
            "github_org",
            "table_header_pattern",
            "key_pattern",
            "package_row_pattern",
            "shape_separator",
            "normalize_pattern",
            "lineage_hook",
        ):
            if not getattr(self, key).strip():
                raise _invalid(f"parameter {key!r} must be a non-empty string")
        for key in ("sources_table", "git_keys", "repository_urls", "packages"):
            if not getattr(self, key):
                raise _invalid(f"parameter {key!r} must not be empty")
        for key in (
            "table_header_pattern",
            "key_pattern",
            "package_row_pattern",
            "normalize_pattern",
        ):
            try:
                re.compile(getattr(self, key))
            except re.error as exc:
                raise _invalid(
                    f"parameter {key!r} is not a regular expression: {exc}"
                ) from exc
        if self.git_key not in self.git_keys or self.tag_key not in self.git_keys:
            raise _invalid("git_key and tag_key must be among git_keys")
        if not self.package_rows:
            raise _invalid("the package table must not be empty")
        return self

    @property
    def package_rows(self) -> tuple[ModelDepProvenancePackage, ...]:
        """The package table parsed through the contract's own row pattern."""
        row_pattern = re.compile(self.package_row_pattern)
        rows: list[ModelDepProvenancePackage] = []
        for text in self.packages:
            matched = row_pattern.fullmatch(text)
            if matched is None:
                raise _invalid(f"package row {text!r} does not match its row pattern")
            try:
                shapes = tuple(
                    EnumDepProvenanceShape(shape.strip())
                    for shape in matched.group("shapes").split(self.shape_separator)
                )
            except ValueError as exc:
                raise _invalid(f"package row {text!r}: {exc}") from exc
            rows.append(
                ModelDepProvenancePackage(
                    name=self.normalize(matched.group("package")),
                    repository=matched.group("repository"),
                    shapes=shapes,
                )
            )
        return tuple(rows)

    def normalize(self, name: str) -> str:
        """Canonical package name: the contract's pattern and replacement, lower case."""
        return re.sub(
            self.normalize_pattern,
            self.normalize_replacement,
            name.strip().strip("\"'"),
        ).lower()
