# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation request wire DTO (graduated from omnibase_compat, OMN-12126)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.delegation.wire.model_budget import ModelBudgetLimits

EnumQualityContractMode = Literal["extend_task_class", "replace_task_class"]

SUPPORTED_ACCEPTANCE_CRITERIA = frozenset(
    {
        "exactly_two_sentences",
        "plain_text_only",
        "response_non_empty",
    }
)
MAX_WORDS_PER_SENTENCE_RE = re.compile(r"^max_words_per_sentence_([1-9]\d*)$")


def validate_acceptance_criteria(criteria: tuple[str, ...]) -> tuple[str, ...]:
    """Validate request-level quality criteria before they enter dispatch."""
    unsupported = [
        item
        for item in criteria
        if item not in SUPPORTED_ACCEPTANCE_CRITERIA
        and not MAX_WORDS_PER_SENTENCE_RE.match(item)
    ]
    if unsupported:
        joined = ", ".join(sorted(unsupported))
        # error-ok: wire DTO boundary check; pydantic model_validator surface, not an OnexError call site
        raise ValueError(f"unsupported acceptance criteria: {joined}")
    return criteria


class ModelDelegationRequest(BaseModel):
    """Delegation command: prompt, task type, source context, and quality contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    prompt: str = Field(
        ..., description="The user prompt to delegate to the local LLM."
    )
    task_type: Literal["test", "document", "research"] = Field(
        ...,
        description="Classification of the delegation task.",
    )
    # string-id-ok: Claude Code session IDs are opaque strings, not UUIDs
    source_session_id: str | None = Field(
        default=None,
        description="Session that originated the delegation request.",
    )
    source_file_path: str | None = Field(
        default=None,
        description="File context for the delegation, if any.",
    )
    correlation_id: UUID = Field(
        ...,
        description="Unique identifier for tracking through the pipeline.",
    )
    max_tokens: int = Field(
        default=2048,
        description="Maximum tokens for the LLM response.",
    )
    emitted_at: datetime = Field(
        ...,
        description="Timestamp when the request was created.",
    )
    output_schema_key: str | None = Field(
        default=None,
        description=(
            "When set, the orchestrator runs the schema-compliance loop: it validates each "
            "inference response against the registry-resolved schema and emits repair prompts "
            "on validation failure. None = legacy single-attempt path."
        ),
    )
    compliance_budget: ModelBudgetLimits | None = Field(
        default=None,
        description=(
            "Budget ceilings (tokens, cost, elapsed time) the compliance loop enforces between "
            "repair attempts. Required when ``output_schema_key`` is set."
        ),
    )
    quality_contract_mode: EnumQualityContractMode = Field(
        default="extend_task_class",
        description="How request-level acceptance criteria interact with task-class DoD.",
    )
    acceptance_criteria: tuple[str, ...] = Field(
        default=(),
        description="Request-level quality checks enforced by the quality gate.",
    )

    @model_validator(mode="after")
    def _validate_compliance_loop_config(self) -> Self:
        if self.output_schema_key is not None and self.compliance_budget is None:
            msg = (
                "compliance_budget is required when output_schema_key is set "
                "(the compliance loop has nothing to evaluate against without "
                "token / cost / time ceilings)"
            )
            raise ValueError(msg)
        validate_acceptance_criteria(self.acceptance_criteria)
        return self


__all__: list[str] = [
    "MAX_WORDS_PER_SENTENCE_RE",
    "SUPPORTED_ACCEPTANCE_CRITERIA",
    "EnumQualityContractMode",
    "ModelDelegationRequest",
    "validate_acceptance_criteria",
]
