from typing import Optional

from pydantic import Field

"""
GitHub release event model to replace Dict[str, Any] usage.
"""

from typing import Any

from pydantic import BaseModel

from .model_git_hub_release import ModelGitHubRelease
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser


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
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelGitHubReleaseEvent"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls(**data)
