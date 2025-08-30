"""
Project context model for intelligence system.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelProjectContext(BaseModel):
    """Project context for intelligent analysis."""

    project_name: str = Field(..., description="Name of the project")
    project_path: str = Field(..., description="Root path of project")
    language: str = Field(..., description="Primary programming language")
    framework: Optional[str] = Field(None, description="Framework used")
    dependencies: List[str] = Field(
        default_factory=list, description="Project dependencies"
    )
    file_count: int = Field(0, description="Total number of files")
