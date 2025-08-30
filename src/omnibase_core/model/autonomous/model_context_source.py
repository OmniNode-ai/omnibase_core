"""
Context Source Model for Autonomous Development

Model representing a single source of context information.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ModelContextSource(BaseModel):
    """Represents a source of context information for autonomous processing."""

    source_type: str = Field(
        ...,
        description="Type of context source",
        examples=["debug_log", "doc", "code", "pr", "scenario"],
    )
    file_path: str = Field(..., description="Path to the source file")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score from 0.0 to 1.0"
    )
    last_modified: datetime = Field(..., description="Last modification time")
    content_summary: str = Field(..., description="Summary of the content")
    key_patterns: List[str] = Field(
        default_factory=list, description="Key patterns extracted from content"
    )
