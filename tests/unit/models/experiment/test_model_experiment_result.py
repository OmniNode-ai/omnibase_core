# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the canonical Shared Experiment Result Contract (OMN-13613).

The contract is shared by all three Phase-3 experiment orchestrators
(OMN-13614 / OMN-13615 / OMN-13616) plus omnimarket. Every field must be
strongly typed (UUID, enums, typed value objects — no bare ``str``), and the
model and its value objects must be frozen.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_experiment_status import EnumExperimentStatus
from omnibase_core.enums.enum_experiment_type import EnumExperimentType
from omnibase_core.models.experiment.model_experiment_cost import ModelExperimentCost
from omnibase_core.models.experiment.model_experiment_evidence_ref import (
    ModelExperimentEvidenceRef,
)
from omnibase_core.models.experiment.model_experiment_result import (
    ModelExperimentResult,
)
from omnibase_core.models.experiment.model_experiment_score import ModelExperimentScore


def _result(**overrides: object) -> ModelExperimentResult:
    base: dict[str, object] = {
        "experiment_id": uuid4(),
        "experiment_type": EnumExperimentType.MODEL_EVAL,
        "run_id": uuid4(),
        "correlation_id": uuid4(),
        "runtime_identity": "stability-test/runtime-local",
        "score": ModelExperimentScore(value=0.875, scale_max=1.0),
        "cost": ModelExperimentCost(cost_usd=Decimal("0.0123")),
        "status": EnumExperimentStatus.COMPLETED,
        "evidence_ref": ModelExperimentEvidenceRef(evidence_id=uuid4()),
    }
    base.update(overrides)
    return ModelExperimentResult(**base)  # type: ignore[arg-type]


@pytest.mark.unit
class TestEnumExperimentType:
    def test_is_str_enum(self) -> None:
        assert EnumExperimentType.MODEL_EVAL.value == "model_eval"
        assert str(EnumExperimentType.MODEL_EVAL) == "model_eval"

    def test_covers_three_phase3_orchestrators(self) -> None:
        values = {member.value for member in EnumExperimentType}
        assert {"entropy", "model_eval", "regression_test"} <= values


@pytest.mark.unit
class TestEnumExperimentStatus:
    def test_is_str_enum(self) -> None:
        assert EnumExperimentStatus.COMPLETED.value == "completed"
        assert str(EnumExperimentStatus.FAILED) == "failed"

    def test_has_lifecycle_states(self) -> None:
        values = {member.value for member in EnumExperimentStatus}
        assert {"pending", "running", "completed", "failed"} <= values


@pytest.mark.unit
class TestModelExperimentScore:
    def test_valid_score(self) -> None:
        score = ModelExperimentScore(value=0.5, scale_max=1.0)
        assert score.value == 0.5
        assert score.scale_max == 1.0

    def test_frozen(self) -> None:
        score = ModelExperimentScore(value=0.5, scale_max=1.0)
        with pytest.raises(ValidationError):
            score.value = 0.6  # type: ignore[misc]

    def test_value_must_not_exceed_scale_max(self) -> None:
        with pytest.raises(ValidationError):
            ModelExperimentScore(value=1.5, scale_max=1.0)

    def test_negative_value_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelExperimentScore(value=-0.1, scale_max=1.0)

    def test_scale_max_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ModelExperimentScore(value=0.0, scale_max=0.0)


@pytest.mark.unit
class TestModelExperimentCost:
    def test_cost_usd_is_decimal(self) -> None:
        cost = ModelExperimentCost(cost_usd=Decimal("0.42"))
        assert isinstance(cost.cost_usd, Decimal)
        assert cost.cost_usd == Decimal("0.42")

    def test_frozen(self) -> None:
        cost = ModelExperimentCost(cost_usd=Decimal("0.42"))
        with pytest.raises(ValidationError):
            cost.cost_usd = Decimal("0.99")  # type: ignore[misc]

    def test_negative_cost_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelExperimentCost(cost_usd=Decimal("-0.01"))

    def test_zero_cost_allowed(self) -> None:
        assert ModelExperimentCost(cost_usd=Decimal("0")).cost_usd == Decimal("0")


