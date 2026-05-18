# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate repository configuration model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from omnibase_core.models.gate.model_omnigate_check import ModelOmniGateCheck
from omnibase_core.models.gate.model_omnigate_gate_policy import (
    ModelOmniGateGatePolicy,
)
from omnibase_core.models.gate.model_omnigate_receipt_policy import (
    ModelOmniGateReceiptPolicy,
)
from omnibase_core.models.gate.model_omnigate_validator_ref import (
    ModelOmniGateValidatorRef,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelOmniGateConfig(BaseModel):
    """Trusted OmniGate configuration from `.omnigate.yaml`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: ModelSemVer
    project_name: str
    project_url: HttpUrl
    max_checks: int = Field(default=50, gt=0, le=200)
    denied_command_patterns: tuple[str, ...] = Field(default=())
    checks: tuple[ModelOmniGateCheck, ...] = Field(default=(), max_length=200)
    validators: tuple[ModelOmniGateValidatorRef, ...] = Field(default=())
    gate: ModelOmniGateGatePolicy = Field(default_factory=ModelOmniGateGatePolicy)
    receipt: ModelOmniGateReceiptPolicy = Field(
        default_factory=ModelOmniGateReceiptPolicy
    )

    @model_validator(mode="after")
    def _validate_check_count(self) -> ModelOmniGateConfig:
        if len(self.checks) > self.max_checks:
            msg = (
                f"checks length {len(self.checks)} exceeds max_checks {self.max_checks}"
            )
            raise ValueError(msg)
        return self


__all__ = ["ModelOmniGateConfig"]
