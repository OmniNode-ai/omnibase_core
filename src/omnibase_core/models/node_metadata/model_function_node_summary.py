"""
Function node summary model.

Simplified, focused summary for function nodes.
Reduced from excessive fields to essential summary information.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_action_category import EnumActionCategory
from omnibase_core.enums.enum_conceptual_complexity import EnumConceptualComplexity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_function_status import EnumFunctionStatus
from omnibase_core.enums.enum_return_type import EnumReturnType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.utils.util_uuid_utilities import uuid_from_string


class ModelFunctionNodeSummary(BaseModel):
    """
    Simplified function node summary.

    Focused on essential information for listings and overviews.
    Eliminates redundant fields from the original 19-field summary.
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Essential function info - UUID-based entity references
    function_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the function entity",
    )
    function_display_name: str | None = Field(
        default=None,
        description="Human-readable function name",
    )
    description: str | None = Field(default=None, description="Function description")
    status: EnumFunctionStatus = Field(
        default=EnumFunctionStatus.ACTIVE,
        description="Function status",
    )
    complexity: EnumConceptualComplexity = Field(
        default=EnumConceptualComplexity.BASIC,
        description="Function conceptual complexity level",
    )
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Function version",
    )

    # Function signature summary
    parameter_count: int = Field(default=0, description="Number of parameters")
    return_type: EnumReturnType | None = Field(
        default=None,
        description="Return type annotation",
    )

    # Quality indicators (condensed)
    quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall quality score (0-1)",
    )
    has_documentation: bool = Field(default=False, description="Has documentation")
    has_tests: bool = Field(default=False, description="Has unit tests")

    # Performance summary
    performance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Performance score (0-1)",
    )
    execution_count: int = Field(default=0, description="Number of executions")

    # Timestamps (essential only)
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    # Organization (condensed)
    primary_category: EnumActionCategory | None = Field(
        default=None,
        description="Primary function category",
    )
    tag_count: int = Field(default=0, description="Number of tags")

    def get_status_display(self) -> str:
        """Get human-readable status."""
        return self.status.value.replace("_", " ").title()

    def is_well_documented(self) -> bool:
        """Check if function is well documented."""
        return self.has_documentation and self.quality_score > 0.7

    def is_high_performance(self) -> bool:
        """Check if function has good performance."""
        return self.performance_score > 0.8

    def is_frequently_used(self) -> bool:
        """Check if function is frequently used."""
        return self.execution_count > 100

    @property
    def function_name(self) -> str:
        """Get function name with fallback to UUID-based name."""
        return self.function_display_name or f"function_{str(self.function_id)[:8]}"

    @function_name.setter
    def function_name(self, value: str) -> None:
        """Set function name."""
        self.function_display_name = value

    @classmethod
    def create_from_full_data(
        cls,
        name: str,
        description: str | None,
        status: EnumFunctionStatus,
        complexity: str,
        version: ModelSemVer,
        parameter_count: int,
        return_type: EnumReturnType | None,
        has_documentation: bool,
        has_examples: bool,
        has_type_annotations: bool,
        has_tests: bool,
        tags: list[str],
        categories: list[str],
        dependencies: list[str],
        created_at: datetime | None,
        updated_at: datetime | None,
        last_validated: datetime | None,
        execution_count: int,
        success_rate: float,
        average_execution_time_ms: float,
        memory_usage_mb: float,
        cyclomatic_complexity: int,
        lines_of_code: int,
    ) -> ModelFunctionNodeSummary:
        """Create summary from full function data."""
        # Calculate quality score from available indicators
        quality_score = 0.0
        if has_documentation:
            quality_score += 0.4
        if has_examples:
            quality_score += 0.2
        if has_type_annotations:
            quality_score += 0.2
        if has_tests:
            quality_score += 0.2

        # Calculate performance score
        performance_score = 0.0
        if success_rate > 0:
            performance_score += success_rate * 0.5
        if average_execution_time_ms < 100:
            performance_score += 0.3
        if memory_usage_mb < 10:
            performance_score += 0.2

        # Convert string complexity to enum
        from omnibase_core.enums.enum_conceptual_complexity import (
            EnumConceptualComplexity,
        )

        complexity_enum = (
            EnumConceptualComplexity(complexity)
            if complexity in EnumConceptualComplexity
            else EnumConceptualComplexity.BASIC
        )

        return cls(
            function_id=uuid_from_string(name, "function"),
            function_display_name=name,
            description=description,
            status=status,
            complexity=complexity_enum,
            version=version,
            parameter_count=parameter_count,
            return_type=return_type,
            quality_score=min(quality_score, 1.0),
            has_documentation=has_documentation,
            has_tests=has_tests,
            performance_score=min(performance_score, 1.0),
            execution_count=execution_count,
            updated_at=updated_at,
            primary_category=(
                EnumActionCategory(categories[0])
                if categories and categories[0] in [e.value for e in EnumActionCategory]
                else None
            ),
            tag_count=len(tags),
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as a dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Map actual fields to TypedDictMetadataDict structure
        # function_name property always returns non-empty (has UUID fallback)
        result["name"] = self.function_name
        if self.description:
            result["description"] = self.description
        # version is required field, always present
        result["version"] = self.version
        # Pack additional fields into metadata
        result["metadata"] = {
            "function_id": str(self.function_id),
            "status": self.status.value,
            "complexity": self.complexity.value,
            "parameter_count": self.parameter_count,
            # return_type is optional, use explicit None check
            "return_type": self.return_type.value
            if self.return_type is not None
            else None,
            "quality_score": self.quality_score,
            "has_documentation": self.has_documentation,
            "has_tests": self.has_tests,
            "performance_score": self.performance_score,
            "execution_count": self.execution_count,
            # primary_category is optional, use explicit None check
            "primary_category": (
                self.primary_category.value
                if self.primary_category is not None
                else None
            ),
            "tag_count": self.tag_count,
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from a dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to a dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


__all__ = ["ModelFunctionNodeSummary"]
