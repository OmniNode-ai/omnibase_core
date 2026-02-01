"""
Function Node Model.

Represents a function/method node with metadata and execution information.
Used for metadata node collections and function documentation.

Restructured to use composition of focused sub-models instead of
excessive string fields in a single large model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_function_status import EnumFunctionStatus
from omnibase_core.enums.enum_operational_complexity import EnumOperationalComplexity
from omnibase_core.enums.enum_return_type import EnumReturnType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

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
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Composed sub-models for focused concerns
    core: ModelFunctionNodeCore = Field(
        default=...,
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

    def has_tests(self) -> bool:  # stub-ok - Tracked in issue #47
        """
        Check if function has tests.

        Raises:
            NotImplementedError: This method requires implementation of test
                detection logic. See GitHub issue #47 for implementation requirements:
                - AST parsing of test files
                - Test name pattern matching
                - Support for multiple test frameworks (pytest, unittest, etc.)
                - Caching mechanism for performance

        Note:
            Current stub implementation to prevent silent failures.
            Implementation tracked in GitHub issue #47.
        """
        msg = (
            "Test detection not yet implemented. "
            "This requires AST parsing of test files and pattern matching. "
            "See GitHub issue #47 for implementation details."
        )
        raise NotImplementedError(msg)  # stub-ok: Tracked in issue #47

    @property
    def implementation(self) -> str:  # stub-ok - Tracked in issue #49
        """
        Get function implementation source code.

        Raises:
            NotImplementedError: This property requires implementation of source
                code retrieval. See GitHub issue #49 for implementation requirements:
                - Use inspect.getsource() as primary method
                - Fall back to AST parsing if needed
                - Store source file path and line numbers in model
                - Handle edge cases (built-ins, C extensions, etc.)

        Note:
            Current stub implementation to prevent silent failures.
            Implementation tracked in GitHub issue #49.
        """
        msg = (
            "Source code retrieval not yet implemented. "
            "This requires AST parsing or inspect module integration. "
            "See GitHub issue #49 for implementation details."
        )
        raise NotImplementedError(msg)  # stub-ok: Tracked in issue #49

    def to_summary(self) -> ModelFunctionNodeSummary:
        """Get function summary with clean typing."""
        # Handle NotImplementedError from has_tests() gracefully
        # See GitHub issue #47 for test detection implementation
        try:
            has_tests_value = self.has_tests()
        except NotImplementedError:
            has_tests_value = False

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
            has_tests=has_tests_value,
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
        function_type: str = "transform",
    ) -> ModelFunctionNode:
        """Create a simple function node."""
        # Import the enum to convert string to enum
        from omnibase_core.enums.enum_function_type import EnumFunctionType

        # Convert string to enum for type safety
        try:
            function_type_enum = EnumFunctionType(function_type)
        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid function type '{function_type}' for EnumFunctionType. "
                f"Must be one of {[t.value for t in EnumFunctionType]}.",
            ) from e

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

        # Convert string to enum for type safety (normalize to uppercase first)
        return_type_enum = None
        if return_type is not None:
            try:
                # Normalize return_type to uppercase before enum conversion
                normalized_return_type = (
                    return_type.upper() if return_type else "UNKNOWN"
                )
                return_type_enum = EnumReturnType(normalized_return_type)
            except ValueError as e:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid return type '{return_type}' for EnumReturnType. "
                    f"Must be one of {[t.value for t in EnumReturnType]}.",
                ) from e

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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Check core.function_id first for ModelFunctionNode
        if hasattr(self, "core") and hasattr(self.core, "function_id"):
            if self.core.function_id is not None:
                return str(self.core.function_id)

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
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Map actual fields to TypedDictMetadataDict structure via delegated properties
        # name property always returns non-empty (has UUID fallback via core.name)
        result["name"] = self.name
        if self.description:
            result["description"] = self.description
        if self.tags:
            result["tags"] = self.tags
        # Pack additional fields into metadata
        # Convert list[str] to list for JsonType compatibility
        result["metadata"] = {
            "function_id": str(self.core.function_id),
            "status": self.status.value,
            "complexity": self.complexity.value,
            "parameters": list(self.parameters),
            "is_active": self.is_active(),
            "has_documentation": self.has_documentation(),
            "has_examples": self.has_examples(),
            "has_type_annotations": self.has_type_annotations(),
            "parameter_count": self.get_parameter_count(),
            "complexity_level": self.get_complexity_level(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelFunctionNode"]
