# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for context pack schema models (OMN-11678)."""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_context_factor import EnumContextFactor
from omnibase_core.enums.enum_context_pack_failure import EnumContextPackFailure
from omnibase_core.enums.enum_context_pack_provenance import EnumContextPackProvenance
from omnibase_core.models.pack.model_context_chunk import ModelContextChunk
from omnibase_core.models.pack.model_context_pack import ModelContextPack
from omnibase_core.utils.util_context_pack import compute_chunk_id

pytestmark = pytest.mark.unit


def _make_default_chunk() -> ModelContextChunk:
    chunk_id = compute_chunk_id("golden_chain", "example content")
    return ModelContextChunk(
        chunk_id=chunk_id,
        factor=EnumContextFactor.GOLDEN_CHAIN,
        content="example content",
        token_estimate=10,
        token_estimation_method="character_heuristic",
        tokenizer_source="tiktoken",
        tokenizer_version="0.5.2",
        estimation_accuracy="estimated",
        provenance=EnumContextPackProvenance.GENERATED,
        source_artifact_hash="abc123",
        source_ticket_id="OMN-11678",
        source_contract_hash="deadbeef",
        source_run_id="run-001",
    )


# --- compute_chunk_id ---


def test_chunk_id_deterministic_same_inputs() -> None:
    a = compute_chunk_id("golden_chain", "hello world")
    b = compute_chunk_id("golden_chain", "hello world")
    assert a == b


def test_chunk_id_differs_for_different_content() -> None:
    a = compute_chunk_id("golden_chain", "content A")
    b = compute_chunk_id("golden_chain", "content B")
    assert a != b


def test_chunk_id_differs_for_different_factor() -> None:
    a = compute_chunk_id("golden_chain", "same content")
    b = compute_chunk_id("exemplar", "same content")
    assert a != b


def test_chunk_id_prefix_format() -> None:
    chunk_id = compute_chunk_id("golden_chain", "test")
    assert chunk_id.startswith("ctx_")
    hex_part = chunk_id[len("ctx_") :]
    assert len(hex_part) == 8
    assert all(c in "0123456789abcdef" for c in hex_part)


def test_chunk_id_requires_enum_dot_value() -> None:
    # compute_chunk_id takes str; callers must pass factor.value, not the enum instance.
    # The str() of a str-Enum renders as "EnumName.MEMBER", not the raw value.
    from_value = compute_chunk_id(EnumContextFactor.GOLDEN_CHAIN.value, "content")
    assert from_value.startswith("ctx_")
    assert len(from_value) == len("ctx_") + 8


# --- ModelContextChunk ---


def test_model_context_chunk_construction() -> None:
    chunk = _make_default_chunk()
    assert chunk.chunk_id == compute_chunk_id("golden_chain", "example content")
    assert chunk.factor == EnumContextFactor.GOLDEN_CHAIN
    assert chunk.content == "example content"
    assert chunk.token_estimate == 10
    assert chunk.provenance == EnumContextPackProvenance.GENERATED
    assert chunk.source_ticket_id == "OMN-11678"
    assert chunk.source_run_id == "run-001"


def test_model_context_chunk_nullable_fields_accept_none() -> None:
    chunk_id = compute_chunk_id("exemplar", "content")
    chunk = ModelContextChunk(
        chunk_id=chunk_id,
        factor=EnumContextFactor.EXEMPLAR,
        content="content",
        token_estimate=5,
        token_estimation_method="character_heuristic",
        tokenizer_source="tiktoken",
        tokenizer_version="0.5.2",
        estimation_accuracy="estimated",
        provenance=EnumContextPackProvenance.CURATED,
        source_artifact_hash="ff00ff",
        source_ticket_id=None,
        source_contract_hash="c0ffee",
        source_run_id=None,
    )
    assert chunk.source_ticket_id is None
    assert chunk.source_run_id is None


def test_model_context_chunk_frozen_rejects_mutation() -> None:
    chunk = _make_default_chunk()
    with pytest.raises(Exception):
        chunk.content = "mutated"  # type: ignore[misc,unused-ignore]


