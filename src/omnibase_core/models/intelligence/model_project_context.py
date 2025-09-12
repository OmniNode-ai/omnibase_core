"""
Project context model for intelligence system.
"""

from pydantic import BaseModel, Field


class ModelProjectContext(BaseModel):
    """Project context for intelligent analysis."""

    project_name: str = Field(..., description="Name of the project")
    project_path: str = Field(..., description="Root path of project")
    language: str = Field(..., description="Primary programming language")
    framework: str | None = Field(None, description="Framework used")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Project dependencies",
    )
    file_count: int = Field(0, description="Total number of files")
