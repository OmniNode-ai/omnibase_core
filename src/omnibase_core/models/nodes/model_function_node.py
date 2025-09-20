"""
Function Node Model.

Represents a function/method node with metadata and execution information.
Used for metadata node collections and function documentation.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ...enums.enum_complexity import EnumComplexity
from ...enums.enum_function_status import EnumFunctionStatus
from ...enums.enum_memory_usage import EnumMemoryUsage
from ...enums.enum_runtime_category import EnumRuntimeCategory
from ..core.model_custom_properties import ModelCustomProperties
from ..metadata.model_semver import ModelSemVer
from .model_function_node_summary import ModelFunctionNodeSummary


class ModelFunctionNode(BaseModel):
    """
    Function node model for metadata collections.

    Represents a function or method with its associated metadata,
    parameters, documentation, and execution context.
    """

    # Core function information
    name: str = Field(..., description="Function name")
    description: str = Field(default="", description="Function description")
    function_type: str = Field(
        default="function",
        description="Type of function (function, method, property, etc.)",
    )

    # Function signature
    parameters: list[str] = Field(
        default_factory=list,
        description="Function parameters",
    )
    return_type: str | None = Field(
        default=None,
        description="Function return type annotation",
    )
    parameter_types: dict[str, str] = Field(
        default_factory=dict,
        description="Parameter type annotations",
    )

    # Documentation
    docstring: str | None = Field(default=None, description="Function docstring")
    examples: list[str] = Field(default_factory=list, description="Usage examples")
    notes: list[str] = Field(default_factory=list, description="Additional notes")

    # Metadata
    module: str | None = Field(
        default=None,
        description="Module containing the function",
    )
    file_path: Path | None = Field(default=None, description="Source file path")
    line_number: int | None = Field(
        default=None,
        description="Line number in source file",
        ge=1,
    )

    # Status and versioning
    status: EnumFunctionStatus = Field(
        default=EnumFunctionStatus.ACTIVE,
        description="Function status (active, deprecated, disabled)",
    )
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Function version",
    )
    deprecated_since: str | None = Field(
        default=None,
        description="Version when deprecated",
    )
    replacement: str | None = Field(
        default=None,
        description="Replacement function if deprecated",
    )

    # Performance and usage
    complexity: EnumComplexity = Field(
        default=EnumComplexity.SIMPLE,
        description="Function complexity (simple, moderate, complex)",
    )
    estimated_runtime: EnumRuntimeCategory | None = Field(
        default=None,
        description="Estimated runtime category",
    )
    memory_usage: EnumMemoryUsage | None = Field(
        default=None,
        description="Memory usage category",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )
    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    # Tags and categorization
    tags: list[str] = Field(default_factory=list, description="Function tags")
    categories: list[str] = Field(
        default_factory=list,
        description="Function categories",
    )

    # Custom properties for extensibility
    custom_properties: ModelCustomProperties = Field(
        default_factory=ModelCustomProperties,
        description="Custom properties with type safety",
    )

    # Dependencies and relationships
    dependencies: list[str] = Field(
        default_factory=list,
        description="Function dependencies",
    )
    related_functions: list[str] = Field(
        default_factory=list,
        description="Related functions",
    )

    def is_active(self) -> bool:
        """Check if function is active."""
        return self.status == EnumFunctionStatus.ACTIVE

    def is_disabled(self) -> bool:
        """Check if function is disabled."""
        return self.status == EnumFunctionStatus.DISABLED

    def get_complexity_level(self) -> int:
        """Get numeric complexity level."""
        complexity_map = {
            EnumComplexity.SIMPLE: 1,
            EnumComplexity.MODERATE: 2,
            EnumComplexity.COMPLEX: 3,
            EnumComplexity.VERY_COMPLEX: 4,
        }
        return complexity_map.get(self.complexity, 1)

    def has_documentation(self) -> bool:
        """Check if function has adequate documentation."""
        return bool(self.description and self.docstring)

    def has_examples(self) -> bool:
        """Check if function has usage examples."""
        return len(self.examples) > 0

    def get_parameter_count(self) -> int:
        """Get number of parameters."""
        return len(self.parameters)

    def has_type_annotations(self) -> bool:
        """Check if function has type annotations."""
        return bool(self.return_type or self.parameter_types)

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def add_category(self, category: str) -> None:
        """Add a category if not already present."""
        if category not in self.categories:
            self.categories.append(category)

    def add_example(self, example: str) -> None:
        """Add a usage example."""
        if example not in self.examples:
            self.examples.append(example)

    def add_note(self, note: str) -> None:
        """Add a note."""
        if note not in self.notes:
            self.notes.append(note)

    def mark_disabled(self) -> None:
        """Mark function as disabled."""
        self.status = EnumFunctionStatus.DISABLED
        self.updated_at = datetime.now(UTC)

    def mark_active(self) -> None:
        """Mark function as active."""
        self.status = EnumFunctionStatus.ACTIVE
        self.deprecated_since = None
        self.replacement = None
        self.updated_at = datetime.now(UTC)

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(UTC)

    def validate_function(self) -> None:
        """Mark function as validated."""
        self.last_validated = datetime.now(UTC)

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
        return ModelFunctionNodeSummary(
            name=self.name,
            description=self.description,
            function_type=self.function_type,
            status=self.status,
            complexity=self.complexity,
            version=self.version,
            parameter_count=self.get_parameter_count(),
            return_type=self.return_type,
            has_documentation=self.has_documentation(),
            has_examples=self.has_examples(),
            has_type_annotations=self.has_type_annotations(),
            has_tests=self.has_tests(),
            tags=self.tags,
            categories=self.categories,
            dependencies=self.dependencies,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_validated=self.last_validated,
            execution_count=0,  # Add actual metrics if available
            success_rate=0.0,  # Add actual metrics if available
            average_execution_time_ms=0.0,  # Add actual metrics if available
            memory_usage_mb=0.0,  # Add actual metrics if available
            cyclomatic_complexity=1,  # Add actual complexity calculation if available
            lines_of_code=(
                len(self.implementation.split("\n")) if self.implementation else 0
            ),
        )

    @classmethod
    def create_simple(
        cls,
        name: str,
        description: str = "",
        function_type: str = "function",
    ) -> "ModelFunctionNode":
        """Create a simple function node."""
        return cls(
            name=name,
            description=description,
            function_type=function_type,
        )

    @classmethod
    def create_from_signature(
        cls,
        name: str,
        parameters: list[str],
        return_type: str | None = None,
        description: str = "",
    ) -> "ModelFunctionNode":
        """Create function node from signature information."""
        return cls(
            name=name,
            description=description,
            parameters=parameters,
            return_type=return_type,
        )


# Export for use
__all__ = ["ModelFunctionNode"]
