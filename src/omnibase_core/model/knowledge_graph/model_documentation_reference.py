"""
Documentation reference model for linking entities to documentation.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelDocumentationReference(BaseModel):
    """Model for documentation references linked to entities."""

    doc_path: str = Field(..., description="Path to documentation file")
    section_title: Optional[str] = Field(None, description="Section or heading title")
    paragraph_number: Optional[int] = Field(
        None, description="Paragraph number in section"
    )
    line_numbers: Optional[str] = Field(
        None, description="Line number range (e.g., '15-23')"
    )
    link_type: str = Field(
        ..., description="Type of link (defines, references, explains, etc.)"
    )
    confidence_score: float = Field(..., description="Confidence in the link (0.0-1.0)")

    model_config = ConfigDict(frozen=True, validate_assignment=True)
