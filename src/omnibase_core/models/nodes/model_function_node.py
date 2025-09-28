"""
Function Node Model.

Represents a function/method node with metadata and execution information.
Used for metadata node collections and function documentation.

Restructured to use composition of focused sub-models instead of
excessive string fields in a single large model.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    Identifiable,
    MetadataProvider,
    Serializable,
    Validatable,
)
from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.enums.enum_function_status import EnumFunctionStatus
from omnibase_core.enums.enum_operational_complexity import EnumOperationalComplexity
from omnibase_core.enums.enum_return_type import EnumReturnType

from .model_function_node_core import ModelFunctionNodeCore
from .model_function_node_metadata import ModelFunctionNodeMetadata
from .model_function_node_performance import ModelFunctionNodePerformance
from .model_function_node_summary import ModelFunctionNodeSummary


class ModelFunctionNode(BaseModel):
    """
    Function node model for metadata collections.

    Restructured to use composition of focused sub-models:
    - core: Essential function information and signature
    - metadata: Documentation, tags, and organizational info
    - performance: Performance metrics and complexity analysis
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Composed sub-models for focused concerns
    core: ModelFunctionNodeCore = Field(
        ...,
        description="Core function information",
    )
    metadata: ModelFunctionNodeMetadata = Field(
        default_factory=lambda: ModelFunctionNodeMetadata(),
        description="Documentation and metadata",
    )
    performance: ModelFunctionNodePerformance = Field(
        default_factory=lambda: ModelFunctionNodePerformance(),
        description="Performance and complexity metrics",
    )

    # Direct access properties
    @property
    def name(self) -> str:
        """Get function name from core."""
        return self.core.name

    @property
    def description(self) -> str:
        """Get description from core."""
        return self.core.description

    @property
    def status(self) -> EnumFunctionStatus:
        """Get status from core."""
        return self.core.status

    @property
    def parameters(self) -> list[str]:
        """Get parameters from core."""
        return self.core.parameters

    @property
    def complexity(self) -> EnumOperationalComplexity:
        """Get complexity from performance."""
        return self.performance.complexity

    @property
    def tags(self) -> list[str]:
        """Get tags from metadata."""
        return self.metadata.tags

    # Delegate methods to appropriate sub-models
    def is_active(self) -> bool:
        """Check if function is active."""
        return self.core.is_active()

    def is_disabled(self) -> bool:
        """Check if function is disabled."""
        return self.core.is_disabled()

    def get_complexity_level(self) -> int:
        """Get numeric complexity level."""
        return self.performance.get_complexity_level()

    def has_documentation(self) -> bool:
        """Check if function has adequate documentation."""
        return self.metadata.has_documentation()

    def has_examples(self) -> bool:
        """Check if function has usage examples."""
        return self.metadata.has_examples()

    def get_parameter_count(self) -> int:
        """Get number of parameters."""
        return self.core.get_parameter_count()

    def has_type_annotations(self) -> bool:
        """Check if function has type annotations."""
        return self.core.has_type_annotations()

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        self.metadata.add_tag(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        self.metadata.remove_tag(tag)

    def add_category(self, category: EnumCategory) -> None:
        """Add a category if not already present."""
        self.metadata.add_category(category)

    def add_example(self, example: str) -> None:
        """Add a usage example."""
        self.metadata.add_example(example)

    def add_note(self, note: str) -> None:
        """Add a note."""
        self.metadata.add_note(note)

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.metadata.update_timestamp()

    def validate_function(self) -> None:
        """Mark function as validated."""
        self.metadata.mark_validated()

    def record_execution(
        self,
        success: bool,
        execution_time_ms: float,
        memory_used_mb: float = 0.0,
    ) -> None:
        """Record a function execution."""
        self.performance.record_execution(success, execution_time_ms, memory_used_mb)

    def has_tests(self) -> bool:
        """Check if function has tests (placeholder implementation)."""
        # TODO: Implement actual test detection logic
        return False

    @property
    def implementation(self) -> str:
        """Get function implementation (placeholder)."""
        # TODO: Implement actual function source code retrieval
        return ""

    def to_summary(self) -> ModelFunctionNodeSummary:
        """Get function summary with clean typing."""
        return ModelFunctionNodeSummary.create_from_full_data(
            name=self.name,
            description=self.description,
            status=EnumFunctionStatus(self.status),
            complexity=self.complexity,
            version=self.core.version,
            parameter_count=self.get_parameter_count(),
            return_type=self.core.return_type,
            has_documentation=self.has_documentation(),
            has_examples=self.has_examples(),
            has_type_annotations=self.has_type_annotations(),
            has_tests=self.has_tests(),
            tags=self.tags,
            categories=[cat.value for cat in self.metadata.categories],
            dependencies=[str(dep) for dep in self.metadata.relationships.dependencies],
            created_at=self.metadata.created_at,
            updated_at=self.metadata.updated_at,
            last_validated=self.metadata.last_validated,
            execution_count=self.performance.execution_count,
            success_rate=self.performance.success_rate,
            average_execution_time_ms=self.performance.average_execution_time_ms,
            memory_usage_mb=self.performance.memory_usage_mb,
            cyclomatic_complexity=self.performance.cyclomatic_complexity,
            lines_of_code=self.performance.lines_of_code,
        )

    @classmethod
    def create_simple(
        cls,
        name: str,
        description: str = "",
        function_type: str = "function",
    ) -> ModelFunctionNode:
        """Create a simple function node."""
        # Import the enum to convert string to enum
        from omnibase_core.enums.enum_function_type import EnumFunctionType

        # Convert string to enum for type safety
        try:
            function_type_enum = EnumFunctionType(function_type.upper())
        except ValueError:
            function_type_enum = EnumFunctionType.TRANSFORM  # Default fallback

        core = ModelFunctionNodeCore.create_simple(
            name,
            description,
            function_type_enum,
        )
        return cls(core=core)

    @classmethod
    def create_from_signature(
        cls,
        name: str,
        parameters: list[str],
        return_type: str | None = None,
        description: str = "",
    ) -> ModelFunctionNode:
        """Create function node from signature information."""
        # Import the enum to convert string to enum

        # Convert string to enum for type safety
        return_type_enum = None
        if return_type is not None:
            try:
                return_type_enum = EnumReturnType(return_type.upper())
            except ValueError:
                return_type_enum = EnumReturnType.UNKNOWN  # Default fallback

        core = ModelFunctionNodeCore.create_from_signature(
            name,
            parameters,
            return_type_enum,
            description,
        )
        return cls(core=core)

    @classmethod
    def create_documented(
        cls,
        name: str,
        description: str,
        docstring: str,
        examples: list[str] | None = None,
    ) -> ModelFunctionNode:
        """Create function node with documentation."""
        core = ModelFunctionNodeCore.create_simple(name, description)
        metadata = ModelFunctionNodeMetadata.create_documented(docstring, examples)
        return cls(core=core, metadata=metadata)

    @classmethod
    def create_with_performance(
        cls,
        name: str,
        description: str = "",
        performance: ModelFunctionNodePerformance | None = None,
    ) -> ModelFunctionNode:
        """Create function node with performance profile."""
        core = ModelFunctionNodeCore.create_simple(name, description)
        return cls(
            core=core,
            performance=performance or ModelFunctionNodePerformance(),
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
        return f"{self.__class__.__name__}_{id(self)}"

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dictionary (MetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dictionary (MetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelFunctionNode"]
