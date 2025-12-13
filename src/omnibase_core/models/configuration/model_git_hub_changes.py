"""
GitHub Changes Model for ONEX Configuration System.

Strongly typed model for GitHub webhook change data.
"""

from pydantic import BaseModel, Field


class ModelGitHubChanges(BaseModel):
    """
    Strongly typed model for GitHub webhook changes.

    Represents the changes field in GitHub webhook events
    for edited actions with proper type safety.
    """

    body: str | None = Field(
        default=None,
        description="Previous body content for edited comments/issues",
    )

    title: str | None = Field(
        default=None,
        description="Previous title for edited issues",
    )

    updated_at: str | None = Field(
        default=None,
        description="Previous updated timestamp",
    )
