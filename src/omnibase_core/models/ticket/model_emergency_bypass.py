# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEmergencyBypass — emergency bypass configuration for ticket contracts.

OMN-10064 / OMN-9582: Ported from onex_change_control.models.model_ticket_contract.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.utils.util_decorators import allow_string_id

_MAX_STRING_LENGTH = 10000


@allow_string_id(
    reason=(
        "follow_up_ticket_id is an external Linear ticket reference "
        "(e.g., 'OMN-962'), not a system UUID."
    )
)
class ModelEmergencyBypass(BaseModel):
    """Emergency bypass configuration in ticket contract.

    When enabled=True, both justification and follow_up_ticket_id are required.
    The follow_up_ticket_id is a Linear-style ticket reference (e.g., "OMN-1234"),
    not a UUID — it is an external system identifier.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(..., description="Whether bypass is enabled")
    justification: str = Field(
        default="",
        description="Justification for bypass (required if enabled)",
        max_length=_MAX_STRING_LENGTH,
    )
    # string-id-ok: Linear ticket reference (e.g., "OMN-962"), not a system UUID
    follow_up_ticket_id: str = Field(
        default="",
        description="Follow-up ticket ID (Linear reference, required if enabled)",
        max_length=50,
    )

    @model_validator(mode="after")
    def validate_bypass_fields(self) -> ModelEmergencyBypass:
        """Validate bypass fields are complete if enabled."""
        if self.enabled:
            if not self.justification.strip():
                msg = "justification is required when bypass is enabled"
                raise ValueError(msg)
            if not self.follow_up_ticket_id.strip():
                msg = "follow_up_ticket_id is required when bypass is enabled"
                raise ValueError(msg)
        return self


__all__ = ["ModelEmergencyBypass"]
