"""Model for ONEX pattern exclusion information."""

from pydantic import BaseModel, Field


class ModelPatternExclusionInfo(BaseModel):
    """
    Strongly-typed model for ONEX pattern exclusion information.

    This model represents the exclusion metadata attached to functions,
    methods, or classes that are excluded from specific ONEX pattern
    enforcement.

    Attributes:
        excluded_patterns: Set of pattern names excluded (e.g., 'dict_str_any', 'any_type')
        reason: Justification for the exclusion
        scope: Scope of exclusion ('function', 'class', 'method')
        reviewer: Optional code reviewer who approved the exclusion
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

    model_config = {"frozen": True}
