"""
Graph edge models for OmniMemory Codebase Graph Integration.

These models represent the relationships between nodes in the codebase knowledge graph,
including imports, definitions, references, inheritance, and documentation relationships.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ModelGraphEdge(BaseModel):
    """Represents a directed edge between two nodes in the codebase graph."""

    edge_id: str = Field(..., description="Unique identifier for the edge")
    edge_type: str = Field(..., description="Type of relationship")
    source_node_id: str = Field(..., description="ID of the source node")
    target_node_id: str = Field(..., description="ID of the target node")

    # Edge metadata
    weight: float = Field(1.0, description="Weight/strength of the relationship")
    confidence: float = Field(1.0, description="Confidence in the relationship (0-1)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Context information
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context about the relationship"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModelImportEdge(ModelGraphEdge):
    """Represents an import relationship between files."""

    edge_type: str = Field("import", description="Edge type")
    import_statement: str = Field(..., description="The actual import statement")
    import_type: str = Field(..., description="Type: direct/from/relative/absolute")
    imported_symbols: List[str] = Field(
        default_factory=list, description="Specific symbols imported"
    )
    line_number: int = Field(..., description="Line number of import statement")
    is_conditional: bool = Field(
        False, description="Whether import is inside a conditional"
    )


class ModelDefinitionEdge(ModelGraphEdge):
    """Represents a definition relationship from file to symbol."""

    edge_type: str = Field("defines", description="Edge type")
    definition_type: str = Field(
        ..., description="What type of definition: class/function/variable"
    )
    line_number: int = Field(..., description="Line where symbol is defined")
    scope_level: int = Field(0, description="Nesting level of definition")


class ModelUsageEdge(ModelGraphEdge):
    """Represents usage of one symbol by another."""

    edge_type: str = Field("uses", description="Edge type")
    usage_type: str = Field(
        ..., description="Type: call/reference/assignment/inheritance"
    )
    line_number: int = Field(..., description="Line where usage occurs")
    usage_context: str = Field(..., description="Context of usage")
    frequency: int = Field(1, description="Number of times this usage occurs")


class ModelInheritanceEdge(ModelGraphEdge):
    """Represents class inheritance relationship."""

    edge_type: str = Field("inherits", description="Edge type")
    inheritance_type: str = Field("class", description="Type of inheritance")
    position: int = Field(0, description="Position in inheritance list")
    is_multiple: bool = Field(False, description="Whether this is multiple inheritance")


class ModelCallEdge(ModelGraphEdge):
    """Represents function call relationship."""

    edge_type: str = Field("calls", description="Edge type")
    call_type: str = Field(..., description="Type: direct/method/super/dynamic")
    line_number: int = Field(..., description="Line where call occurs")
    arguments_count: int = Field(0, description="Number of arguments in call")
    is_recursive: bool = Field(False, description="Whether this is a recursive call")


class ModelDocumentationEdge(ModelGraphEdge):
    """Represents documentation relationship."""

    edge_type: str = Field("documents", description="Edge type")
    doc_relationship: str = Field(
        ..., description="Type: docstring/comment/reference/example"
    )
    relevance_score: float = Field(
        1.0, description="Relevance of documentation to symbol"
    )
    line_range: Optional[tuple[int, int]] = Field(
        None, description="Line range of documentation"
    )


class ModelReferenceEdge(ModelGraphEdge):
    """Represents reference relationship from file to documentation."""

    edge_type: str = Field("references", description="Edge type")
    reference_type: str = Field(..., description="Type: inline/external/citation")
    line_number: Optional[int] = Field(None, description="Line where reference occurs")
    reference_context: str = Field(..., description="Context of the reference")


# Union type for all edge types
GraphEdge = Union[
    ModelImportEdge,
    ModelDefinitionEdge,
    ModelUsageEdge,
    ModelInheritanceEdge,
    ModelCallEdge,
    ModelDocumentationEdge,
    ModelReferenceEdge,
    ModelGraphEdge,  # Generic edge for other relationships
]
