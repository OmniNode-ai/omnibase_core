"""
Detection Rule Metadata Model.

Typed metadata for detection rules that match sensitive information.

This model stores rule-level information (rule_id, rule_name, category)
for detection matches. Not to be confused with ModelDetectionMetadata
in the context module which handles security pattern metadata.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDetectionRuleMetadata"]


class ModelDetectionRuleMetadata(BaseModel):
    """
    Typed metadata for detection rule matches.

    This model captures information about the detection rule that triggered
    a match, including rule identification, categorization, and extensible
    metadata fields.

    Attributes:
        rule_id: Identifier of the detection rule that matched.
        rule_name: Human-readable name of the detection rule.
        category: Category or grouping for the detection.
        source: Source system or component that generated the detection.
        tags: Arbitrary tags for classification.
        extra: Additional string key-value pairs for extensibility.

    Example:
        >>> metadata = ModelDetectionRuleMetadata(
        ...     rule_id="RULE-001",
        ...     rule_name="Credit Card Detection",
        ...     category="PCI",
        ...     tags=["financial", "sensitive"],
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    rule_id: str | None = Field(  # string-id-ok: detection rule identifier
        default=None,
        description="Identifier of the detection rule that matched",
    )

    rule_name: str | None = Field(
        default=None,
        description="Human-readable name of the detection rule",
    )

    category: str | None = Field(
        default=None,
        description="Category or grouping for the detection",
    )

    source: str | None = Field(
        default=None,
        description="Source system or component that generated the detection",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Arbitrary tags for classification",
    )

    extra: dict[str, str] = Field(
        default_factory=dict,
        description="Additional string key-value pairs for extensibility",
    )
