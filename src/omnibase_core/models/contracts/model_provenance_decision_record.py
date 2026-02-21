# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Decision Provenance Record Model.

Provides the ModelProvenanceDecisionRecord class — the foundational artifact for
the Decision Provenance system (OMN-2350). All subsequent emission, storage,
and dashboard work depends on this schema.

This model captures the complete context needed to audit and reproduce any
decision made by an agent in the ONEX system.

Design Decisions:
    - frozen=True: Immutable after emission — events are facts, not mutable state.
    - agent_rationale is nullable: Rationale is optional/assistive; provenance
      fields (decision_id, timestamp, candidates, etc.) are mandatory.
    - reproducibility_snapshot as dict: Captures runtime state needed to re-derive
      the decision without coupling to any specific runtime type.
    - Separate DecisionScore model: Allows per-candidate breakdown without
      flattening into a single flat structure.
    - No implicit defaults for decision_id or timestamp: Callers must inject these
      values — no auto-generation, no datetime.now() defaults — per repo invariant.

See Also:
    model_provenance_decision_score.py: Per-candidate scoring breakdown.
    OMN-2350: Decision Provenance epic.
    CLAUDE.md: Repository invariants (explicit timestamp injection).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from omnibase_core.models.contracts.model_provenance_decision_score import (
    ModelProvenanceDecisionScore,
)


