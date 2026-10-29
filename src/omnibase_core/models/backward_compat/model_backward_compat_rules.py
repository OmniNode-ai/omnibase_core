# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule data of the backcompat detector (OMN-21433)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["RULE_IDS", "ModelBackwardCompatRules"]

RULE_IDS = (
    "compat-comment",
    "compat-method",
    "compat-extra-allow",
    "compat-protocol",
    "compat-function-name",
    "compat-docstring",
    "compat-protocol-condition",
)


class ModelBackwardCompatRules(BaseModel):
    """Loaded from ``contracts/backward_compat_rules.yaml``; no rules live in code."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    compatibility_comment_patterns: tuple[str, ...] = Field(min_length=1)
    negative_patterns: tuple[str, ...] = Field(min_length=1)
    compatibility_method_patterns: tuple[str, ...] = Field(min_length=1)
    deprecated_method_pattern: str = Field(min_length=1)
    legitimate_deprecated_methods: tuple[str, ...] = Field(min_length=1)
    extra_allow_same_line_patterns: tuple[str, ...] = Field(min_length=1)
    extra_allow_pattern: str = Field(min_length=1)
    method_name_pattern: str = Field(min_length=1)
    extra_allow_keywords: tuple[str, ...] = Field(min_length=1)
    extra_allow_context_before: int = Field(ge=0)
    extra_allow_context_after: int = Field(ge=0)
    protocol_compat_patterns: tuple[str, ...] = Field(min_length=1)
    function_name_suffixes: tuple[str, ...] = Field(min_length=1)
    docstring_phrases: tuple[str, ...] = Field(min_length=1)
    protocol_condition_keywords: tuple[str, ...] = Field(min_length=1)
    protocol_condition_context_before: int = Field(ge=0)
    protocol_condition_context_after: int = Field(ge=0)
    protocol_startswith_constant: str = Field(min_length=1)
    startswith_method: str = Field(min_length=1)
    dunder_marker: str = Field(min_length=1)
    protocol_import_prefixes: tuple[str, ...] = Field(min_length=1)
    protocol_assignment_marker: str = Field(min_length=1)
    protocol_import_keyword: str = Field(min_length=1)
    architectural_exemptions: dict[str, str]
    skip_dir_parts: tuple[str, ...] = Field(min_length=1)
    max_file_size_bytes: int = Field(ge=1)
    encodings: tuple[str, ...] = Field(min_length=1)
    messages: dict[str, str]
    remediation: str = Field(min_length=1)

    @field_validator("messages")
    @classmethod
    def _messages_cover_every_rule(cls, value: dict[str, str]) -> dict[str, str]:
        missing = sorted(set(RULE_IDS) - set(value))
        if missing:
            raise ValueError(f"messages lack the rule ids {missing}")
        return value
