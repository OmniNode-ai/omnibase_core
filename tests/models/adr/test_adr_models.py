# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for ADR extraction domain models (OMN-10691)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from omnibase_core.enums.adr.enum_decision_type import EnumDecisionType
from omnibase_core.enums.adr.enum_segment_type import EnumSegmentType
from omnibase_core.enums.adr.enum_usage_source import EnumUsageSource
from omnibase_core.models.adr.model_adr_draft import ModelADRDraft
from omnibase_core.models.adr.model_canary_result import ModelCanaryResult
from omnibase_core.models.adr.model_decision_extraction import ModelDecisionExtraction
from omnibase_core.models.adr.model_document_segment import ModelDocumentSegment
from omnibase_core.models.adr.model_extraction_score import ModelExtractionScore
from omnibase_core.models.adr.model_llm_call_evidence import ModelLLMCallEvidence

pytestmark = pytest.mark.unit

NOW = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


# --- EnumSegmentType ---


def test_enum_segment_type_members() -> None:
    expected = {
        "decision",
        "critique",
        "proposal",
        "migration",
        "invariant",
        "failure_analysis",
        "operational_concern",
        "hypothesis",
        "doctrine_formation",
        "implementation_detail",
        "architectural_risk",
        "non_decision",
        "background",
        "unknown",
    }
    assert {v.value for v in EnumSegmentType} == expected


def test_enum_segment_type_is_str() -> None:
    assert isinstance(EnumSegmentType.DECISION, str)
    assert EnumSegmentType.DECISION.value == "decision"


# --- EnumDecisionType ---


def test_enum_decision_type_members() -> None:
    expected = {
        "architecture_decision",
        "architecture_pivot",
        "doctrine_formation",
        "operational_lesson",
        "supersession",
        "rejected_approach",
    }
    assert {v.value for v in EnumDecisionType} == expected


# --- EnumUsageSource ---


def test_enum_usage_source_members() -> None:
    expected = {"MEASURED", "ESTIMATED", "UNKNOWN"}
    assert {v.value for v in EnumUsageSource} == expected


# --- ModelDocumentSegment ---


def _make_segment(**overrides: object) -> ModelDocumentSegment:
    defaults: dict[str, object] = {
        "source_path": "docs/adr/001.md",
        "segment_type": EnumSegmentType.DECISION,
        "content": "We decided to use Pydantic for models.",
        "source_content_sha256": "a" * 64,
        "segment_content_sha256": "b" * 64,
        "start_line": 1,
        "end_line": 10,
        "git_sha": "abc123",
        "created_at": NOW,
        "updated_at": NOW,
        "subsystems": ["core"],
        "tags": ["pydantic"],
    }
    defaults.update(overrides)
    return ModelDocumentSegment(**defaults)  # type: ignore[arg-type]


def test_document_segment_deterministic_id() -> None:
    seg = _make_segment()
    raw = f"{seg.source_path}{seg.source_content_sha256}{seg.start_line}{seg.end_line}{seg.segment_type.value}"
    expected = hashlib.sha256(raw.encode()).hexdigest()
    assert seg.segment_id == expected


def test_document_segment_frozen() -> None:
    seg = _make_segment()
    with pytest.raises(Exception):
        seg.content = "mutated"  # type: ignore[misc,unused-ignore]


def test_document_segment_extra_forbid() -> None:
    with pytest.raises(Exception):
        _make_segment(unknown_field="bad")  # type: ignore[call-overload]


def test_document_segment_default_lists() -> None:
    seg = _make_segment(subsystems=[], tags=[])
    assert seg.subsystems == []
    assert seg.tags == []


# --- ModelDecisionExtraction ---


def _make_extraction(**overrides: object) -> ModelDecisionExtraction:
    defaults: dict[str, object] = {
        "decision_type": EnumDecisionType.ARCHITECTURE_DECISION,
        "title": "Use Pydantic for models",
        "confidence": 0.9,
        "rationale": ["Type safety", "Validation"],
        "subsystems": ["core"],
        "supersedes": [],
        "alternatives_considered": ["dataclass", "attrs"],
        "source_segment_ids": ["seg1", "seg2"],
        "segment_content_hashes": ["hash1", "hash2"],
        "extraction_model_id": "qwen3-30b",
        "extraction_version": "1.0.0",
        "prompt_template_id": "extract_v1",
        "prompt_template_version": "1",
        "extracted_at": NOW,
    }
    defaults.update(overrides)
    return ModelDecisionExtraction(**defaults)  # type: ignore[arg-type]


def test_decision_extraction_deterministic_id() -> None:
    ext = _make_extraction()
    sorted_ids = sorted(ext.source_segment_ids)
    sorted_hashes = sorted(ext.segment_content_hashes)
    raw = f"{ext.extraction_version}{ext.extraction_model_id}{''.join(sorted_ids)}{''.join(sorted_hashes)}"
    expected = hashlib.sha256(raw.encode()).hexdigest()
    assert ext.extraction_id == expected


def test_decision_extraction_confidence_bounds() -> None:
    with pytest.raises(Exception):
        _make_extraction(confidence=1.1)
    with pytest.raises(Exception):
        _make_extraction(confidence=-0.1)


def test_decision_extraction_frozen() -> None:
    ext = _make_extraction()
    with pytest.raises(Exception):
        ext.title = "mutated"  # type: ignore[misc,unused-ignore]


