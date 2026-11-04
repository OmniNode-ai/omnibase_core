# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed rule-row parameters for section 4's hard stops."""

from pydantic import BaseModel, ConfigDict, Field


class ModelErrorRulePolicy(BaseModel):
    """All policy values come from the validator's reviewed contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    registered_actions: tuple[str, ...] = Field(min_length=1)
    forbidden_capabilities: tuple[str, ...] = Field(min_length=1)
    allowed_targets: tuple[str, ...] = Field(min_length=1)
    scope_marker: tuple[str, ...] = Field(min_length=1)
    modes: tuple[str, ...] = Field(min_length=1)
    trigger_kinds: tuple[str, ...] = Field(min_length=1)
    break_classes: tuple[str, ...] = Field(min_length=1)
    subject_kinds: tuple[str, ...] = Field(min_length=1)
    source_pattern: str
    source_pointer_pattern: str
    terminal_kind: str
    shadow_mode: str
    dispatch_mode: str
    needs_source: str
    state_trigger: str
    backlog_action: str
    pr_subject: str
    measurement_writer: str
    registry_env: str
    sources_env: str
    measurements_env: str
    modes_env: str
    source_record_types: tuple[str, ...] = Field(min_length=1)
    terminal_prefix: str
    message: str
