"""
Model for work characteristics.

Characteristics used to classify work items.
"""

from pydantic import BaseModel, Field


class ModelWorkCharacteristics(BaseModel):
    """Characteristics used to classify work."""

    has_clear_requirements: bool = Field(
        ..., description="Requirements are well-defined"
    )
    has_test_coverage: bool = Field(..., description="Tests exist or can be generated")
    affects_critical_path: bool = Field(
        ..., description="Impacts critical system components"
    )
    requires_design_decisions: bool = Field(
        ..., description="Needs architectural choices"
    )
    has_external_dependencies: bool = Field(
        ..., description="Depends on external systems"
    )
    is_reversible: bool = Field(..., description="Changes can be easily rolled back")
    has_precedent: bool = Field(..., description="Similar work has been done before")
    estimated_duration_minutes: int = Field(
        ..., gt=0, description="Estimated time to complete"
    )
    file_count: int = Field(..., ge=0, description="Number of files to modify")
    line_count: int = Field(..., ge=0, description="Estimated lines of change")
