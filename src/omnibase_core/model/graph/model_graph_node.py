"""
Graph node models for OmniMemory Codebase Graph Integration.

These models represent the nodes in the codebase knowledge graph,
including files, symbols, and documentation nodes.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Union

from pydantic import BaseModel, Field


class ModelGraphNodeBase(BaseModel):
    """Base model for all graph nodes."""

    node_id: str = Field(..., description="Unique identifier for the node (hash-based)")
    node_type: str = Field(..., description="Type of node (file/symbol/documentation)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class ModelFileNode(ModelGraphNodeBase):
    """Represents a file in the codebase graph."""

    file_path: Path = Field(..., description="Absolute file path")
    file_type: str = Field(..., description="Type of file (code/doc/config/test)")
    language: str | None = Field(
        None,
        description="Programming language (python/yaml/markdown)",
    )
    size_bytes: int = Field(0, description="File size in bytes")
    line_count: int = Field(0, description="Number of lines in file")
    content_hash: str = Field(
        ...,
        description="Hash of file content for change detection",
    )
    last_modified: datetime = Field(..., description="Last modification timestamp")

    # OnexTree integration fields
    stamped_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata from stamper",
    )
    tree_validated: bool = Field(
        False,
        description="Whether file structure was validated by OnexTree",
    )

    # Vector embeddings for semantic search
    embedding_vector: list[float] | None = Field(
        None,
        description="Vector representation for semantic search",
    )
    embedding_model: str | None = Field(
        None,
        description="Model used to generate embedding",
    )


class ModelSymbolNode(ModelGraphNodeBase):
    """Represents a code symbol (class/function/variable) in the codebase graph."""

    symbol_name: str = Field(..., description="Name of the symbol")
    symbol_type: str = Field(
        ...,
        description="Type: class/function/variable/constant/import",
    )
    file_node_id: str = Field(..., description="ID of the file containing this symbol")
    line_number: int = Field(..., description="Line number where symbol is defined")
    column_number: int | None = Field(
        None,
        description="Column number where symbol starts",
    )

    # Symbol-specific metadata
    scope: str = Field("module", description="Scope: module/class/function")
    access_modifier: str | None = Field(
        None,
        description="Access modifier: public/private/protected",
    )
    is_exported: bool = Field(False, description="Whether symbol is exported/public")
    docstring: str | None = Field(
        None,
        description="Symbol's docstring if available",
    )

    # Type information
    return_type: str | None = Field(None, description="Return type for functions")
    parameter_types: list[str] = Field(
        default_factory=list,
        description="Parameter types for functions",
    )
    base_classes: list[str] = Field(
        default_factory=list,
        description="Base classes for class symbols",
    )

    # Vector embedding for semantic search
    embedding_vector: list[float] | None = Field(
        None,
        description="Vector representation for semantic search",
    )


class ModelDocumentationNode(ModelGraphNodeBase):
    """Represents documentation in the codebase graph."""

    content: str = Field(..., description="Documentation text content")
    doc_type: str = Field(
        ...,
        description="Type: module/class/function/inline/standalone",
    )
    format_type: str = Field(
        "markdown",
        description="Format: markdown/docstring/comment/rst",
    )

    # Location information
    file_node_id: str | None = Field(
        None,
        description="ID of file containing this documentation",
    )
    line_start: int | None = Field(None, description="Starting line number")
    line_end: int | None = Field(None, description="Ending line number")

    # References to symbols this documentation describes
    documented_symbols: list[str] = Field(
        default_factory=list,
        description="Symbol node IDs this doc describes",
    )

    # Extracted metadata from documentation
    tags: list[str] = Field(
        default_factory=list,
        description="Tags extracted from documentation",
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Code examples in documentation",
    )

    # Vector embedding for semantic search
    embedding_vector: list[float] | None = Field(
        None,
        description="Vector representation for semantic search",
    )
    embedding_model: str | None = Field(
        None,
        description="Model used to generate embedding",
    )


# Union type for all graph nodes
GraphNode = Union[ModelFileNode, ModelSymbolNode, ModelDocumentationNode]
