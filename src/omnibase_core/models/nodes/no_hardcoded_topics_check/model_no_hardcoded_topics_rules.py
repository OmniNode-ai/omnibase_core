# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule data of the no-hardcoded-topics check (OMN-21518).

Loaded from the rule rows of ``validation/contracts/no_hardcoded_topics.validation.yaml``;
never written as code.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelNoHardcodedTopicsRules"]


class ModelNoHardcodedTopicsRules(BaseModel):
    """The patterns, name lists, thresholds and message of the topic-literal decision."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    validator_name: str = Field(min_length=1)
    topic_literal_pattern: str = Field(min_length=1)
    message: str = Field(min_length=1)
    remediation: str = Field(min_length=1)
    approved_basenames: frozenset[str] = Field(min_length=1)
    test_dir_marker: str = Field(min_length=1)
    test_name_prefix: str = Field(min_length=1)
    test_name_suffixes: tuple[str, ...] = Field(min_length=1)
    wire_schema_dir: str = Field(min_length=1)
    wire_schema_name_pattern: str = Field(min_length=1)
    wire_schema_min_parts: int = Field(ge=1)
    comment_prefixes: tuple[str, ...] = Field(min_length=1)
    block_comment_open: str = Field(min_length=1)
    block_comment_close: str = Field(min_length=1)
    docstring_delimiters: tuple[str, ...] = Field(min_length=1)