class ModelProvenanceDecisionRecord(BaseModel):
    """Foundational provenance artifact for an agent decision.

    Captures the complete context of a single decision: what was considered,
    how candidates were scored, what constraints were applied, which candidate
    was selected, and enough state to reproduce or audit the decision later.

    All fields with the exception of tie_breaker and agent_rationale are
    mandatory — callers must supply them explicitly. This design prevents
    silent omissions that would compromise auditability.

    Attributes:
        decision_id: Caller-supplied UUID for this decision. No auto-generation
            — callers must provide a UUID.
        decision_type: Classification string, e.g. "model_select",
            "workflow_route", "tool_pick".
        timestamp: Caller-injected UTC datetime of the decision. No
            datetime.now() default — callers must inject the timestamp.
        candidates_considered: Ordered list of candidate identifiers that
            were evaluated.
        constraints_applied: Key-value mapping of constraint name to its
            applied value (e.g., {"max_cost_usd": "0.05"}).
        scoring_breakdown: Per-candidate scores with individual criterion
            breakdowns. See ModelProvenanceDecisionScore.
        tie_breaker: Optional strategy name used when candidates scored
            equally (e.g., "random", "alphabetical", "cost_ascending").
        selected_candidate: The candidate identifier that was ultimately
            selected.
        agent_rationale: Optional free-text explanation from the agent
            for why this candidate was selected. Assistive only.
        reproducibility_snapshot: Key-value mapping of runtime state needed
            to re-derive or audit this decision (e.g., model versions,
            feature flags, config hashes).

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import UUID
        >>> record = ModelProvenanceDecisionRecord(
        ...     decision_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        ...     decision_type="model_select",
        ...     timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
        ...     candidates_considered=["claude-3-opus", "gpt-4", "gemini-pro"],
        ...     constraints_applied={"max_cost_usd": "0.05", "min_quality": "0.8"},
        ...     scoring_breakdown=[
        ...         ModelProvenanceDecisionScore(
        ...             candidate="claude-3-opus",
        ...             score=0.87,
        ...             breakdown={"quality": 0.45, "speed": 0.25, "cost": 0.17},
        ...         ),
        ...     ],
        ...     tie_breaker=None,
        ...     selected_candidate="claude-3-opus",
        ...     agent_rationale="Selected for highest quality within cost constraint.",
        ...     reproducibility_snapshot={"routing_version": "1.2.3"},
        ... )
        >>> record.selected_candidate
        'claude-3-opus'
        >>> record.decision_type
        'model_select'
    """

    model_config = ConfigDict(
        frozen=True,
        # extra="ignore" intentional: contract/external model — forward-compatible with event bus
        extra="ignore",
        from_attributes=True,
    )

    decision_id: UUID = Field(
        ...,
        description=(
            "Caller-supplied unique identifier (UUID) for this decision. "
            "No auto-generation — callers must provide a UUID."
        ),
    )

    decision_type: str = Field(
        ...,
        min_length=1,
        description=(
            'Classification of the decision. E.g. "model_select", '
            '"workflow_route", "tool_pick".'
        ),
    )

    timestamp: datetime = Field(
        ...,
        description=(
            "Caller-injected UTC datetime of the decision. "
            "No datetime.now() default — callers must inject the timestamp."
        ),
    )

    candidates_considered: list[Annotated[str, StringConstraints(min_length=1)]] = (
        Field(
            ...,
            description=(
                "Ordered list of candidate identifiers that were evaluated. "
                "Each element must be a non-empty string (min_length=1)."
            ),
        )
    )

    constraints_applied: dict[str, str] = Field(
        ...,
        description=(
            "Key-value mapping of constraint name to its applied value "
            '(e.g., {"max_cost_usd": "0.05"}).'
        ),
    )

    scoring_breakdown: list[ModelProvenanceDecisionScore] = Field(
        ...,
        description="Per-candidate scores with individual criterion breakdowns.",
    )

    tie_breaker: str | None = Field(
        default=None,
        description=(
            "Optional strategy name used when candidates scored equally "
            '(e.g., "random", "alphabetical", "cost_ascending").'
        ),
    )

    selected_candidate: str = Field(
        ...,
        min_length=1,
        description="The candidate identifier that was ultimately selected.",
    )

    agent_rationale: str | None = Field(
        default=None,
        description=(
            "Optional free-text explanation from the agent for why this "
            "candidate was selected. Assistive only."
        ),
    )

    reproducibility_snapshot: dict[str, str] = Field(
        ...,
        description=(
            "Key-value mapping of runtime state needed to re-derive or audit "
            "this decision (e.g., model versions, feature flags, config hashes)."
        ),
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (use UTC)")
        return v

    @model_validator(mode="after")
    def validate_selected_candidate_in_candidates(
        self,
    ) -> ModelProvenanceDecisionRecord:
        """Cross-validate selected_candidate and scoring_breakdown against candidates_considered.

        When candidates_considered is empty, all cross-validation against it is
        skipped — EXCEPT when scoring_breakdown is non-empty. A non-empty
        scoring_breakdown alongside an empty candidates_considered is logically
        inconsistent: there can be no scored candidates if none were considered.

        Checks:
            - If candidates_considered is empty and scoring_breakdown is non-empty,
              raises ValueError (logically inconsistent state).
            - selected_candidate must be present in candidates_considered (when
              candidates_considered is non-empty).
            - Every score.candidate in scoring_breakdown must be present in
              candidates_considered (when candidates_considered is non-empty).
        """
        if not self.candidates_considered:
            if self.scoring_breakdown:
                raise ValueError(
                    "scoring_breakdown must be empty when candidates_considered is empty: "
                    f"found {len(self.scoring_breakdown)} scoring entry/entries but no "
                    "candidates were recorded. Either populate candidates_considered or "
                    "clear scoring_breakdown."
                )
            return self
        if self.selected_candidate not in self.candidates_considered:
            raise ValueError(
                f"selected_candidate '{self.selected_candidate}' must be present "
                "in candidates_considered"
            )
        for score in self.scoring_breakdown:
            if score.candidate not in self.candidates_considered:
                raise ValueError(
                    f"scoring_breakdown candidate '{score.candidate}' must be present "
                    "in candidates_considered"
                )
        return self


# Public alias for API surface
DecisionRecord = ModelProvenanceDecisionRecord

__all__ = ["DecisionRecord", "ModelProvenanceDecisionRecord"]
