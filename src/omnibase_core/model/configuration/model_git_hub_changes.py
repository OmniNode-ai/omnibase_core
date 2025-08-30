"""
GitHub Changes Model for ONEX Configuration System.

Strongly typed model for GitHub webhook change data.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelGitHubChanges(BaseModel):
    """
    Strongly typed model for GitHub webhook changes.

    Represents the changes field in GitHub webhook events
    for edited actions with proper type safety.
    """

    body: Optional[str] = Field(
        default=None, description="Previous body content for edited comments/issues"
    )

    title: Optional[str] = Field(
        default=None, description="Previous title for edited issues"
    )

    updated_at: Optional[str] = Field(
        default=None, description="Previous updated timestamp"
    )
