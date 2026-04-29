# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContractAllowedActions — permission model for contract role access (OMN-10251)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractAllowedActions(BaseModel):
    """Permission model for a contract: specifies allowed and denied actions.

    Rules:
    - denied_actions takes precedence over allowed_actions.
    - Empty allowed_actions means no access (deny-all by default).
    - An action is permitted only when it appears in allowed_actions
      AND does not appear in denied_actions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    allowed_actions: frozenset[str] = Field(default_factory=frozenset)
    denied_actions: frozenset[str] = Field(default_factory=frozenset)

    def is_action_permitted(self, action: str) -> bool:
        """Return True if action is permitted for this role."""
        if action in self.denied_actions:
            return False
        return action in self.allowed_actions


__all__ = ["ModelContractAllowedActions"]
