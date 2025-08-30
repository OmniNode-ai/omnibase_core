"""
Relationship evidence model for supporting relationship claims.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EnumEvidenceType(str, Enum):
    """Types of evidence supporting relationships."""

    # Textual evidence
    EXPLICIT_MENTION = "explicit_mention"
    IMPLICIT_REFERENCE = "implicit_reference"
    CONTEXTUAL_PROXIMITY = "contextual_proximity"
    SEMANTIC_SIMILARITY = "semantic_similarity"

    # Structural evidence
    CODE_STRUCTURE = "code_structure"
    IMPORT_STATEMENT = "import_statement"
    FUNCTION_CALL = "function_call"
    CLASS_INHERITANCE = "class_inheritance"

    # Documentation evidence
    CROSS_REFERENCE = "cross_reference"
    SHARED_DOCUMENTATION = "shared_documentation"
    EXAMPLE_USAGE = "example_usage"

    # Behavioral evidence
    EXECUTION_TRACE = "execution_trace"
    USAGE_PATTERN = "usage_pattern"
    CONFIGURATION_LINK = "configuration_link"


class ModelRelationshipEvidence(BaseModel):
    """Model for evidence supporting a relationship."""

    evidence_type: EnumEvidenceType = Field(..., description="Type of evidence")
    source_location: str = Field(..., description="Where evidence was found")
    evidence_text: str = Field(..., description="Actual evidence content")
    confidence_contribution: float = Field(
        ...,
        description="How much this evidence contributes to confidence (0.0-1.0)",
    )
    line_number: int = Field(0, description="Line number where evidence was found")
    extraction_method: str = Field(
        ...,
        description="Method used to extract this evidence",
    )

    model_config = ConfigDict(frozen=True, validate_assignment=True)
