"""
Function Node Model.

Unified model that supports both core domain (dict-based parameters) and nodes domain
(list-based function signatures). Represents a function/method node with metadata,
parameters, documentation, and execution information.
"""

from datetime import UTC, datetime
from typing import Any, Union

from pydantic import BaseModel, Field, field_validator


class ModelFunctionNode(BaseModel):
    """
    Function node model for metadata collections.

    Unified implementation that supports both core domain usage (configuration-style
    parameters as dict) and nodes domain usage (function signature parameters as list).
    Represents a function or method with its associated metadata, parameters,
    documentation, and execution context.
    """

    # Core function information
    name: str = Field(..., description="Function name")
    description: str = Field(default="", description="Function description")
    function_type: str = Field(
        default="function",
        description="Type of function (function, method, property, etc.)",
    )

    # Hybrid parameters field - supports both dict and list patterns
    parameters: Union[list[str], dict[str, Any]] = Field(
        default_factory=list,
        description="Function parameters (list for signatures, dict for configuration)"
    )
    return_type: str | None = Field(
        default=None, description="Function return type annotation"
    )
    parameter_types: dict[str, str] = Field(
        default_factory=dict, description="Parameter type annotations"
    )

    # Documentation
    docstring: str | None = Field(default=None, description="Function docstring")
    examples: list[str] = Field(default_factory=list, description="Usage examples")
    notes: list[str] = Field(default_factory=list, description="Additional notes")

    # Metadata and source information
    module: str | None = Field(
        default=None, description="Module containing the function"
    )
    file_path: str | None = Field(default=None, description="Source file path")
    line_number: int | None = Field(
        default=None, description="Line number in source file", ge=1
    )

    # Status and versioning
    status: str = Field(
        default="active", description="Function status (active, deprecated, disabled)"
    )
    version: str = Field(default="1.0.0", description="Function version")
    deprecated_since: str | None = Field(
        default=None, description="Version when deprecated"
    )
    replacement: str | None = Field(
        default=None, description="Replacement function if deprecated"
    )

    # Performance and usage
    complexity: str = Field(
        default="simple", description="Function complexity (simple, moderate, complex)"
    )
    estimated_runtime: str | None = Field(
        default=None, description="Estimated runtime category (fast, medium, slow)"
    )
    memory_usage: str | None = Field(
        default=None, description="Memory usage category (low, medium, high)"
    )

    # Execution information (for backward compatibility)
    async_execution: bool = Field(False, description="Whether function is async")
    timeout_seconds: int | None = Field(None, description="Execution timeout")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )
    last_validated: datetime | None = Field(
        default=None, description="Last validation timestamp"
    )

    # Tags and categorization (support both category and categories)
    tags: list[str] = Field(default_factory=list, description="Function tags")
    categories: list[str] = Field(
        default_factory=list, description="Function categories"
    )
    category: str = Field(default="general", description="Primary function category")

    # Custom metadata for extensibility (includes HEAD version metadata field)
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional function metadata"
    )

    # Dependencies and relationships
    dependencies: list[str] = Field(
        default_factory=list, description="Function dependencies"
    )
    related_functions: list[str] = Field(
        default_factory=list, description="Related functions"
    )

    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: Union[list[str], dict[str, Any]]) -> Union[list[str], dict[str, Any]]:
        """Validate parameters field supports both list and dict."""
        if isinstance(v, (list, dict)):
            return v
        raise ValueError("Parameters must be either a list or dict")

    # Core domain compatibility methods
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation (HEAD version compatibility)."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelFunctionNode":
        """Create from dictionary representation (HEAD version compatibility)."""
        return cls(**data)

    # Parameters conversion utilities
    def get_parameters_as_list(self) -> list[str]:
        """Get parameters as list (for function signatures)."""
        if isinstance(self.parameters, list):
            return self.parameters
        elif isinstance(self.parameters, dict):
            return list(self.parameters.keys())
        return []

    def get_parameters_as_dict(self) -> dict[str, Any]:
        """Get parameters as dict (for configuration)."""
        if isinstance(self.parameters, dict):
            return self.parameters
        elif isinstance(self.parameters, list):
            return {param: None for param in self.parameters}
        return {}

    def set_parameters_from_list(self, params: list[str]) -> None:
        """Set parameters from list format."""
        self.parameters = params
        self.update_timestamp()

    def set_parameters_from_dict(self, params: dict[str, Any]) -> None:
        """Set parameters from dict format."""
        self.parameters = params
        self.update_timestamp()

    # Status and utility methods
    def is_active(self) -> bool:
        """Check if function is active."""
        return self.status == "active"

    def is_disabled(self) -> bool:
        """Check if function is disabled."""
        return self.status == "disabled"

    def get_complexity_level(self) -> int:
        """Get numeric complexity level."""
        complexity_map = {
            "simple": 1,
            "moderate": 2,
            "complex": 3,
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
        params = self.get_parameters_as_list()
        return len(params)

    def has_type_annotations(self) -> bool:
        """Check if function has type annotations."""
        return bool(self.return_type or self.parameter_types)

    # Manipulation methods
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
        self.status = "disabled"
        self.updated_at = datetime.now(UTC)

    def mark_active(self) -> None:
        """Mark function as active."""
        self.status = "active"
        self.deprecated_since = None
        self.replacement = None
        self.updated_at = datetime.now(UTC)

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(UTC)

    def validate_function(self) -> None:
        """Mark function as validated."""
        self.last_validated = datetime.now(UTC)

    def to_summary(self) -> dict[str, Any]:
        """Get function summary for quick overview."""
        return {
            "name": self.name,
            "description": self.description,
            "function_type": self.function_type,
            "status": self.status,
            "complexity": self.complexity,
            "parameter_count": self.get_parameter_count(),
            "has_documentation": self.has_documentation(),
            "has_examples": self.has_examples(),
            "has_type_annotations": self.has_type_annotations(),
            "tags": self.tags,
            "categories": self.categories,
            "category": self.category,
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
        }

    # Factory methods for different use cases
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
        """Create function node from signature information (nodes domain)."""
        return cls(
            name=name,
            description=description,
            parameters=parameters,
            return_type=return_type,
        )

    @classmethod
    def create_from_config(
        cls,
        name: str,
        parameters: dict[str, Any],
        description: str = "",
        category: str = "general",
    ) -> "ModelFunctionNode":
        """Create function node from configuration (core domain)."""
        return cls(
            name=name,
            description=description,
            parameters=parameters,
            category=category,
        )


# Export for use
__all__ = ["ModelFunctionNode"]
