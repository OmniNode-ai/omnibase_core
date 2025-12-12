from typing import Self

from pydantic import BaseModel, Field

"""
GitHub release event model to replace Dict[str, Any] usage.
"""

from .model_git_hub_release import ModelGitHubRelease
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubReleaseEventData(BaseModel):
    """Data structure for GitHub release event."""

    action: str = Field(default=..., description="Event action")
    release: dict[str, object] = Field(default=..., description="Release data")
    repository: dict[str, object] = Field(default=..., description="Repository data")
    sender: dict[str, object] = Field(default=..., description="Sender data")


class ModelGitHubReleaseEvent(BaseModel):
    """
    GitHub release event with typed fields.
    Replaces Dict[str, Any] for release event fields.
    """

    action: str = Field(
        default=...,
        description="Event action (published/created/edited/deleted/prereleased/released)",
    )
    release: ModelGitHubRelease = Field(default=..., description="Release data")
    repository: ModelGitHubRepository = Field(
        default=..., description="Repository data"
    )
    sender: ModelGitHubUser = Field(
        default=..., description="User who triggered the event"
    )

    @classmethod
    def from_data(
        cls,
        data: ModelGitHubReleaseEventData | None,
    ) -> Self | None:
        """Create from typed data model for easy migration."""
        if data is None:
            return None
        return cls(**data.model_dump())
