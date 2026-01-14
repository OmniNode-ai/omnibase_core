"""
Structured Description Model.

Provides consistent description patterns across metadata models.
Reduces reliance on free-form description strings with standardized templates.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_standard_category import EnumStandardCategory
from omnibase_core.enums.enum_standard_tag import EnumStandardTag
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.utils.util_uuid_utilities import uuid_from_string


class ModelStructuredDescription(BaseModel):
    """
    Structured description with standardized templates and patterns.

    Replaces free-form description strings with structured components
    that provide better consistency and information architecture.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identity
    description_id: UUID = Field(
        default_factory=lambda: uuid_from_string("default", "description"),
        description="Unique identifier for this description",
    )

    # Core description components
    purpose: str = Field(
        default=...,
        description="Primary purpose or function of the entity",
        max_length=200,
    )

    functionality: str | None = Field(
        default=None,
        description="Detailed functionality description",
        max_length=500,
    )

    context: str | None = Field(
        default=None,
        description="Context or scope of usage",
        max_length=300,
    )

    # Structured metadata
    category: EnumStandardCategory | None = Field(
        default=None,
        description="Primary category for context",
    )

    complexity_level: EnumStandardTag | None = Field(
        default=None,
        description="Complexity indicator",
    )

    # Usage information
    use_cases: list[str] = Field(
        default_factory=list,
        description="Common use cases",
    )

    prerequisites: list[str] = Field(
        default_factory=list,
        description="Prerequisites or dependencies",
    )

    outputs: list[str] = Field(
        default_factory=list,
        description="Expected outputs or results",
    )

    # Quality and constraints
    constraints: list[str] = Field(
        default_factory=list,
        description="Constraints or limitations",
    )

    performance_notes: str | None = Field(
        default=None,
        description="Performance characteristics",
        max_length=200,
    )

    # Template-based properties
    is_template_based: bool = Field(
        default=False,
        description="Whether this uses a standardized template",
    )

    template_version: ModelSemVer | None = Field(
        default=None,
        description="Template version if template-based",
    )

    @property
    def full_description(self) -> str:
        """Generate complete description from structured components."""
        components = [self.purpose]

        if self.functionality:
            components.append(f"Functionality: {self.functionality}")

        if self.context:
            components.append(f"Context: {self.context}")

        if self.use_cases:
            use_cases_text = ", ".join(self.use_cases)
            components.append(f"Use cases: {use_cases_text}")

        if self.prerequisites:
            prereq_text = ", ".join(self.prerequisites)
            components.append(f"Prerequisites: {prereq_text}")

        if self.constraints:
            constraints_text = ", ".join(self.constraints)
            components.append(f"Constraints: {constraints_text}")

        if self.performance_notes:
            components.append(f"Performance: {self.performance_notes}")

        return ". ".join(components) + "."

    @property
    def summary_description(self) -> str:
        """Get concise summary description."""
        base = self.purpose
        if self.category:
            base = f"{self.category.value.title()} - {base}"
        return base

    @property
    def detailed_description(self) -> str:
        """Get detailed description with all components."""
        return self.full_description

    @classmethod
    def from_plain_text(
        cls,
        description: str,
        category: EnumStandardCategory | None = None,
    ) -> ModelStructuredDescription:
        """Create structured description from plain text string."""
        return cls(
            description_id=uuid_from_string(description[:50], "description"),
            purpose=description,
            category=category,
            is_template_based=False,
        )

    @classmethod
    def for_metadata_node(
        cls,
        name: str,
        functionality: str | None = None,
        category: EnumStandardCategory | None = None,
    ) -> ModelStructuredDescription:
        """Create description for metadata nodes."""
        purpose = f"Metadata node for {name} with structured information tracking"

        return cls(
            description_id=uuid_from_string(f"metadata_node_{name}", "description"),
            purpose=purpose,
            functionality=functionality or f"Manages metadata for {name} entities",
            context="Metadata collection and node management",
            category=category or EnumStandardCategory.DATA_PROCESSING,
            complexity_level=EnumStandardTag.MODERATE,
            use_cases=[
                "Metadata tracking",
                "Node information management",
                "Collection organization",
            ],
            outputs=[
                "Structured metadata",
                "Node relationships",
                "Usage metrics",
            ],
            is_template_based=True,
            template_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    @classmethod
    def for_function_node(
        cls,
        name: str,
        functionality: str | None = None,
        category: EnumStandardCategory | None = None,
    ) -> ModelStructuredDescription:
        """Create description for function nodes."""
        purpose = f"Function node implementing {name} business logic"

        return cls(
            description_id=uuid_from_string(f"function_{name}", "description"),
            purpose=purpose,
            functionality=functionality
            or f"Executes {name} operations with proper error handling",
            context="Business logic execution and data processing",
            category=category or EnumStandardCategory.BUSINESS_LOGIC,
            complexity_level=EnumStandardTag.MODERATE,
            use_cases=[
                "Business logic execution",
                "Data transformation",
                "Process orchestration",
            ],
            prerequisites=[
                "Valid input data",
                "Proper configuration",
            ],
            outputs=[
                "Processed results",
                "Execution metrics",
                "Error information",
            ],
            performance_notes="Optimized for low latency execution",
            is_template_based=True,
            template_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    @classmethod
    def for_analytics_summary(
        cls,
        collection_name: str,
        metrics_included: list[str] | None = None,
    ) -> ModelStructuredDescription:
        """Create description for analytics summaries."""
        purpose = f"Analytics summary for {collection_name} with comprehensive metrics"

        return cls(
            description_id=uuid_from_string(
                f"analytics_{collection_name}",
                "description",
            ),
            purpose=purpose,
            functionality="Aggregates and summarizes collection performance metrics",
            context="Performance monitoring and analytics reporting",
            category=EnumStandardCategory.ANALYTICS,
            complexity_level=EnumStandardTag.SIMPLE,
            use_cases=[
                "Performance monitoring",
                "Health assessment",
                "Trend analysis",
            ],
            outputs=[
                "Aggregated metrics",
                "Health scores",
                "Performance indicators",
            ],
            performance_notes="Lightweight aggregation with minimal overhead",
            is_template_based=True,
            template_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    @classmethod
    def for_usage_metrics(
        cls,
        entity_name: str,
    ) -> ModelStructuredDescription:
        """Create description for usage metrics."""
        purpose = (
            f"Usage metrics tracking for {entity_name} with comprehensive statistics"
        )

        return cls(
            description_id=uuid_from_string(f"metrics_{entity_name}", "description"),
            purpose=purpose,
            functionality="Tracks invocation patterns, success rates, and performance metrics",
            context="Runtime monitoring and usage analysis",
            category=EnumStandardCategory.MONITORING,
            complexity_level=EnumStandardTag.SIMPLE,
            use_cases=[
                "Usage tracking",
                "Performance analysis",
                "Capacity planning",
            ],
            outputs=[
                "Invocation counts",
                "Success rates",
                "Performance statistics",
            ],
            constraints=[
                "Real-time updates",
                "Minimal performance impact",
            ],
            performance_notes="Optimized for high-frequency updates",
            is_template_based=True,
            template_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    @classmethod
    def for_configuration(
        cls,
        config_name: str,
        purpose_detail: str | None = None,
    ) -> ModelStructuredDescription:
        """Create description for configuration objects."""
        purpose = purpose_detail or f"Configuration settings for {config_name}"

        return cls(
            description_id=uuid_from_string(f"config_{config_name}", "description"),
            purpose=purpose,
            functionality="Manages configuration parameters with validation and defaults",
            context="System configuration and parameter management",
            category=EnumStandardCategory.CONFIGURATION,
            complexity_level=EnumStandardTag.SIMPLE,
            use_cases=[
                "Parameter configuration",
                "Setting management",
                "Environment adaptation",
            ],
            prerequisites=[
                "Valid configuration schema",
                "Proper validation rules",
            ],
            outputs=[
                "Validated settings",
                "Default values",
                "Configuration state",
            ],
            constraints=[
                "Schema compliance",
                "Type safety",
            ],
            is_template_based=True,
            template_version=ModelSemVer(major=1, minor=0, patch=0),
        )

    def add_use_case(self, use_case: str) -> bool:
        """Add a use case if not already present and within limits."""
        if use_case not in self.use_cases and len(self.use_cases) < 5:
            self.use_cases.append(use_case)
            return True
        return False

    def add_prerequisite(self, prerequisite: str) -> bool:
        """Add a prerequisite if not already present and within limits."""
        if prerequisite not in self.prerequisites and len(self.prerequisites) < 5:
            self.prerequisites.append(prerequisite)
            return True
        return False

    def add_constraint(self, constraint: str) -> bool:
        """Add a constraint if not already present and within limits."""
        if constraint not in self.constraints and len(self.constraints) < 3:
            self.constraints.append(constraint)
            return True
        return False

    def update_functionality(self, functionality: str) -> None:
        """Update the functionality description."""
        self.functionality = functionality

    def update_performance_notes(self, notes: str) -> None:
        """Update performance notes."""
        self.performance_notes = notes

    def __str__(self) -> str:
        """String representation returns the summary description."""
        return self.summary_description

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # summary_description always returns non-empty string (includes required purpose)
        result["description"] = self.summary_description
        if self.template_version is not None:
            result["version"] = self.template_version
        return result

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
__all__ = ["ModelStructuredDescription"]
