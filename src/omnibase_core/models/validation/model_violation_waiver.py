"""Violation waiver model for baseline management.

Waivers allow temporary exceptions to validation rules.
They require governance: owner, reason, expiry, ticket.
"""

from __future__ import annotations

import fnmatch
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelViolationWaiver(BaseModel):
    """Temporary waiver for known violations.

    Waivers are not a garbage chute - they're a contract.
    Expired waivers become validation errors.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    waiver_id: str = Field(  # string-id-ok: human-readable waiver identifier
        description="Unique identifier for this waiver"
    )

    rule_id: str = Field(  # string-id-ok: references rule_id from RuleRegistry
        description="Rule ID this waiver applies to"
    )

    path_pattern: str = Field(
        description="Glob pattern for files this waiver covers",
    )

    reason: str = Field(
        description="Explanation of why this waiver exists",
    )

    owner: str = Field(
        description="Email or team responsible for this waiver",
    )

    expires: datetime = Field(
        description="When this waiver expires (must be in the future)",
    )

    ticket_id: str | None = Field(  # string-id-ok: Linear ticket ID like "OMN-1234"
        default=None,
        description="Linear ticket tracking remediation",
    )

    fingerprint: str | None = Field(
        default=None,
        description="Specific violation fingerprint (for precise targeting)",
    )

    def is_expired(self) -> bool:
        """Check if this waiver has expired."""
        return self.expires < datetime.now(tz=UTC)

    def matches_violation(
        self,
        rule_id: str,  # string-id-ok: rule_id from RuleRegistry
        file_path: str,
        fingerprint: str | None = None,
    ) -> bool:
        """Check if this waiver applies to a specific violation.

        Args:
            rule_id: The rule ID that produced the violation.
            file_path: The file path where the violation occurred.
            fingerprint: Optional violation fingerprint for precise matching.

        Returns:
            True if this waiver covers the violation, False otherwise.
        """
        if self.rule_id != rule_id:
            return False

        if not fnmatch.fnmatch(file_path, self.path_pattern):
            return False

        # If waiver specifies fingerprint, it must match
        if self.fingerprint is not None and fingerprint != self.fingerprint:
            return False

        return True


__all__ = ["ModelViolationWaiver"]
