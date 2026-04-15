# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Dispatch Claim Model.

Represents a filesystem-backed mutual exclusion claim for agent dispatch deduplication.
The blocker_id is a deterministic sha1 of kind|host|resource, used as the claim file key.
Prevents duplicate agent dispatches for the same logical operation (OMN-8921).
"""

import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def compute_blocker_id(kind: str, host: str, resource: str) -> str:
    """Deterministic sha1 of 'kind|host|resource'. Stable across calls with identical inputs."""
    payload = f"{kind}|{host}|{resource}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


class ModelDispatchClaim(BaseModel):
    """Filesystem claim record for dispatch deduplication.

    Written as JSON to state/dispatch_claims/<blocker_id>.json.
    O_CREAT|O_EXCL atomicity guarantees exactly-once acquisition.
    """

    model_config = {"frozen": True, "extra": "ignore"}

    blocker_id: str = Field(
        description="sha1(kind|host|resource) — 40-char lowercase hex"
    )
    kind: str = Field(description="Logical operation kind, e.g. 'fix_containers'")
    host: str = Field(description="Target host or scope, e.g. '192.168.86.201'")
    resource: str = Field(description="Specific resource within the host")
    claimant: str = Field(
        description="Agent ID or session identifier that owns this claim"
    )
    claimed_at: datetime = Field(description="UTC timestamp when claim was acquired")
    ttl_seconds: int = Field(
        default=300, ge=1, description="Claim expires after this many seconds"
    )
    tool_name: Literal["Agent", "Bash"] = Field(
        description="Claude tool that triggered the claim"
    )
    category: str = Field(default="", description="Optional dispatch category tag")
    evidence: str = Field(
        default="", description="Free-text evidence or reason for dispatch"
    )

    @field_validator("blocker_id")
    @classmethod
    def validate_blocker_id_format(cls, v: str) -> str:
        if len(v) != 40 or not all(c in "0123456789abcdef" for c in v):
            raise ValueError(
                f"blocker_id must be a 40-char lowercase sha1 hex string, got: {v!r}"
            )
        return v

    def is_expired(self) -> bool:
        """Returns True if TTL has elapsed since claimed_at."""
        now = datetime.now(tz=UTC)
        claimed_at_aware = (
            self.claimed_at.replace(tzinfo=UTC)
            if self.claimed_at.tzinfo is None
            else self.claimed_at
        )
        elapsed = (now - claimed_at_aware).total_seconds()
        return elapsed >= self.ttl_seconds

    def ttl_remaining_seconds(self) -> float:
        """Seconds remaining before expiry. Negative if already expired."""
        now = datetime.now(tz=UTC)
        claimed_at_aware = (
            self.claimed_at.replace(tzinfo=UTC)
            if self.claimed_at.tzinfo is None
            else self.claimed_at
        )
        elapsed = (now - claimed_at_aware).total_seconds()
        return self.ttl_seconds - elapsed
