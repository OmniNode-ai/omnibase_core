# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelReviewPacket — the deterministic review-packet primitive.

OMN-13387 (epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md). A
ReviewPacket binds together the four content-addressed hashes that prove a
contract-driven change is internally consistent — the source contract hash,
the derived IR hash, the produced patch hash — plus the validation-pipeline
version that produced them and the typed receipt-gate outcome.

The packet is frozen and ``extra="forbid"``. Its own ``packet_hash`` is a
deterministic content hash over the canonical (sort-key) JSON serialization of
the packet, so two packets with the same fields hash identically regardless of
construction order. This is the surface a renderer (or an OmniStudio evidence
bundle) reads to decide whether to display, gate, or commit a change.
"""

from __future__ import annotations

import hashlib
import json
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.contracts.ticket.model_receipt_gate_result import (
    ModelReceiptGateResult,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelReviewPacket"]

_SHA256_REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelReviewPacket(BaseModel):
    """A deterministic, content-addressed packet for a contract-driven review.

    ``source_contract_hash``, ``ir_hash``, and ``patch_hash`` are each a
    ``sha256:<64 lowercase hex>`` reference to the source contract, the derived
    intermediate representation, and the produced patch respectively.
    ``validation_pipeline_version`` is the semantic version of the pipeline that
    produced the packet. ``receipt_gate_result`` is the typed receipt-gate
    outcome for the change. ``compute_packet_hash`` yields a stable hash over the
    canonical serialization so equal packets hash equally.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_contract_hash: str = Field(
        ...,
        description="sha256:<hex> reference to the source contract under review",
    )
    ir_hash: str = Field(
        ...,
        description="sha256:<hex> reference to the IR derived from the contract",
    )
    patch_hash: str = Field(
        ...,
        description="sha256:<hex> reference to the patch produced for the change",
    )
    validation_pipeline_version: ModelSemVer = Field(
        ...,
        description="Semantic version of the validation pipeline that produced this packet",
    )
    receipt_gate_result: ModelReceiptGateResult = Field(
        ...,
        description="Typed receipt-gate outcome for the reviewed change",
    )

    @field_validator("source_contract_hash", "ir_hash", "patch_hash")
    @classmethod
    def _validate_sha256_ref(cls, value: str) -> str:
        if not _SHA256_REF_RE.fullmatch(value):
            raise ValueError(
                f"hash must match 'sha256:<64 lowercase hex chars>', got: {value!r}"
            )
        return value

    def compute_packet_hash(self) -> str:
        """Return a deterministic ``sha256:<hex>`` content hash for this packet.

        The hash is computed over the canonical (sort-key, no-whitespace) JSON
        serialization of the packet's fields, so two packets with equal fields
        produce an identical hash independent of construction order.
        """
        payload = self.model_dump(mode="json")
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
