"""
Model for function discovery information.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelFunctionSignature(BaseModel):
    """Model for a function signature."""

    name: str = Field(..., description="Function name")
    parameters: List[str] = Field(default_factory=list, description="Parameter names")
    return_type: Optional[str] = Field(None, description="Return type annotation")
    is_async: bool = Field(False, description="Whether function is async")
    is_method: bool = Field(False, description="Whether function is a class method")
    line_number: Optional[int] = Field(
        None, description="Line number where function is defined"
    )
    docstring: Optional[str] = Field(None, description="Function docstring")


class ModelClassInfo(BaseModel):
    """Model for class information."""

    name: str = Field(..., description="Class name")
    base_classes: List[str] = Field(
        default_factory=list, description="Base class names"
    )
    methods: List[ModelFunctionSignature] = Field(
        default_factory=list, description="Class methods"
    )
    line_number: Optional[int] = Field(
        None, description="Line number where class is defined"
    )
    docstring: Optional[str] = Field(None, description="Class docstring")


class ModelImportInfo(BaseModel):
    """Model for import information."""

    module: str = Field(..., description="Module name")
    imported_names: List[str] = Field(
        default_factory=list, description="Imported names"
    )
    alias: Optional[str] = Field(None, description="Import alias")
    is_from_import: bool = Field(False, description="Whether this is a 'from' import")


class ModelFunctionDiscovery(BaseModel):
    """Model for function discovery information."""

    # Discovered functions
    functions: List[ModelFunctionSignature] = Field(
        default_factory=list, description="Functions discovered in the file"
    )

    # Discovered classes
    classes: List[ModelClassInfo] = Field(
        default_factory=list, description="Classes discovered in the file"
    )

    # Import analysis
    imports: List[ModelImportInfo] = Field(
        default_factory=list, description="Imports discovered in the file"
    )

    # File statistics
    total_lines: Optional[int] = Field(None, description="Total lines in file")
    code_lines: Optional[int] = Field(None, description="Lines of actual code")
    comment_lines: Optional[int] = Field(None, description="Lines of comments")
    blank_lines: Optional[int] = Field(None, description="Blank lines")

    # Complexity metrics
    cyclomatic_complexity: Optional[int] = Field(
        None, description="Cyclomatic complexity"
    )
    cognitive_complexity: Optional[int] = Field(
        None, description="Cognitive complexity"
    )

    # Discovery metadata
    discovery_tool: Optional[str] = Field(None, description="Tool used for discovery")
    discovery_version: Optional[str] = Field(
        None, description="Version of discovery tool"
    )
    discovery_timestamp: Optional[str] = Field(
        None, description="When discovery was performed"
    )

    # Language-specific information
    language: Optional[str] = Field(None, description="Programming language detected")
    language_version: Optional[str] = Field(
        None, description="Language version if detected"
    )

    # Error handling
    discovery_errors: List[str] = Field(
        default_factory=list, description="Any errors encountered during discovery"
    )

    discovery_warnings: List[str] = Field(
        default_factory=list, description="Any warnings encountered during discovery"
    )
