# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Policy bundle model aggregating trust policy, classification gates, and redaction.

A policy bundle is the top-level policy object passed to the tiered
resolver. It combines a trust policy with classification gates and
redaction policies, and provides a deterministic hash for use as a
determinism input to route plans.

.. versionadded:: 0.21.0
    Phase 4 of authenticated dependency resolution (OMN-2893).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.routing.model_classification_gate import (
    ModelClassificationGate,
)
from omnibase_core.models.routing.model_redaction_policy import ModelRedactionPolicy
from omnibase_core.models.security.model_trustpolicy import ModelTrustPolicy

__all__ = ["ModelPolicyBundle"]


class ModelPolicyBundle(BaseModel):
    """Aggregated policy bundle for tiered resolution.

    Combines a trust policy with classification gates and redaction
    policies. The ``compute_hash()`` method produces a deterministic
    SHA-256 hash used as a determinism input to ``ModelRoutePlan``.

    Attributes:
        bundle_id: Unique identifier for this policy bundle.
        trust_policy: The underlying trust policy with rules and
            enforcement settings.
        classification_gates: List of classification gates constraining
            resolution by data sensitivity level.
        redaction_policies: List of redaction policies available for
            field-level data protection.
        version: Version string for this policy bundle
            (e.g., ``"1.0.0"``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    bundle_id: UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for this policy bundle",
    )

    trust_policy: ModelTrustPolicy = Field(
        description="Trust policy with rules and enforcement settings",
    )

    classification_gates: list[ModelClassificationGate] = Field(
        default_factory=list,
        description="Classification gates constraining resolution by tier",
    )

    redaction_policies: list[ModelRedactionPolicy] = Field(
        default_factory=list,
        description="Redaction policies for field-level data protection",
    )

    version: str = Field(
        description="Version string for this policy bundle",
        min_length=1,
    )

    def compute_hash(self) -> str:
        """Compute a deterministic SHA-256 hash of this policy bundle.

        Serializes the bundle to canonical JSON (sorted keys, compact
        separators) and produces a hex-encoded SHA-256 digest prefixed
        with ``sha256:``.

        The hash is deterministic: identical bundle contents always
        produce the same hash regardless of field ordering or Python
        dict iteration order.

        Returns:
            SHA-256 hex digest prefixed with ``sha256:``.
        """
        # Build a canonical representation for hashing.
        # We use model_dump with mode="json" for JSON-compatible types,
        # then re-serialize with sorted keys for determinism.
        data = self.model_dump(mode="json")
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
