# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The patterns and remediation text of the internal sibling pin check (OMN-21518)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelInternalSiblingPinsRules"]


class ModelInternalSiblingPinsRules(BaseModel):
    """Rule data read from the rows of ``internal_sibling_pins.validation.yaml``.

    Attributes:
        name_pattern: Captures the distribution name at the head of a requirement.
        sha_pattern: A git ref that is a commit sha.
        release_tag_pattern: A git ref that is a release tag such as ``v0.47.48``.
        exact_pattern: An exact ``==`` or ``===`` version clause with no wildcard.
        git_url_pattern: A ``git+`` direct URL with ``url`` and optional ``ref`` groups.
        remediation: The remediation text every finding carries.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name_pattern: str = Field(min_length=1)
    sha_pattern: str = Field(min_length=1)
    release_tag_pattern: str = Field(min_length=1)
    exact_pattern: str = Field(min_length=1)
    git_url_pattern: str = Field(min_length=1)
    remediation: str = Field(min_length=1)

    @field_validator(
        "name_pattern",
        "sha_pattern",
        "release_tag_pattern",
        "exact_pattern",
        "git_url_pattern",
    )
    @classmethod
    def _compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"pattern {value!r} does not compile: {exc}") from exc
        return value
