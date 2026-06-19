# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output model for the backend-secret-discipline COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_backend_ref_violation import (
    ModelBackendRefViolation,
)
from omnibase_core.models.validation.model_credential_violation import (
    ModelCredentialViolation,
)


class ModelBackendSecretDisciplineOutput(BaseModel):
    """COMPUTE result from the backend-secret-discipline handler."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ticket: str = "OMN-13305"
    gate: str = "backend-secret-discipline"
    literal_credential_violations: list[ModelCredentialViolation] = Field(
        default_factory=list
    )
    backend_ref_violations: list[ModelBackendRefViolation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    passed: bool = False


__all__ = ["ModelBackendSecretDisciplineOutput"]
