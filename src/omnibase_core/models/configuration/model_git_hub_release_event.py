"""
GitHub release event model to replace Dict[str, Any] usage.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from .model_git_hub_release import ModelGitHubRelease
from .model_git_hub_release_event_data import ModelGitHubReleaseEventData
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubReleaseEvent(BaseModel):
    """
    GitHub release event with typed fields.
    Replaces Dict[str, Any] for release event fields.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

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


# Note: ModelGitHubReleaseEventData is already imported at module level (line 10)
# and re-exported via __all__ for external consumers
__all__ = ["ModelGitHubReleaseEvent", "ModelGitHubReleaseEventData"]
