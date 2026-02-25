# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelDecisionStoreEntry - Core entry model for the Decision Store.

Represents a single architectural or design decision recorded in the
Decision Store. Supports lineage tracking via supersession references,
alternative options recording, and multi-scope tagging.

.. versionadded:: 0.7.0
    Added as part of Decision Store infrastructure (OMN-2763)
"""

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_decision_type import EnumDecisionType
from omnibase_core.models.store.model_decision_alternative import (
    ModelDecisionAlternative,
)

# Controlled vocabulary for scope_domain.
ALLOWED_DOMAINS: frozenset[str] = frozenset(
    {
        "transport",
        "data-model",
        "auth",
        "api",
        "infra",
        "testing",
        "code-structure",
        "security",
        "observability",
        "custom",
    }
)

# Maximum seconds a created_at timestamp may be ahead of now() before being rejected.
_MAX_FUTURE_SECONDS: int = 300  # 5 minutes


class ModelDecisionStoreEntry(BaseModel):
    """A single recorded decision in the Decision Store.

    Captures the full context of an architectural or design decision,
    including its scope, lineage, alternatives, and current status.

    Attributes:
        decision_id: UUIDv7-compatible identifier (caller-supplied, time-sortable).
        decision_type: Classification of the decision.
        correlation_id: Correlation UUID linking to the initiating context.
        scope_domain: Domain vocabulary term controlling which decisions are grouped.
        scope_services: Pre-normalized sorted tuple of service/repo slugs in scope;
            empty tuple means platform-wide.
        scope_layer: Architectural layer this decision affects.
        status: Lifecycle status of the decision.
        supersedes: Tuple of decision UUIDs this entry supersedes.
        superseded_by: UUID of the decision that supersedes this one, if any.
        rationale: Human-readable explanation for the decision.
        alternatives: Ordered tuple of alternatives considered.
        tags: Tuple of free-form tags for search and filtering.
        source: How this decision was recorded.
        created_at: Timezone-aware creation timestamp; rejected if > 5 min in future.

    Example:
        >>> from datetime import datetime, UTC
        >>> entry = ModelDecisionStoreEntry(
        ...     decision_type=EnumDecisionType.TECH_STACK_CHOICE,
        ...     correlation_id=uuid4(),
        ...     scope_domain="data-model",
        ...     scope_services=("omnibase_core", "omnibase_infra"),
        ...     scope_layer="architecture",
        ...     status="ACTIVE",
        ...     rationale="PostgreSQL selected for JSON indexing and ACID guarantees.",
        ...     alternatives=(
        ...         ModelDecisionAlternative(label="PostgreSQL", status="SELECTED"),
        ...         ModelDecisionAlternative(
        ...             label="MySQL",
        ...             status="REJECTED",
        ...             rejection_reason="Lacks JSON indexing support",
        ...         ),
        ...     ),
        ...     tags=("database", "storage"),
        ...     source="planning",
        ...     created_at=datetime.now(UTC),
        ... )
        >>> entry.scope_domain
        'data-model'

    .. versionadded:: 0.7.0
        Added as part of Decision Store infrastructure (OMN-2763)
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # === Identity ===

    decision_id: UUID = Field(
        default_factory=uuid4,
        description=(
            "UUIDv7-compatible identifier for this decision (caller-supplied, "
            "time-sortable). Defaults to uuid4 when not provided."
        ),
    )

    decision_type: EnumDecisionType = Field(
        ...,
        description="Classification of this decision.",
    )

    correlation_id: UUID = Field(
        ...,
        description="Correlation UUID linking to the initiating context or session.",
    )

    # === Scope ===

    scope_domain: str = Field(
        ...,
        description=(
            f"Domain vocabulary term for grouping decisions. "
            f"Must be one of: {sorted(ALLOWED_DOMAINS)!r}"
        ),
    )

    scope_services: tuple[str, ...] = Field(
        default=(),
        description=(
            "Pre-normalized (sorted, lowercase) repo slugs in scope. "
            "Empty tuple means platform-wide."
        ),
    )

    scope_layer: Literal["architecture", "design", "planning", "implementation"] = (
        Field(
            ...,
            description="Architectural layer this decision affects.",
        )
    )

    # === Lifecycle ===

    status: Literal["PROPOSED", "ACTIVE", "SUPERSEDED", "DEPRECATED"] = Field(
        ...,
        description="Lifecycle status of this decision.",
    )

    supersedes: tuple[UUID, ...] = Field(
        default=(),
        description="UUIDs of decisions this entry supersedes.",
    )

    superseded_by: UUID | None = Field(
        default=None,
        description="UUID of the decision that supersedes this one, if any.",
    )

    # === Content ===

    rationale: str = Field(
        ...,
        min_length=1,
        description="Human-readable explanation for this decision.",
    )

    alternatives: tuple[ModelDecisionAlternative, ...] = Field(
        default=(),
        description="Ordered tuple of alternatives considered for this decision.",
    )

    tags: tuple[str, ...] = Field(
        default=(),
        description="Free-form tags for search and filtering.",
    )

    # === Provenance ===

    source: Literal["planning", "interview", "pr_review", "manual"] = Field(
        ...,
        description="How this decision was recorded.",
    )

    created_at: datetime = Field(
        ...,
        description=(
            "Timezone-aware creation timestamp. "
            "Rejected if more than 5 minutes in the future relative to now()."
        ),
    )

    # === Validators ===

    @field_validator("scope_domain")
    @classmethod
    def validate_scope_domain(cls, v: str) -> str:
        """Validate scope_domain is in the ALLOWED_DOMAINS vocabulary.

        Args:
            v: The domain string to validate.

        Returns:
            The validated domain string.

        Raises:
            ValueError: If the domain is not in ALLOWED_DOMAINS.
        """
        if v not in ALLOWED_DOMAINS:
            raise ValueError(
                f"scope_domain {v!r} is not in the allowed vocabulary. "
                f"Allowed values: {sorted(ALLOWED_DOMAINS)!r}"
            )
        return v

    @field_validator("scope_services", mode="before")
    @classmethod
    def normalize_scope_services(cls, v: object) -> tuple[str, ...]:
        """Normalize scope_services to a sorted tuple of lowercase strings.

        Accepts a sequence of strings, sorts them, and lowercases each slug.

        Args:
            v: The input sequence of service slugs.

        Returns:
            A sorted tuple of lowercase service slugs.

        Raises:
            ValueError: If the input is not a sequence of strings.
        """
        if isinstance(v, (list, tuple)):
            normalized = tuple(sorted(str(s).lower() for s in v))
            return normalized
        raise ValueError(
            f"scope_services must be a list or tuple of strings, got {type(v).__name__!r}"
        )

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, v: datetime) -> datetime:
        """Validate created_at is timezone-aware and not too far in the future.

        Args:
            v: The creation timestamp to validate.

        Returns:
            The validated timezone-aware datetime.

        Raises:
            ValueError: If the timestamp is naive or more than 5 minutes in the future.
        """
        if v.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (tzinfo required)")
        now = datetime.now(UTC)
        if v > now + timedelta(seconds=_MAX_FUTURE_SECONDS):
            raise ValueError(
                f"created_at is more than {_MAX_FUTURE_SECONDS // 60} minutes in the future "
                f"({v.isoformat()} vs now={now.isoformat()})"
            )
        return v

    @model_validator(mode="after")
    def validate_superseded_consistency(self) -> "ModelDecisionStoreEntry":
        """Validate supersession status consistency.

        When status is SUPERSEDED, superseded_by must be set.
        When status is not SUPERSEDED, superseded_by should be None.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If the supersession fields are inconsistent with status.
        """
        if self.status == "SUPERSEDED" and self.superseded_by is None:
            raise ValueError("superseded_by must be set when status is 'SUPERSEDED'")
        if self.status != "SUPERSEDED" and self.superseded_by is not None:
            raise ValueError(
                f"superseded_by must be None when status is {self.status!r}; "
                "only SUPERSEDED entries may reference a superseding decision"
            )
        return self


__all__ = ["ALLOWED_DOMAINS", "ModelDecisionStoreEntry"]
