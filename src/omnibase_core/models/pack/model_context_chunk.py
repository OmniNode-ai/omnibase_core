# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context chunk model for context pack pipeline (OMN-11678)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_context_factor import EnumContextFactor
from omnibase_core.enums.enum_context_pack_provenance import EnumContextPackProvenance


class ModelContextChunk(BaseModel):
    """A single tagged context chunk within a ModelContextPack.

    chunk_id is deterministic: ctx_ + first 8 hex chars of sha256(factor:content).
    Use compute_chunk_id() from util_context_pack to generate it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    chunk_id: str  # string-id-ok: deterministic ctx_XXXXXXXX hash prefix, not a UUID
    factor: EnumContextFactor
    content: str
    token_estimate: int
    token_estimation_method: str
    tokenizer_source: str
    # string-version-ok: external tokenizer version string, not ModelSemVer
    tokenizer_version: str
    estimation_accuracy: str  # "estimated" | "measured"
    provenance: EnumContextPackProvenance
    source_artifact_hash: str
    # string-id-ok: Linear ticket ID (e.g. OMN-XXXX), not a UUID
    source_ticket_id: str | None
    source_contract_hash: str
    # string-id-ok: pipeline run identifier string, not a UUID
    source_run_id: str | None


__all__ = [
    "ModelContextChunk",
]
