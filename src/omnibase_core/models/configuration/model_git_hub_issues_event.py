"""
ONEX-Compliant GitHub Issues Event Model

Phase 3I remediation: Eliminated factory method anti-patterns and optional return types.
"""

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .model_git_hub_issue import ModelGitHubIssue
from .model_git_hub_label import ModelGitHubLabel
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubIssuesEvent(BaseModel):
    """
    ONEX-compatible GitHub issues event model with strong typing and validation.

    Provides structured GitHub issues event handling with proper constructor patterns
    and immutable design following ONEX standards.
    """

    action: str = Field(
        default=...,
        description="GitHub event action type",
        pattern="^(opened|edited|deleted|transferred|pinned|unpinned|closed|reopened|assigned|unassigned|labeled|unlabeled|locked|unlocked|milestoned|demilestoned)$",
        min_length=4,
        max_length=15,
    )

    issue: ModelGitHubIssue = Field(
        default=...,
        description="Associated issue data",
    )

    repository: ModelGitHubRepository = Field(
        default=...,
        description="Repository where event occurred",
    )

    sender: ModelGitHubUser = Field(
        default=...,
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
    @field_validator("action")
    @classmethod
    def validate_action_context(cls, v: str, info: ValidationInfo) -> str:
        """Pass-through validator for action field (validation handled by Field pattern).

        The action field is already validated by the Field pattern constraint, which
        enforces valid GitHub action strings. Context-specific validation (ensuring
        label/assignee data is present for corresponding actions) happens in the
        validate_label_context and validate_assignee_context validators.

        This validator exists as a hook point for future cross-field validation if needed.
        """
        return v

    @field_validator("label")
    @classmethod
    def validate_label_context(
        cls, v: ModelGitHubLabel | None, info: ValidationInfo
    ) -> ModelGitHubLabel | None:
        """Ensure label is provided when action requires it."""
        action_raw = info.data.get("action", "")
        # Runtime type check for action from info.data
        if not isinstance(action_raw, str):
            raise ModelOnexError(
                message=f"action must be str, got {type(action_raw).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        action: str = action_raw
        if action in {"labeled", "unlabeled"} and v is None:
            raise ModelOnexError(
                message=f"Action '{action}' requires label data",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if action not in {"labeled", "unlabeled"} and v is not None:
            # Note: This might be too strict - GitHub may include label in other contexts
            pass  # Allow label in other contexts for flexibility
        return v

    @field_validator("assignee")
    @classmethod
    def validate_assignee_context(
        cls, v: ModelGitHubUser | None, info: ValidationInfo
    ) -> ModelGitHubUser | None:
        """Ensure assignee is provided when action requires it."""
        action_raw = info.data.get("action", "")
        # Runtime type check for action from info.data
        if not isinstance(action_raw, str):
            raise ModelOnexError(
                message=f"action must be str, got {type(action_raw).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        action: str = action_raw
        if action in {"assigned", "unassigned"} and v is None:
            raise ModelOnexError(
                message=f"Action '{action}' requires assignee data",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if action not in {"assigned", "unassigned"} and v is not None:
            # Allow assignee in other contexts for flexibility
            pass
        return v
