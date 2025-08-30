"""
Relationship type model for categorizing semantic connections.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EnumRelationshipType(str, Enum):
    """Enumeration of semantic relationship types."""

    # Documentation relationships
    DOCUMENTS = "documents"
    EXPLAINS = "explains"
    REFERENCES = "references"
    EXEMPLIFIES = "exemplifies"
    TUTORIAL_FOR = "tutorial_for"

    # Code relationships
    IMPLEMENTS = "implements"
    USES = "uses"
    DEPENDS_ON = "depends_on"
    EXTENDS = "extends"
    CALLS = "calls"
    DEFINES = "defines"
    CONFIGURES = "configures"

    # Conceptual relationships
    IS_A = "is_a"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    REQUIRES = "requires"
    ENABLES = "enables"

    # Workflow relationships
    TRIGGERS = "triggers"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    VALIDATES = "validates"
    TESTS = "tests"

    # Business relationships
    SUPPORTS = "supports"
    FULFILLS = "fulfills"
    CONSTRAINS = "constrains"
    CONFLICTS_WITH = "conflicts_with"


class ModelRelationshipType(BaseModel):
    """Model for relationship type with additional metadata."""

    type_enum: EnumRelationshipType = Field(
        ...,
        description="Primary relationship type",
    )
    category: str = Field(..., description="High-level category grouping")
    is_directional: bool = Field(True, description="Whether relationship has direction")
    semantic_distance: float = Field(
        1.0,
        description="Semantic distance (lower = closer)",
    )
    importance_weight: float = Field(1.0, description="Importance weighting factor")

    model_config = ConfigDict(frozen=True, validate_assignment=True)
