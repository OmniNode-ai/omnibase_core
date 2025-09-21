"""
Function Node Model.

Represents a function/method node with metadata and execution information.
Used for metadata node collections and function documentation.

Restructured to use composition of focused sub-models instead of
excessive string fields in a single large model.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

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
    """

    # Composed sub-models for focused concerns
    core: ModelFunctionNodeCore = Field(
        ...,
        description="Core function information",
    )
    metadata: ModelFunctionNodeMetadata = Field(
        default_factory=ModelFunctionNodeMetadata,
        description="Documentation and metadata",
    )
    performance: ModelFunctionNodePerformance = Field(
        default_factory=ModelFunctionNodePerformance,
        description="Performance and complexity metrics",
    )

    # Backward compatibility properties
    @property
    def name(self) -> str:
        """Get function name from core."""
        return self.core.name

    @property
    def description(self) -> str:
        """Get description from core."""
        return self.core.description

    @property
    def status(self):
        """Get status from core."""
        return self.core.status

    @property
    def parameters(self) -> list[str]:
        """Get parameters from core."""
        return self.core.parameters

    @property
    def complexity(self):
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

    def add_category(self, category: str) -> None:
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
            status=self.status,
            complexity=str(self.complexity.value),
            version=self.core.version,
            parameter_count=self.get_parameter_count(),
            return_type=self.core.return_type,
            has_documentation=self.has_documentation(),
            has_examples=self.has_examples(),
            has_type_annotations=self.has_type_annotations(),
            has_tests=self.has_tests(),
            tags=self.tags,
            categories=self.metadata.categories,
            dependencies=self.metadata.dependencies,
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
        core = ModelFunctionNodeCore.create_simple(name, description, function_type)
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
        core = ModelFunctionNodeCore.create_from_signature(
            name, parameters, return_type, description
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


# Export for use
__all__ = ["ModelFunctionNode"]
