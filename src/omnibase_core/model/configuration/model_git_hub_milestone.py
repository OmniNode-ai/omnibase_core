"""
GitHub Milestone Model

Type-safe GitHub milestone that replaces Dict[str, Any] usage.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .model_git_hub_user import ModelGitHubUser


class ModelGitHubMilestone(BaseModel):
    """
    Type-safe GitHub milestone.

    Represents a GitHub milestone with structured fields.
    """

    id: int = Field(..., description="Milestone ID")
    node_id: str = Field(..., description="Milestone node ID")
    number: int = Field(..., description="Milestone number")
    title: str = Field(..., description="Milestone title")
    description: Optional[str] = Field(None, description="Milestone description")
    creator: ModelGitHubUser = Field(..., description="Milestone creator")
    open_issues: int = Field(0, description="Number of open issues")
    closed_issues: int = Field(0, description="Number of closed issues")
    state: str = Field("open", description="Milestone state (open/closed)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    due_on: Optional[datetime] = Field(None, description="Due date")
    closed_at: Optional[datetime] = Field(None, description="Close timestamp")
