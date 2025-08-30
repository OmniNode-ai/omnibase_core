"""
GitHub release event model to replace Dict[str, Any] usage.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .model_git_hub_release import ModelGitHubRelease
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubReleaseEvent(BaseModel):
    """
    GitHub release event with typed fields.
    Replaces Dict[str, Any] for release event fields.
    """

    action: str = Field(
        ...,
        description="Event action (published/created/edited/deleted/prereleased/released)",
    )
    release: ModelGitHubRelease = Field(..., description="Release data")
    repository: ModelGitHubRepository = Field(..., description="Repository data")
    sender: ModelGitHubUser = Field(..., description="User who triggered the event")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(
        cls, data: Optional[Dict[str, Any]]
    ) -> Optional["ModelGitHubReleaseEvent"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls(**data)
