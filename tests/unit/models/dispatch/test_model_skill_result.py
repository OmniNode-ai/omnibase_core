# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelSkillResult[T] typed skill dispatch receipt (OMN-13091)."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums.enum_skill_result_status import EnumSkillResultStatus
from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef
from omnibase_core.models.dispatch.model_skill_result import (
    SKILL_RESULT_SCHEMA_VERSION,
    ModelSkillResult,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class StubDelegateResponse(BaseModel):
    """Concrete result model standing in for a skill's typed result."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    answer: str
    tokens_used: int


def _stub_result() -> StubDelegateResponse:
    return StubDelegateResponse(answer="42", tokens_used=7)


def _artifact_ref(seed: bytes = b"capture-log") -> ModelArtifactRef:
    return ModelArtifactRef(ref=f"sha256:{hashlib.sha256(seed).hexdigest()}")


def _envelope_kwargs() -> dict[str, object]:
    return {
        "skill_name": "delegate",
        "node_name": "node_delegate_skill_orchestrator",
        "status": EnumSkillResultStatus.SUCCESS,
        "correlation_id": uuid4(),
        "run_id": uuid4(),
        "exit_code": 0,
        "duration_ms": 1250,
        "result": _stub_result(),
        "result_model": (
            "tests.unit.models.dispatch.test_model_skill_result.StubDelegateResponse"
        ),
    }


@pytest.mark.unit
class TestModelSkillResultConstruction:
    """Construction, defaults, and typing."""

    def test_minimal_construction(self) -> None:
        envelope = ModelSkillResult[StubDelegateResponse](**_envelope_kwargs())  # type: ignore[arg-type]
        assert envelope.skill_name == "delegate"
        assert envelope.node_name == "node_delegate_skill_orchestrator"
        assert envelope.status is EnumSkillResultStatus.SUCCESS
        assert isinstance(envelope.correlation_id, UUID)
        assert isinstance(envelope.run_id, UUID)
        assert envelope.exit_code == 0
        assert envelope.duration_ms == 1250
        assert envelope.result == _stub_result()
        assert envelope.metrics == {}
        assert envelope.artifact_refs == []
        assert envelope.schema_version == SKILL_RESULT_SCHEMA_VERSION

    def test_typed_result_is_concrete_model(self) -> None:
        envelope = ModelSkillResult[StubDelegateResponse](**_envelope_kwargs())  # type: ignore[arg-type]
        assert isinstance(envelope.result, StubDelegateResponse)
        assert envelope.result.answer == "42"

    def test_artifact_refs_and_metrics(self) -> None:
        kwargs = _envelope_kwargs()
        kwargs["artifact_refs"] = [_artifact_ref(), _artifact_ref(b"handler-result")]
        kwargs["metrics"] = {"llm_calls": 1.0, "tokens": 7.0}
        envelope = ModelSkillResult[StubDelegateResponse](**kwargs)  # type: ignore[arg-type]
        assert len(envelope.artifact_refs) == 2
        assert all(isinstance(r, ModelArtifactRef) for r in envelope.artifact_refs)
        assert envelope.metrics["tokens"] == 7.0

    def test_status_coerced_from_string(self) -> None:
        kwargs = _envelope_kwargs()
        kwargs["status"] = "failed"
        envelope = ModelSkillResult[StubDelegateResponse](**kwargs)  # type: ignore[arg-type]
        assert envelope.status is EnumSkillResultStatus.FAILED

    def test_schema_version_default_is_semver(self) -> None:
        envelope = ModelSkillResult[StubDelegateResponse](**_envelope_kwargs())  # type: ignore[arg-type]
        assert isinstance(envelope.schema_version, ModelSemVer)


@pytest.mark.unit
class TestModelSkillResultValidation:
    """Field validation and rejection paths."""

    @pytest.mark.parametrize(
        "field",
        [
            "skill_name",
            "node_name",
            "status",
            "correlation_id",
            "run_id",
            "exit_code",
            "duration_ms",
            "result",
            "result_model",
        ],
    )
    def test_required_fields(self, field: str) -> None:
        kwargs = _envelope_kwargs()
        del kwargs[field]
        with pytest.raises(ValidationError):
            ModelSkillResult[StubDelegateResponse](**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("field", ["skill_name", "node_name"])
    def test_empty_name_rejected(self, field: str) -> None:
        kwargs = _envelope_kwargs()
        kwargs[field] = ""
        with pytest.raises(ValidationError):
            ModelSkillResult[StubDelegateResponse](**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "bad_fqn",
        [
            "",
            "NoDotsHere",  # not fully qualified
            ".leading.dot",
            "trailing.dot.",
            "spaces in.name",
            "1numeric.start",
        ],
    )
    def test_result_model_must_be_fully_qualified(self, bad_fqn: str) -> None:
        kwargs = _envelope_kwargs()
        kwargs["result_model"] = bad_fqn
        with pytest.raises(ValidationError):
            ModelSkillResult[StubDelegateResponse](**kwargs)  # type: ignore[arg-type]

    def test_negative_duration_rejected(self) -> None:
        kwargs = _envelope_kwargs()
        kwargs["duration_ms"] = -1
        with pytest.raises(ValidationError):
            ModelSkillResult[StubDelegateResponse](**kwargs)  # type: ignore[arg-type]

    def test_negative_exit_code_allowed_for_signal_termination(self) -> None:
        kwargs = _envelope_kwargs()
        kwargs["exit_code"] = -15
        kwargs["status"] = EnumSkillResultStatus.ERROR
        envelope = ModelSkillResult[StubDelegateResponse](**kwargs)  # type: ignore[arg-type]
        assert envelope.exit_code == -15


@pytest.mark.unit
class TestModelSkillResultContract:
    """Model contract: frozen, extra forbidden, round-trip."""

    def test_frozen(self) -> None:
        envelope = ModelSkillResult[StubDelegateResponse](**_envelope_kwargs())  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            envelope.exit_code = 1  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        kwargs = _envelope_kwargs()
        kwargs["unexpected"] = True
        with pytest.raises(ValidationError):
            ModelSkillResult[StubDelegateResponse](**kwargs)  # type: ignore[arg-type]

    def test_json_round_trip_parametrized(self) -> None:
        envelope = ModelSkillResult[StubDelegateResponse](**_envelope_kwargs())  # type: ignore[arg-type]
        restored = ModelSkillResult[StubDelegateResponse].model_validate_json(
            envelope.model_dump_json()
        )
        assert restored == envelope
        assert isinstance(restored.result, StubDelegateResponse)

    def test_unparametrized_envelope_validation(self) -> None:
        """Receipt consumers validate envelope structure before resolving T."""
        envelope = ModelSkillResult[StubDelegateResponse](**_envelope_kwargs())  # type: ignore[arg-type]
        generic = ModelSkillResult.model_validate_json(envelope.model_dump_json())
        assert generic.skill_name == "delegate"
        assert generic.result_model.endswith("StubDelegateResponse")
