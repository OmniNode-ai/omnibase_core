# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Git and parsing policy supplied by the validator contract."""

from pydantic import BaseModel, ConfigDict, Field


class ModelDevTagLineagePolicy(BaseModel):
    """Every configurable git argument, name and pattern is explicit request data."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    tag_pattern: str
    suffix_pattern: str
    commit_pattern: str
    normalize_pattern: str
    declaration_pattern: str
    declaration_tables: tuple[str, ...] = Field(min_length=1)
    project_name: str
    lock_name: str
    branch: str
    git_binary: str = Field(min_length=1)
    timeout_seconds: int = Field(gt=0, strict=True)
    tag_ref: str
    branch_ref: str
    peeled_suffix: str
    complete_history_value: str
    init_arguments: tuple[str, ...] = Field(min_length=1)
    remote_arguments: tuple[str, ...] = Field(min_length=1)
    fetch_arguments: tuple[str, ...] = Field(min_length=1)
    peel_arguments: tuple[str, ...] = Field(min_length=1)
    shallow_arguments: tuple[str, ...] = Field(min_length=1)
    ancestor_arguments: tuple[str, ...] = Field(min_length=1)
    show_arguments: tuple[str, ...] = Field(min_length=1)
