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
    - Shallow-freeze limitation: scoring_breakdown is a frozen list of frozen
      ModelProvenanceDecisionScore objects (frozen=True on the score model). The
      list reference itself is immutable via frozen=True on this record. However,
      the breakdown dict *inside* each score is enforced as a read-only
      MappingProxyType by ModelProvenanceDecisionScore's field_validator
      validate_breakdown_keys, which returns types.MappingProxyType(v) after key
      validation — Pydantic v2 stores the validator return value directly, so no
      frozen bypass is needed. In-place mutation of breakdown raises TypeError.
      Nested container contents beyond that level are not additionally frozen.
    - constraints_applied and reproducibility_snapshot as MappingProxyType: Both
      dict fields follow the same pattern as breakdown in ModelProvenanceDecisionScore.
      Their field_validators (validate_constraints_applied_keys and
      validate_reproducibility_snapshot_keys) return types.MappingProxyType(v) after
      key validation, so Pydantic v2 stores the read-only proxy directly. In-place
      mutation of either field raises TypeError.

See Also:
    model_provenance_decision_score.py: Per-candidate scoring breakdown.
    OMN-2350: Decision Provenance epic.
    CLAUDE.md: Repository invariants (explicit timestamp injection).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from omnibase_core.enums.enum_decision_type import EnumDecisionType
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
        decision_type: Enum classification of the decision. E.g.
            EnumDecisionType.MODEL_SELECTION, EnumDecisionType.ROUTE_CHOICE,
            EnumDecisionType.TOOL_SELECTION. String values are coerced to the
            enum member automatically by Pydantic.
        timestamp: Caller-injected UTC datetime of the decision. No
            datetime.now() default — callers must inject the timestamp.
        candidates_considered: Ordered list of candidate identifiers that
            were evaluated.
        constraints_applied: Key-value mapping of constraint name to its
            applied value (e.g., {"max_cost_usd": "0.05"}). Stored as a
            read-only MappingProxyType after construction; in-place mutation
            raises TypeError.
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
            feature flags, config hashes). Stored as a read-only
            MappingProxyType after construction; in-place mutation raises
            TypeError.

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import UUID
        >>> record = ModelProvenanceDecisionRecord(
        ...     decision_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        ...     decision_type="model_selection",
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
        <EnumDecisionType.MODEL_SELECTION: 'model_selection'>
    """

    model_config = ConfigDict(
        frozen=True,
        # extra="ignore" intentional: contract/external model — forward-compatible with event bus
        extra="ignore",
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    decision_id: UUID = Field(
        ...,
        description=(
            "Caller-supplied unique identifier (UUID) for this decision. "
            "No auto-generation — callers must provide a UUID."
        ),
    )

    decision_type: EnumDecisionType = Field(
        ...,
        description=(
            "Enum classification of the decision. E.g. "
            '"model_selection", "route_choice", "tool_selection", "custom". '
            "String values matching a valid EnumDecisionType member are "
            "coerced automatically by Pydantic."
        ),
    )

    timestamp: datetime = Field(
        ...,
        description=(
            "Caller-injected UTC-aware datetime of the decision. "
            "Must be timezone-aware with a UTC offset of zero. "
            "No datetime.now() default — callers must inject the timestamp."
        ),
    )

    candidates_considered: list[Annotated[str, StringConstraints(min_length=1)]] = (
        Field(
            ...,
            description=(
                "Ordered list of candidate identifiers that were evaluated. "
                "Each element must be a non-empty string (min_length=1). "
                "Uniqueness is intentionally not enforced: duplicate identifiers "
                "are accepted so that the provenance record faithfully reflects "
                "whatever candidate list was supplied by the caller (e.g. a "
                "deliberate re-evaluation of the same candidate under different "
                "constraints). Callers that require unique identifiers must "
                "deduplicate before constructing this record."
            ),
        )
    )

    # Values are intentionally constrained to str for cross-process wire-format
    # stability — numeric or structured values must be serialized as strings by
    # callers before constructing this record.
    constraints_applied: Mapping[str, str] = Field(
        ...,
        description=(
            "Read-only mapping of constraint name to its applied value "
            '(e.g., {"max_cost_usd": "0.05"}). '
            "All values are strings by design: the record faithfully captures the "
            "constraint specification as declared (which may be a threshold, flag, "
            "or enum label). Callers must stringify numeric values before constructing "
            "this record (e.g., str(0.05) → '0.05'). This avoids lossy numeric "
            "coercions and keeps the schema homogeneous for downstream serialization. "
            "Stored as an immutable MappingProxyType to prevent in-place mutation."
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
            '(e.g., "random", "alphabetical", "cost_ascending"). '
            "When provided, must be a non-empty string (min_length=1); "
            "use None to indicate no tie-breaking was applied."
        ),
    )

    selected_candidate: str = Field(
        ...,
        min_length=1,
        description=(
            "The candidate identifier that was ultimately selected. "
            "When candidates_considered is non-empty, this field is "
            "cross-validated to ensure the value is present in that list. "
            "When candidates_considered is empty (bootstrapped or "
            "single-candidate scenarios), this field is unconstrained — "
            "any non-empty string is accepted without cross-validation."
        ),
    )

    agent_rationale: str | None = Field(
        default=None,
        description=(
            "Optional free-text explanation from the agent for why this "
            "candidate was selected. Assistive only. "
            "When provided, must be a non-empty string (min_length=1); "
            "use None to omit the rationale entirely."
        ),
    )

    # Values are intentionally constrained to str for cross-process wire-format
    # stability — numeric or structured values must be serialized as strings by
    # callers before constructing this record.
    reproducibility_snapshot: Mapping[str, str] = Field(
        ...,
        description=(
            "Read-only mapping of runtime state needed to re-derive or audit "
            "this decision (e.g., model versions, feature flags, config hashes). "
            "Stored as an immutable MappingProxyType to prevent in-place mutation."
        ),
    )

    @field_validator("constraints_applied", mode="before")
    @classmethod
    def validate_constraints_applied_keys(cls, v: object) -> object:
        """Validate that all constraints_applied keys and values are non-empty strings."""
        if isinstance(v, MappingProxyType):
            mapping: Mapping[str, str] = v
        elif isinstance(v, dict):
            mapping = v
        else:
            # Let Pydantic produce its own type error for non-mapping inputs.
            return v
        for key, value in mapping.items():
            if not key:
                raise ValueError(
                    "constraints_applied keys must be non-empty strings; "
                    "found an empty string key"
                )
            if not value:
                raise ValueError(
                    "constraints_applied values must be non-empty strings; "
                    f"found an empty string value for key '{key}'"
                )
        return v

    @field_validator("constraints_applied", mode="after")
    @classmethod
    def validate_constraints_applied_immutable(
        cls, v: Mapping[str, str]
    ) -> MappingProxyType[str, str]:
        """Wrap the validated mapping in MappingProxyType to prevent in-place mutation."""
        if isinstance(v, MappingProxyType):
            return v
        return MappingProxyType(dict(v))

    @field_validator("reproducibility_snapshot", mode="before")
    @classmethod
    def validate_reproducibility_snapshot_keys(cls, v: object) -> object:
        """Validate that all reproducibility_snapshot keys and values are non-empty strings."""
        if isinstance(v, MappingProxyType):
            snapshot: Mapping[str, str] = v
        elif isinstance(v, dict):
            snapshot = v
        else:
            # Let Pydantic produce its own type error for non-mapping inputs.
            return v
        for key, value in snapshot.items():
            if not key:
                raise ValueError(
                    "reproducibility_snapshot keys must be non-empty strings; "
                    "found an empty string key"
                )
            if not value:
                raise ValueError(
                    "reproducibility_snapshot values must be non-empty strings; "
                    f"found an empty string value for key '{key}'"
                )
        return v

    @field_validator("reproducibility_snapshot", mode="after")
    @classmethod
    def validate_reproducibility_snapshot_immutable(
        cls, v: Mapping[str, str]
    ) -> MappingProxyType[str, str]:
        """Wrap the validated mapping in MappingProxyType to prevent in-place mutation."""
        if isinstance(v, MappingProxyType):
            return v
        return MappingProxyType(dict(v))

    @field_validator("tie_breaker")
    @classmethod
    def validate_tie_breaker_not_empty(cls, v: str | None) -> str | None:
        if v is not None and len(v) == 0:
            raise ValueError(
                "tie_breaker must be a non-empty string when provided; "
                "use None to indicate no tie-breaking was applied"
            )
        return v

    @field_validator("agent_rationale")
    @classmethod
    def validate_agent_rationale_not_empty(cls, v: str | None) -> str | None:
        if v is not None and len(v) == 0:
            raise ValueError(
                "agent_rationale must be a non-empty string when provided; "
                "use None to omit the rationale entirely"
            )
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("timestamp must be a timezone-aware UTC datetime")
        if v.utcoffset() != timedelta(0):
            raise ValueError(
                "timestamp must be UTC; got non-UTC timezone-aware datetime"
            )
        return v

    @model_validator(mode="after")
    def validate_selected_candidate_in_candidates(
        self,
    ) -> Self:
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

        Note — partial scoring_breakdown is intentional by design:
            This validator does NOT require that every candidate in
            candidates_considered has a corresponding entry in
            scoring_breakdown. Partial coverage is valid because some
            candidates may be eliminated before scoring (e.g. filtered out
            by a pre-screen step), and recording a score for them would be
            misleading. Callers that require full coverage must enforce that
            invariant themselves before constructing this record.
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
        # candidates_considered intentionally permits duplicate identifiers (see field
        # description). If a scoring_breakdown key appears multiple times in
        # candidates_considered, all occurrences are valid per that design — this
        # validator only checks membership, not uniqueness.
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
