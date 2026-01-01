"""
GitHub release event data model.

Data structure for GitHub release event, separate from the main event model.
"""

from pydantic import BaseModel, Field


class ModelGitHubReleaseEventData(BaseModel):
    """Data structure for GitHub release event."""

    action: str = Field(default=..., description="Event action")
    release: dict[str, object] = Field(default=..., description="Release data")
    repository: dict[str, object] = Field(default=..., description="Repository data")
    sender: dict[str, object] = Field(default=..., description="Sender data")


__all__ = ["ModelGitHubReleaseEventData"]
