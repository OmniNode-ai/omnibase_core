"""
Detection Metadata Model.

Typed metadata for sensitive information detection matches.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelDetectionMetadata(BaseModel):
    """
    Typed metadata for detection matches.

    Replaces untyped dict[str, str] with structured fields for common
    detection metadata while preserving flexibility via the extra field.
    """

    rule_id: str | None = Field(
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

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
