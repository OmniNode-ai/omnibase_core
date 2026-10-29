# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The merge-queue parity rule data the handler judges with (OMN-21518)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelMergeQueueParityRules"]


class ModelMergeQueueParityRules(BaseModel):
    """Trigger names, patterns, bounds and wording read from the rule rows.

    Loaded from ``merge_queue_parity.validation.yaml`` by
    ``checker_workflow_selection.load_parity_rules``; the handler holds no rule
    data of its own.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    queue_event: str = Field(min_length=1, description="Merge queue trigger name")
    pull_request_event: str = Field(
        min_length=1, description="Pull request event the queue is compared against"
    )
    pull_request_events: tuple[str, ...] = Field(
        description="Triggers that count as pull request CI"
    )
    path_filter_keys: tuple[str, ...] = Field(
        description="Trigger keys that filter a pull request run by path"
    )
    event_atom_pattern: str = Field(
        min_length=1, description="Atom comparing github.event_name to a string"
    )
    draft_atom_pattern: str = Field(
        min_length=1, description="Atom reading the pull request draft flag"
    )
    needs_output_pattern: str = Field(
        min_length=1, description="Reference to a needed job's output"
    )
    event_name_pattern: str = Field(
        min_length=1, description="Any read of github.event_name"
    )
    max_unknowns: int = Field(
        ge=0, description="Most unknown atoms a condition may hold before it is skipped"
    )
    remediation: str = Field(min_length=1, description="Fix carried by every finding")
    finding_template: str = Field(min_length=1, description="Finding message")
    baselined_template: str = Field(
        min_length=1, description="Baselined finding prefix"
    )
    stale_template: str = Field(
        min_length=1, description="Stale baseline entry message"
    )
    no_pull_request_trigger_message: str = Field(min_length=1)
    pull_request_path_filter_message: str = Field(min_length=1)
    merge_queue_only_if_message: str = Field(min_length=1)
    event_dependent_gate_message: str = Field(min_length=1)
