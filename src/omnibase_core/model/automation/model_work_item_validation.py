"""
Work Item Validation Model.

Model for work items that need validation before automation processing.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelWorkItemValidation(BaseModel):
    """Model for work items requiring validation."""

    id: str = Field(..., description="Unique work item identifier")
    title: str = Field(..., description="Work item title")
    work_type: str = Field(..., description="Type of work")
    priority: str = Field(..., description="Work priority level")
    description: Optional[str] = Field(None, description="Work item description")
    file_paths: Optional[List[str]] = Field(None, description="Associated file paths")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours")
    assignee: Optional[str] = Field(None, description="Assigned to")
    tags: Optional[List[str]] = Field(None, description="Work item tags")