def test_model_context_chunk_rejects_extra_fields() -> None:
    chunk_id = compute_chunk_id("golden_chain", "example content")
    with pytest.raises(Exception):
        ModelContextChunk(  # type: ignore[call-arg]
            chunk_id=chunk_id,
            factor=EnumContextFactor.GOLDEN_CHAIN,
            content="example content",
            token_estimate=10,
            token_estimation_method="character_heuristic",
            tokenizer_source="tiktoken",
            tokenizer_version="0.5.2",
            estimation_accuracy="estimated",
            provenance=EnumContextPackProvenance.GENERATED,
            source_artifact_hash="abc123",
            source_ticket_id=None,
            source_contract_hash="deadbeef",
            source_run_id=None,
            unknown_field="oops",
        )


# --- ModelContextPack ---


def _make_chunk(factor: EnumContextFactor, content: str) -> ModelContextChunk:
    chunk_id = compute_chunk_id(factor.value, content)
    return ModelContextChunk(
        chunk_id=chunk_id,
        factor=factor,
        content=content,
        token_estimate=20,
        token_estimation_method="character_heuristic",
        tokenizer_source="tiktoken",
        tokenizer_version="0.5.2",
        estimation_accuracy="estimated",
        provenance=EnumContextPackProvenance.GENERATED,
        source_artifact_hash="aabb",
        source_ticket_id=None,
        source_contract_hash="ccdd",
        source_run_id=None,
    )


def test_model_context_pack_construction() -> None:
    chunk = _make_chunk(EnumContextFactor.GOLDEN_CHAIN, "chain content")
    pack = ModelContextPack(
        pack_id="pack-001",
        contract_hash="ctr_hash",
        model_id="glm-4-5",
        chunks=(chunk,),
        total_token_estimate=20,
        generated_at="2026-05-22T00:00:00Z",
        profile_version="1.0.0",
    )
    assert pack.pack_id == "pack-001"
    assert len(pack.chunks) == 1
    assert pack.chunks[0].factor == EnumContextFactor.GOLDEN_CHAIN


def test_model_context_pack_chunks_is_tuple() -> None:
    chunk = _make_chunk(EnumContextFactor.EXEMPLAR, "exemplar content")
    pack = ModelContextPack(
        pack_id="pack-002",
        contract_hash="ctr_hash",
        model_id="qwen3-coder",
        chunks=(chunk,),
        total_token_estimate=20,
        generated_at="2026-05-22T00:00:00Z",
        profile_version="1.0.0",
    )
    assert isinstance(pack.chunks, tuple)


def test_model_context_pack_empty_chunks_allowed() -> None:
    pack = ModelContextPack(
        pack_id="pack-003",
        contract_hash="ctr_hash",
        model_id="test-model",
        chunks=(),
        total_token_estimate=0,
        generated_at="2026-05-22T00:00:00Z",
        profile_version="1.0.0",
    )
    assert pack.chunks == ()


def test_model_context_pack_frozen_rejects_mutation() -> None:
    pack = ModelContextPack(
        pack_id="pack-004",
        contract_hash="ctr_hash",
        model_id="test-model",
        chunks=(),
        total_token_estimate=0,
        generated_at="2026-05-22T00:00:00Z",
        profile_version="1.0.0",
    )
    with pytest.raises(Exception):
        pack.pack_id = "mutated"  # type: ignore[misc,unused-ignore]


def test_model_context_pack_serializes_and_deserializes() -> None:
    chunk = _make_chunk(EnumContextFactor.CLAUDE_MD, "claude md content")
    pack = ModelContextPack(
        pack_id="pack-005",
        contract_hash="ctr_hash",
        model_id="deepseek-r1",
        chunks=(chunk,),
        total_token_estimate=30,
        generated_at="2026-05-22T12:00:00+00:00",
        profile_version="0.1.0",
    )
    data = pack.model_dump()
    restored = ModelContextPack.model_validate(data)
    assert restored.pack_id == pack.pack_id
    assert restored.chunks[0].chunk_id == chunk.chunk_id
    assert restored.chunks[0].factor == EnumContextFactor.CLAUDE_MD


# --- Enum coverage ---


def test_enum_context_factor_members() -> None:
    values = {e.value for e in EnumContextFactor}
    assert values == {
        "golden_chain",
        "exemplar",
        "local_failures",
        "architecture_patterns",
        "claude_md",
    }


def test_enum_context_pack_provenance_members() -> None:
    values = {e.value for e in EnumContextPackProvenance}
    assert values == {"generated", "curated", "cached", "observed"}


def test_enum_context_pack_failure_members() -> None:
    values = {e.value for e in EnumContextPackFailure}
    assert values == {
        "required_factor_missing",
        "profile_not_found",
        "token_budget_exceeded",
        "invalid_profile",
        "artifact_hash_mismatch",
    }
