"""Model for ONEX pattern exclusion information."""

from pydantic import BaseModel, ConfigDict, Field


class ModelPatternExclusionInfo(BaseModel):
    """
    Strongly-typed model for ONEX pattern exclusion information.

    This model represents the exclusion metadata attached to functions,
    methods, or classes that are excluded from specific ONEX pattern
    enforcement. It provides a structured way to document why certain
    code elements are exempt from pattern rules.

    This model is immutable (frozen=True) after creation, making it safe
    for use as dictionary keys and in thread-safe contexts.

    Attributes:
        excluded_patterns: Set of pattern names excluded from enforcement
            (e.g., 'dict_str_any', 'any_type').
        reason: Justification for the exclusion, explaining why the pattern
            cannot be followed in this specific case.
        scope: Scope of exclusion - 'function', 'class', or 'method'.
        reviewer: Optional code reviewer who approved the exclusion for
            audit trail purposes.
    """

    excluded_patterns: set[str] = Field(
        default_factory=set,
        description="Set of pattern names excluded from enforcement",
    )
    reason: str = Field(
        default="No reason provided",
        description="Justification for the exclusion",
    )
    scope: str = Field(
        default="function",
        description="Scope of exclusion: 'function', 'class', or 'method'",
    )
    reviewer: str | None = Field(
        default=None,
        description="Optional code reviewer who approved the exclusion",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
