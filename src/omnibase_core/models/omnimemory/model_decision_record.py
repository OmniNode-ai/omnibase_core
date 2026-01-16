"""
ModelDecisionRecord - Record of a single agent decision with context.

Defines the ModelDecisionRecord model which represents a single agent
decision with full context for analysis and replay. Each record tracks
the options considered, chosen option, confidence level, and outcome.

This is a pure data model with no side effects.

.. versionadded:: 0.6.0
    Added as part of OmniMemory decision tracking infrastructure (OMN-1241)
"""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_decision_type import EnumDecisionType
from omnibase_core.utils.util_validators import ensure_timezone_aware


class ModelDecisionRecord(BaseModel):
    """Record of a single agent decision with context.

    Tracks a single decision made by an agent, including all options
    that were considered, the chosen option, confidence level, and
    eventual outcome for analysis and replay.

    Attributes:
        decision_id: Unique identifier for this decision (auto-generated).
        decision_type: Classification of the decision type.
        timestamp: When the decision was made.
        options_considered: Tuple of options that were considered.
        chosen_option: The selected option.
        confidence: Confidence level in the decision (0.0-1.0).
        rationale: Optional explanation for the decision.
        input_hash: Hash of input for replay matching.
        cost_impact: Optional cost impact of this decision.
        outcome: Optional outcome of the decision (success/failure/unknown).

    Example:
        >>> from datetime import datetime, UTC
        >>> from omnibase_core.enums.enum_decision_type import EnumDecisionType
        >>> record = ModelDecisionRecord(
        ...     decision_type=EnumDecisionType.MODEL_SELECTION,
        ...     timestamp=datetime.now(UTC),
        ...     options_considered=("gpt-4", "claude-3-opus", "llama-2-70b"),
        ...     chosen_option="gpt-4",
        ...     confidence=0.85,
        ...     input_hash="abc123",
        ... )
        >>> record.confidence
        0.85

    .. versionadded:: 0.6.0
        Added as part of OmniMemory decision tracking infrastructure (OMN-1241)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Required Fields ===

    decision_id: UUID = Field(
        default_factory=uuid4,
        description="Unique decision identifier",
    )

    decision_type: EnumDecisionType = Field(
        ...,
        description="Type of decision made",
    )

    timestamp: datetime = Field(
        ...,
        description="When the decision was made",
    )

    # === Decision Details ===

    options_considered: tuple[str, ...] = Field(
        ...,
        description="Options that were considered",
    )

    chosen_option: str = Field(
        ...,
        min_length=1,
        description="The selected option",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the decision (0.0-1.0)",
    )

    rationale: str | None = Field(
        default=None,
        description="Explanation for the decision",
    )

    # === Context ===

    input_hash: str = Field(
        ...,
        min_length=1,
        description="Hash of input for replay matching",
    )

    cost_impact: float | None = Field(
        default=None,
        description="Cost impact of this decision",
    )

    # === Outcome (filled later) ===

    outcome: Literal["success", "failure", "unknown"] | None = Field(
        default=None,
        description="Decision outcome",
    )

    # === Validators ===

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_has_timezone(cls, v: datetime) -> datetime:
        """Validate timestamp is timezone-aware using shared utility."""
        return ensure_timezone_aware(v, "timestamp")

    @model_validator(mode="after")
    def validate_chosen_option_in_options(self) -> "ModelDecisionRecord":
        """Ensure chosen_option is in options_considered when options are provided.

        If options_considered is non-empty, chosen_option must be one of
        the considered options. If options_considered is empty (e.g., for
        decisions where options weren't explicitly enumerated), any
        chosen_option is allowed.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If chosen_option is not in a non-empty options_considered.
        """
        if (
            self.options_considered
            and self.chosen_option not in self.options_considered
        ):
            raise ValueError(
                f"chosen_option '{self.chosen_option}' must be in options_considered "
                f"{self.options_considered}. "
                "If options were not explicitly enumerated, use an empty tuple."
            )
        return self

    # === Utility Methods ===

    def __str__(self) -> str:
        return (
            f"DecisionRecord({self.decision_type.value}: "
            f"chose '{self.chosen_option}' with {self.confidence:.0%} confidence)"
        )

    def __repr__(self) -> str:
        return (
            f"ModelDecisionRecord(decision_id={self.decision_id!r}, "
            f"decision_type={self.decision_type!r}, "
            f"chosen_option={self.chosen_option!r}, "
            f"confidence={self.confidence!r}, "
            f"outcome={self.outcome!r})"
        )


# Export for use
__all__ = ["ModelDecisionRecord"]