@pytest.mark.unit
class TestModelExperimentEvidenceRef:
    def test_evidence_id_is_uuid(self) -> None:
        evidence_id = uuid4()
        ref = ModelExperimentEvidenceRef(evidence_id=evidence_id)
        assert ref.evidence_id == evidence_id
        assert isinstance(ref.evidence_id, UUID)

    def test_frozen(self) -> None:
        ref = ModelExperimentEvidenceRef(evidence_id=uuid4())
        with pytest.raises(ValidationError):
            ref.evidence_id = uuid4()  # type: ignore[misc]

    def test_optional_artifact_ref(self) -> None:
        ref = ModelExperimentEvidenceRef(
            evidence_id=uuid4(),
            artifact_ref="sha256:" + "a" * 64,
        )
        assert ref.artifact_ref == "sha256:" + "a" * 64

    def test_string_evidence_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelExperimentEvidenceRef(evidence_id="not-a-uuid")  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelExperimentResultFieldTypes:
    def test_identifier_fields_are_uuid(self) -> None:
        result = _result()
        assert isinstance(result.experiment_id, UUID)
        assert isinstance(result.run_id, UUID)
        assert isinstance(result.correlation_id, UUID)

    def test_enum_fields_are_enums(self) -> None:
        result = _result()
        assert isinstance(result.experiment_type, EnumExperimentType)
        assert isinstance(result.status, EnumExperimentStatus)

    def test_typed_value_objects(self) -> None:
        result = _result()
        assert isinstance(result.score, ModelExperimentScore)
        assert isinstance(result.cost, ModelExperimentCost)
        assert isinstance(result.evidence_ref, ModelExperimentEvidenceRef)

    def test_runtime_identity_typed(self) -> None:
        result = _result()
        assert result.runtime_identity == "stability-test/runtime-local"

    def test_string_experiment_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _result(experiment_id="not-a-uuid")

    def test_invalid_experiment_type_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _result(experiment_type="not_a_type")

    def test_valid_experiment_type_string_coerced(self) -> None:
        # str-enum members accept their own string value (cross-process wire).
        result = _result(experiment_type="model_eval")
        assert result.experiment_type is EnumExperimentType.MODEL_EVAL

    def test_string_status_coerced_or_rejected(self) -> None:
        # str enum members accept their string value; an unknown string must fail.
        with pytest.raises(ValidationError):
            _result(status="not_a_status")

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            _result(unexpected_field="x")


@pytest.mark.unit
class TestModelExperimentResultFrozen:
    def test_result_is_frozen(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.status = EnumExperimentStatus.FAILED  # type: ignore[misc]

    def test_score_field_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.score = ModelExperimentScore(value=0.1, scale_max=1.0)  # type: ignore[misc]


@pytest.mark.unit
class TestModelExperimentResultSerialization:
    def test_roundtrip_json(self) -> None:
        result = _result()
        dumped = result.model_dump_json()
        restored = ModelExperimentResult.model_validate_json(dumped)
        assert restored == result

    def test_equality_by_value(self) -> None:
        experiment_id = uuid4()
        run_id = uuid4()
        correlation_id = uuid4()
        evidence_id = uuid4()
        kwargs: dict[str, object] = {
            "experiment_id": experiment_id,
            "experiment_type": EnumExperimentType.REGRESSION_TEST,
            "run_id": run_id,
            "correlation_id": correlation_id,
            "runtime_identity": "dev/runtime-local",
            "score": ModelExperimentScore(value=1.0, scale_max=1.0),
            "cost": ModelExperimentCost(cost_usd=Decimal("0")),
            "status": EnumExperimentStatus.COMPLETED,
            "evidence_ref": ModelExperimentEvidenceRef(evidence_id=evidence_id),
        }
        assert ModelExperimentResult(**kwargs) == ModelExperimentResult(**kwargs)  # type: ignore[arg-type]
