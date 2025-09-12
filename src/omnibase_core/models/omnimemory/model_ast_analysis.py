"""
AST analysis models for OmniMemory system.

Represents AST analysis results and code patterns.
"""

from pydantic import BaseModel, Field


class ModelFunctionSignature(BaseModel):
    """Represents a function signature extracted from AST."""

    name: str = Field(..., description="Function name")
    line_number: int = Field(..., description="Line number where function is defined")
    parameters: list[str] = Field(default_factory=list, description="Parameter names")
    return_type: str | None = Field(
        None,
        description="Return type annotation if present",
    )
    is_async: bool = Field(default=False, description="Whether function is async")
    decorators: list[str] = Field(
        default_factory=list,
        description="Applied decorators",
    )


class ModelClassDefinition(BaseModel):
    """Represents a class definition extracted from AST."""

    name: str = Field(..., description="Class name")
    line_number: int = Field(..., description="Line number where class is defined")
    base_classes: list[str] = Field(
        default_factory=list,
        description="Base class names",
    )
    methods: list[str] = Field(
        default_factory=list,
        description="Method names in class",
    )
    attributes: list[str] = Field(default_factory=list, description="Class attributes")
    decorators: list[str] = Field(
        default_factory=list,
        description="Applied decorators",
    )


class ModelImportStatement(BaseModel):
    """Represents an import statement extracted from AST."""

    module: str = Field(..., description="Module being imported")
    names: list[str] = Field(
        default_factory=list,
        description="Names imported from module",
    )
    alias: str | None = Field(None, description="Import alias if present")
    line_number: int = Field(..., description="Line number of import")
    is_from_import: bool = Field(
        default=False,
        description="Whether it's a 'from X import Y' statement",
    )


class ModelTypingViolation(BaseModel):
    """Represents a typing violation found in code."""

    violation_type: str = Field(..., description="Type of violation")
    line_number: int = Field(..., description="Line number of violation")
    column: int = Field(..., description="Column offset of violation")
    message: str = Field(..., description="Violation description")
    severity: str = Field(
        ...,
        description="Severity level (critical, high, medium, low)",
    )
    suggested_fix: str | None = Field(
        None,
        description="Suggested fix for the violation",
    )


class ModelASTCache(BaseModel):
    """Represents cached AST analysis results."""

    file_path: str = Field(..., description="Path to the analyzed file")
    code_hash: str = Field(..., description="Hash of the analyzed code")
    ast_json: str = Field(..., description="Serialized AST representation")
    analysis_timestamp: float = Field(..., description="Unix timestamp of analysis")
