"""
Example context data model.

Clean, strongly-typed replacement for dict[str, Any] in example context data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_context_type import EnumContextType
from ...enums.enum_execution_mode import EnumExecutionMode
from ..metadata.model_semver import ModelSemVer


class ModelExampleContextData(BaseModel):
    """
    Clean model for example context data.

    Replaces dict[str, Any] with structured context model.
    """

    # Core context fields
    context_type: EnumContextType = Field(
        default=EnumContextType.USER, description="Type of context"
    )
    environment: str | None = Field(None, description="Environment context")

    # Execution context
    execution_mode: EnumExecutionMode = Field(
        default=EnumExecutionMode.AUTO, description="Execution mode"
    )
    timeout_seconds: float | None = Field(None, description="Timeout in seconds")

    # Environment variables and settings
    environment_variables: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )

    # Configuration context
    configuration_overrides: dict[str, str | int | bool] = Field(
        default_factory=dict, description="Configuration overrides"
    )

    # User and session context
    user_id: UUID | None = Field(None, description="UUID of the user")
    user_display_name: str | None = Field(None, description="Human-readable user name")
    session_id: UUID | None = Field(None, description="Session identifier")

    # Additional metadata
    tags: list[str] = Field(default_factory=list, description="Context tags")
    notes: str | None = Field(None, description="Additional context notes")

    # Version info
    schema_version: ModelSemVer | None = Field(
        None, description="Schema version for validation"
    )


# Export the model
__all__ = ["ModelExampleContextData"]
