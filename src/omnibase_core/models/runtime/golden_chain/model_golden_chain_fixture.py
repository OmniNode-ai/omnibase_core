# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Provenance-stamped golden-chain replay fixture model (OMN-13499).

A golden-chain fixture is RECORDED EVIDENCE, not authority. It freezes ONLY the
model's response bytes plus a full provenance bundle proving WHICH concrete route
+ request produced those bytes, so the replay transport can fail closed when the
live path resolves a different route or constructs a different request.

The provenance bundle is the load-bearing surface: it pins the fixture to a
concrete ``provider`` / ``model_id`` / ``endpoint`` and to the exact ``request_hash``
the live inference handler must reconstruct on replay. If any of those drift, the
recorded bytes are no longer evidence for the request and the replay FAILS.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelGoldenChainProvenance(BaseModel):
    """Full provenance bundle stamped on every recorded golden-chain fixture.

    Every field is REQUIRED — a fixture missing any provenance field is an
    ``INVALID_FIXTURE``. The hashes pin the fixture to the concrete route +
    request + routing-contract state it was recorded against.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    provider: str = Field(
        ...,
        min_length=1,
        description="Provider the response was recorded from (e.g. zai, gemini, openrouter).",
    )
    model_id: str = Field(
        ...,
        min_length=1,
        description="CONCRETE resolved model id (never a delegation tier name).",
    )
    endpoint_ref: str = Field(
        ...,
        min_length=1,
        description="Logical endpoint reference / backend_id resolved by routing authority.",
    )
    endpoint: str = Field(
        ...,
        min_length=1,
        description="COMPLETE resolved chat-completions URL the request was posted to verbatim.",
    )
    request_hash: str = Field(
        ...,
        min_length=1,
        description=(
            "Canonical hash of the OpenAI-compatible request body the live path "
            "constructed at record time. The replay transport recomputes this from "
            "the live request and fails closed on mismatch (REQUEST_HASH_MISMATCH)."
        ),
    )
    prompt_hash: str = Field(
        ...,
        min_length=1,
        description="Canonical hash of the prompt messages (provenance / drift triage).",
    )
    routing_contract_hash: str = Field(
        ...,
        min_length=1,
        description="Hash of the routing contract bytes (e.g. bifrost_delegation.yaml) at record time.",
    )
    routing_overlay_hash: str = Field(
        ...,
        min_length=1,
        description=(
            "Hash of the routing overlay bytes at record time, or the sentinel "
            "'none' when no overlay was applied."
        ),
    )
    recorded_at: str = Field(
        ...,
        min_length=1,
        description="UTC ISO-8601 timestamp the fixture was recorded.",
    )
    fixture_version: str = Field(
        ..., min_length=1, description="Schema version of the fixture envelope."
    )


class ModelGoldenChainFixture(BaseModel):
    """A recorded-from-real golden-chain fixture: provenance + raw response bytes.

    ``raw_response`` is the model's REAL output captured at record time (the only
    thing the replay transport replaces). ``provenance`` proves which concrete
    route + request produced it. Everything else on the chain runs live on replay.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    fixture_version: str = Field(
        ...,
        min_length=1,
        description="Schema version of the fixture envelope (mirrors provenance.fixture_version).",
    )
    provenance: ModelGoldenChainProvenance = Field(
        ...,
        description="Full provenance bundle pinning this fixture to a concrete route + request.",
    )
    raw_response: dict[str, object] = Field(
        ...,
        description=(
            "The REAL provider response JSON captured at record time (OpenAI-compatible "
            "chat-completion shape). Replayed verbatim as the model's response bytes."
        ),
    )


__all__ = ["ModelGoldenChainFixture", "ModelGoldenChainProvenance"]