# --- ModelADRDraft ---


def _make_adr_draft(**overrides: object) -> ModelADRDraft:
    defaults: dict[str, object] = {
        "date": NOW,
        "title": "Use Pydantic for models",
        "context": "We need a validation library.",
        "decision": "We will use Pydantic.",
        "consequences": "Strong typing throughout.",
        "alternatives_considered": ["dataclass"],
        "supersedes": [],
        "source_evidence": ["seg1"],
        "extraction_metadata": {
            "model_id": "qwen3-30b",
            "confidence": 0.9,
            "pipeline_version": "1.0.0",
            "prompt_template_id": "extract_v1",
            "prompt_template_version": "1",
            "canary_run_id": "run-001",
            "extracted_at": NOW,
        },
    }
    defaults.update(overrides)
    return ModelADRDraft(**defaults)  # type: ignore[arg-type]


def test_adr_draft_status_always_proposed() -> None:
    draft = _make_adr_draft()
    assert draft.status == "Proposed"


def test_adr_draft_frozen() -> None:
    draft = _make_adr_draft()
    with pytest.raises(Exception):
        draft.title = "mutated"  # type: ignore[misc,unused-ignore]


def test_adr_draft_date_is_datetime() -> None:
    draft = _make_adr_draft()
    assert isinstance(draft.date, datetime)


# --- ModelExtractionScore ---


def _make_score(**overrides: object) -> ModelExtractionScore:
    defaults: dict[str, object] = {
        "model_id": "qwen3-30b",
        "recall": 0.8,
        "precision": 0.9,
        "fidelity": 0.85,
        "format_compliance": 1.0,
        "consensus_agreement": 0.75,
        "overall_score": 0.86,
        "success": True,
        "error_code": None,
        "error_message": None,
    }
    defaults.update(overrides)
    return ModelExtractionScore(**defaults)  # type: ignore[arg-type]


def test_extraction_score_frozen() -> None:
    score = _make_score()
    with pytest.raises(Exception):
        score.model_id = "mutated"  # type: ignore[misc,unused-ignore]


def test_extraction_score_float_bounds() -> None:
    with pytest.raises(Exception):
        _make_score(recall=1.1)
    with pytest.raises(Exception):
        _make_score(overall_score=-0.1)


def test_extraction_score_error_fields_nullable() -> None:
    score = _make_score(
        success=False, error_code="LLM_TIMEOUT", error_message="timed out"
    )
    assert score.error_code == "LLM_TIMEOUT"
    assert score.success is False


# --- ModelCanaryResult ---


def test_canary_result_frozen() -> None:
    score = _make_score()
    result = ModelCanaryResult(
        ground_truth_adr_path="docs/adr/001.md",
        source_doc_paths=["docs/decisions.md"],
        model_scores={"qwen3-30b": score},
        best_model_id="qwen3-30b",
        cost_summary={"total_usd": 0.42},
    )
    with pytest.raises(Exception):
        result.best_model_id = "mutated"  # type: ignore[misc,unused-ignore]


def test_canary_result_empty_scores() -> None:
    result = ModelCanaryResult(
        ground_truth_adr_path="docs/adr/001.md",
        source_doc_paths=[],
        model_scores={},
        best_model_id=None,
        cost_summary={},
    )
    assert result.model_scores == {}
    assert result.best_model_id is None


# --- ModelLLMCallEvidence ---


def _make_llm_evidence(**overrides: object) -> ModelLLMCallEvidence:
    defaults: dict[str, object] = {
        "model_id": "qwen3-30b",
        "provider": "vllm_local",
        "prompt_template_id": "extract_v1",
        "prompt_template_version": "1",
        "prompt_hash": "p" * 64,
        "input_hash": "i" * 64,
        "request_timestamp": NOW,
        "response_hash": "r" * 64,
        "raw_response_path": None,
        "usage_source": EnumUsageSource.MEASURED,
        "prompt_tokens": 512,
        "completion_tokens": 256,
        "total_tokens": 768,
        "estimated_cost_usd": 0.001,
        "pricing_manifest_version": "v1",
        "error_state": None,
        "success": True,
    }
    defaults.update(overrides)
    return ModelLLMCallEvidence(**defaults)  # type: ignore[arg-type]


def test_llm_call_evidence_frozen() -> None:
    ev = _make_llm_evidence()
    with pytest.raises(Exception):
        ev.model_id = "mutated"  # type: ignore[misc,unused-ignore]


def test_llm_call_evidence_nullable_fields() -> None:
    ev = _make_llm_evidence(
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        estimated_cost_usd=None,
        pricing_manifest_version=None,
        raw_response_path=None,
        error_state="LLM_TIMEOUT",
        success=False,
    )
    assert ev.prompt_tokens is None
    assert ev.success is False
    assert ev.error_state == "LLM_TIMEOUT"


def test_llm_call_evidence_usage_source_estimated() -> None:
    ev = _make_llm_evidence(usage_source=EnumUsageSource.ESTIMATED)
    assert ev.usage_source == EnumUsageSource.ESTIMATED


def test_llm_call_evidence_request_timestamp_is_datetime() -> None:
    ev = _make_llm_evidence()
    assert isinstance(ev.request_timestamp, datetime)
