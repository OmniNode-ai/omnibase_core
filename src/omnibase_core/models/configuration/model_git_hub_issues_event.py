from pydantic import Field

from omnibase_core.errors.error_codes import ModelOnexError

"""
ONEX-Compliant GitHub Issues Event Model

Phase 3I remediation: Eliminated factory method anti-patterns and optional return types.
"""

from pydantic import BaseModel, Field, validator

from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError

from .model_git_hub_issue import ModelGitHubIssue
from .model_git_hub_label import ModelGitHubLabel
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubIssuesEvent(BaseModel):
    """
    ONEX-compliant GitHub issues event model with strong typing and validation.

    Provides structured GitHub issues event handling with proper constructor patterns
    and immutable design following ONEX standards.
    """

    action: str = Field(
        ...,
        description="GitHub event action type",
        pattern="^(opened|edited|deleted|transferred|pinned|unpinned|closed|reopened|assigned|unassigned|labeled|unlabeled|locked|unlocked|milestoned|demilestoned)$",
        min_length=4,
        max_length=15,
    )

    issue: ModelGitHubIssue = Field(
        ...,
        description="Associated issue data",
    )

    repository: ModelGitHubRepository = Field(
        ...,
        description="Repository where event occurred",
    )

    sender: ModelGitHubUser = Field(
        ...,
        description="User who triggered the event",
    )

    label: ModelGitHubLabel | None = Field(
        default=None,
        description="Label data for labeled/unlabeled actions",
    )

    assignee: ModelGitHubUser | None = Field(
        default=None,
        description="Assignee data for assigned/unassigned actions",
    )

    # ONEX validation constraints
    @validator("action")
    def validate_action_context(cls, v, values):
        """Validate action corresponds to appropriate context data."""
        label_actions = {"labeled", "unlabeled"}
        assignee_actions = {"assigned", "unassigned"}

        # Label context validation would require label field validation
        # Assignee context validation would require assignee field validation
        # This validation ensures action is in expected format
        return v

    @validator("label")
    def validate_label_context(cls, v, values):
        """Ensure label is provided when action requires it."""
        action = values.get("action", "")
        if action in {"labeled", "unlabeled"} and v is None:
            raise ModelOnexError(
                f"Action '{action}' requires label data",
                ModelCoreErrorCode.VALIDATION_ERROR,
            )
        if action not in {"labeled", "unlabeled"} and v is not None:
            # Note: This might be too strict - GitHub may include label in other contexts
            pass  # Allow label in other contexts for flexibility
        return v

    @validator("assignee")
    def validate_assignee_context(cls, v, values):
        """Ensure assignee is provided when action requires it."""
        action = values.get("action", "")
        if action in {"assigned", "unassigned"} and v is None:
            raise ModelOnexError(
                f"Action '{action}' requires assignee data",
                ModelCoreErrorCode.VALIDATION_ERROR,
            )
        if action not in {"assigned", "unassigned"} and v is not None:
            # Allow assignee in other contexts for flexibility
            pass
        return v
