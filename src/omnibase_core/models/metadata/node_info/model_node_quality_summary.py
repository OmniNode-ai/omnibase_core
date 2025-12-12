from __future__ import annotations

from pydantic import Field

"""
Node Quality Summary Model.

Structured quality summary data for nodes.
Follows ONEX one-model-per-file architecture.
"""


from pydantic import BaseModel

from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelNodeQualitySummary(BaseModel):
    """
    Structured quality summary for nodes.

    Replaces primitive soup unions with typed fields.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Documentation status
    has_documentation: bool = Field(description="Whether node has documentation")
    has_examples: bool = Field(description="Whether node has examples")

    # Quality levels (string categories)
    documentation_quality: str = Field(description="Documentation quality level")
    quality_level: str = Field(description="Overall quality level category")

    # Computed metrics
    quality_score: float = Field(description="Numeric quality score")

    # Boolean indicators
    is_well_documented: bool = Field(description="Whether node is well documented")
    needs_documentation: bool = Field(description="Whether node needs documentation")

    # Improvement suggestions
    improvement_suggestions: list[str] = Field(
        default_factory=list,
        description="List of quality improvement suggestions",
    )

    @property
    def has_improvement_suggestions(self) -> bool:
        """Check if there are improvement suggestions available."""
        return len(self.improvement_suggestions) > 0

    @property
    def suggestion_count(self) -> int:
        """Get the number of improvement suggestions."""
        return len(self.improvement_suggestions)

    def get_overall_quality_status(self) -> str:
        """Get overall quality status based on multiple indicators."""
        if self.is_well_documented and not self.needs_documentation:
            return "Excellent"
        if self.has_documentation and not self.needs_documentation:
            return "Good"
        if self.has_documentation and self.needs_documentation:
            return "Fair"
        return "Poor"

    def get_priority_improvements(self) -> list[str]:
        """Get the most critical improvement suggestions."""
        # Return up to 3 most important suggestions
        return self.improvement_suggestions[:3]

    @classmethod
    def create_summary(
        cls,
        has_documentation: bool,
        has_examples: bool,
        documentation_quality: str,
        quality_score: float,
        quality_level: str,
        is_well_documented: bool,
        needs_documentation: bool,
        improvement_suggestions: list[str],
    ) -> ModelNodeQualitySummary:
        """Create a quality summary with all required data."""
        return cls(
            has_documentation=has_documentation,
            has_examples=has_examples,
            documentation_quality=documentation_quality,
            quality_score=quality_score,
            quality_level=quality_level,
            is_well_documented=is_well_documented,
            needs_documentation=needs_documentation,
            improvement_suggestions=improvement_suggestions,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata  # type: ignore[return-value]

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If metadata setting logic fails
        """
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelNodeQualitySummary"]
