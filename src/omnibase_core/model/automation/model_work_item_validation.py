"""
Work Item Validation Model.

Model for work items that need validation before automation processing.
"""

from pydantic import BaseModel, Field


class ModelWorkItemValidation(BaseModel):
    """Model for work items requiring validation."""

    id: str = Field(..., description="Unique work item identifier")
    title: str = Field(..., description="Work item title")
    work_type: str = Field(..., description="Type of work")
    priority: str = Field(..., description="Work priority level")
    description: str | None = Field(None, description="Work item description")
    file_paths: list[str] | None = Field(None, description="Associated file paths")
    estimated_hours: float | None = Field(None, description="Estimated hours")
    assignee: str | None = Field(None, description="Assigned to")
    tags: list[str] | None = Field(None, description="Work item tags")
