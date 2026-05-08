# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_hook_activation import (
    ModelHookActivation,
)


class ModelPackageHookActivations(BaseModel):
    """Envelope that <package>/contracts/hook_activations.yaml validates against."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hook_activations: list[ModelHookActivation] = Field(default_factory=list)
