"""
Transformation Config Model

Structured model for refactoring transformation configuration.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EnumTransformationType(str, Enum):
    """Types of code transformations."""

    rename = "rename"
    extract_method = "extract_method"
    inline_method = "inline_method"
    move_class = "move_class"
    extract_class = "extract_class"
    refactor_imports = "refactor_imports"
    modernize_syntax = "modernize_syntax"
    optimize_performance = "optimize_performance"


class EnumTransformationScope(str, Enum):
    """Scope of transformations."""

    file = "file"
    module = "module"
    package = "package"
    project = "project"


class ModelTransformationConfig(BaseModel):
    """
    Structured transformation configuration model.

    Replaces Dict[str, Any] usage with proper typing for
    refactoring transformation configuration.
    """

    # Core transformation settings
    transformation_type: EnumTransformationType = Field(
        ...,
        description="Type of transformation to apply",
    )
    scope: EnumTransformationScope = Field(
        default=EnumTransformationScope.file,
        description="Scope of transformation",
    )
    preserve_comments: bool = Field(
        default=True,
        description="Preserve code comments during transformation",
    )
    preserve_formatting: bool = Field(
        default=True,
        description="Preserve code formatting where possible",
    )

    # Safety settings
    create_backup: bool = Field(
        default=True,
        description="Create backup files before transformation",
    )
    validate_syntax: bool = Field(
        default=True,
        description="Validate syntax after transformation",
    )
    run_tests: bool = Field(default=False, description="Run tests after transformation")

    # Transformation-specific parameters
    old_name: str | None = Field(None, description="Old name for rename operations")
    new_name: str | None = Field(None, description="New name for rename operations")
    target_module: str | None = Field(
        None,
        description="Target module for move operations",
    )
    method_lines: list[int] | None = Field(
        None,
        description="Line numbers for method extraction",
    )

    # Advanced options
    excluded_patterns: list[str] = Field(
        default_factory=list,
        description="File patterns to exclude",
    )
    included_patterns: list[str] = Field(
        default_factory=list,
        description="File patterns to include",
    )
    custom_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Custom transformation rules",
    )
