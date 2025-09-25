"""
Strongly-typed workflow parameters model.

Replaces dict[str, Any] usage in workflow parameters with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any


class ModelWorkflowParameters(BaseModel):
    """
    Strongly-typed workflow parameters.

    Replaces dict[str, Any] with structured workflow parameter model.
    """

    workflow_configuration: dict[str, str] = Field(
        default_factory=dict, description="String-based workflow configuration"
    )
    execution_settings: dict[str, bool] = Field(
        default_factory=dict, description="Boolean execution settings"
    )
    timeout_settings: dict[str, int] = Field(
        default_factory=dict, description="Timeout settings in milliseconds"
    )
    resource_limits: dict[str, float] = Field(
        default_factory=dict, description="Resource limit values"
    )
    environment_variables: dict[str, str] = Field(
        default_factory=dict, description="Environment variable settings"
    )


# Export for use
__all__ = ["ModelWorkflowParameters"]
