# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelGatewayRenewalDirective — the renewal cycle handed to a client at attach.

Client-side mirror of ``omnibase_infra``'s ``ModelGatewayRenewalDirective``
(``node_gateway_attach_effect`` contract 0.3.0, OMN-15952), field-for-field.
Mirrored, not imported: ``omnibase_core`` sits below ``omnibase_infra``, so
the import edge does not exist in that direction; this is the same seam
precedent ``onex-api``'s ``models_gateway.py`` records for the same family.

The ordering invariant ``renew_not_before <= renew_at < session_expires_at``
is re-enforced HERE, on the receiving side, rather than trusted from the
producer. A directive whose ``renew_at`` is at or past the ceiling is worse
than no directive -- it instructs the client to attempt a re-attach with a
session already dead, and reads as deliberate policy rather than a bug. The
check lives in the model rather than in the parser so every construction path
(wire deserialization, a test, a future second caller) is subject to it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_gateway_renewal_mode import EnumGatewayRenewalMode

__all__ = ["ModelGatewayRenewalDirective"]


class ModelGatewayRenewalDirective(BaseModel):
    """Server-declared renewal cycle for one attached session."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    mode: EnumGatewayRenewalMode
    # Echo of the session ceiling this cycle races. Never moved by any later call.
    session_expires_at: datetime
    # Earliest moment the client should begin its re-grant + re-attach.
    renew_not_before: datetime
    # Latest moment by which re-grant + re-attach must have COMPLETED.
    renew_at: datetime
    # The terms that produced the two timestamps, echoed so a client can
    # recompute the cycle after a clock correction without a second round trip.
    margin_seconds: int = Field(gt=0)
    jitter_seconds: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_ordering(self) -> ModelGatewayRenewalDirective:
        """Reject a directive that would tell this client to renew late."""
        if self.renew_not_before > self.renew_at:
            raise ValueError(
                "renew_not_before must not be later than renew_at "
                f"({self.renew_not_before.isoformat()} > {self.renew_at.isoformat()})"
            )
        if self.renew_at >= self.session_expires_at:
            raise ValueError(
                "renew_at must be strictly before session_expires_at -- renewal "
                "completes before expiry and never extends it "
                f"({self.renew_at.isoformat()} >= "
                f"{self.session_expires_at.isoformat()})"
            )
        return self
