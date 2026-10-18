# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Deterministic shared-token policy verdict for CI and pre-commit."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_shared_token_use import ModelSharedTokenUse


class ModelSharedTokenPolicyResult(BaseModel):
    """Unreadable workflows and stale exceptions both fail the policy."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    uses: tuple[ModelSharedTokenUse, ...] = ()
    violations: tuple[ModelSharedTokenUse, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """Return true only after all supplied workflows were evaluated."""
        return not self.errors and not self.violations
