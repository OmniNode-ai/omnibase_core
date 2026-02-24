# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence bundle model for structured scoring input to the ScoringReducer.

An EvidenceBundle is a tamper-evident, fingerprinted collection of structured
evidence items for a single run evaluation. The bundle_fingerprint is computed
deterministically from content, not timestamps — enabling full replay integrity.

Part of the objective functions and reward architecture (OMN-2537).
"""

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.objective.model_evidence_item import ModelEvidenceItem

__all__ = ["ModelEvidenceBundle"]


class ModelEvidenceBundle(BaseModel):
    """A tamper-evident collection of structured evidence for one run.

    The bundle_fingerprint is a SHA-256 hash computed deterministically over
    the serialized items. This enables replay integrity: the same evidence
    always produces the same fingerprint, regardless of when it is computed.

    The fingerprint is computed from content, NOT from timestamps or identifiers.

    Attributes:
        run_id: The run that produced this evidence bundle.
        bundle_fingerprint: SHA-256 hash of the serialized evidence items.
        items: The structured evidence items in this bundle.
        collected_at_utc: ISO-8601 UTC timestamp when evidence was collected.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    run_id: str = Field(  # string-id-ok: run identifier for traceability
        description="The run that produced this evidence bundle"
    )
    bundle_fingerprint: str = Field(  # string-hash-ok: SHA-256 hex digest
        description="SHA-256 hash of the serialized evidence items (content-based, not timestamp-based)"
    )
    items: list[ModelEvidenceItem] = Field(
        description="Structured evidence items — all must be from allowed typed sources"
    )
    collected_at_utc: str = Field(  # string-datetime-ok: ISO-8601 UTC timestamp
        description="ISO-8601 UTC timestamp when this evidence bundle was collected"
    )

    @classmethod
    def fingerprint(cls, items: list[ModelEvidenceItem]) -> str:
        """Compute a deterministic SHA-256 fingerprint over a list of evidence items.

        The fingerprint is computed from the content of the items, not from
        timestamps or identifiers. This ensures that the same evidence always
        produces the same fingerprint for replay integrity.

        Algorithm:
        1. Serialize each item to a sorted-key JSON dict
        2. Sort the serialized items lexicographically (order-independent)
        3. Concatenate all serialized items
        4. Compute SHA-256 over the concatenation

        The sort ensures order-independence: two bundles with the same items
        in different orders produce the same fingerprint.

        Args:
            items: The evidence items to fingerprint.

        Returns:
            Hex-encoded SHA-256 digest of the sorted serialized items.
        """
        serialized = [
            json.dumps(item.model_dump(), sort_keys=True, ensure_ascii=True)
            for item in items
        ]
        # Sort for order-independence
        serialized.sort()
        payload = "".join(serialized)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        run_id: str,  # string-id-ok: run identifier
        items: list[ModelEvidenceItem],
        collected_at_utc: str,  # string-datetime-ok: ISO-8601 UTC timestamp
    ) -> "ModelEvidenceBundle":
        """Factory method that computes the fingerprint and constructs the bundle.

        This is the preferred construction path — it ensures the fingerprint
        is always computed from the actual items.

        Args:
            run_id: The run that produced this evidence.
            items: The structured evidence items.
            collected_at_utc: ISO-8601 UTC timestamp of collection.

        Returns:
            A new ModelEvidenceBundle with a computed bundle_fingerprint.
        """
        return cls(
            run_id=run_id,
            bundle_fingerprint=cls.fingerprint(items),
            items=items,
            collected_at_utc=collected_at_utc,
        )
