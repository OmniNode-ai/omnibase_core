# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumValidatorMode + ModelCorpusValidationReport (OMN-9767, parent OMN-9757).

Phase 3 — validator mode selection and per-file outcome record for the
corpus classification + normalization layer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket
from omnibase_core.enums.enum_validator_mode import EnumValidatorMode
from omnibase_core.models.contracts.model_corpus_validation_report import (
    ModelCorpusValidationReport,
)


@pytest.mark.unit
class TestEnumValidatorModeStructure:
    """Test enum membership, types, and lookup behavior."""

    def test_two_modes_exist(self) -> None:
        assert hasattr(EnumValidatorMode, "STRICT")
        assert hasattr(EnumValidatorMode, "MIGRATION_AUDIT")

    def test_member_count_is_two(self) -> None:
        assert len(list(EnumValidatorMode)) == 2

    def test_wire_values(self) -> None:
        assert EnumValidatorMode.STRICT.value == "strict"
        assert EnumValidatorMode.MIGRATION_AUDIT.value == "migration_audit"

    def test_mode_is_str_enum(self) -> None:
        assert isinstance(EnumValidatorMode.STRICT, str)

    def test_enum_is_unique(self) -> None:
        values = [m.value for m in EnumValidatorMode]
        assert len(values) == len(set(values))

    def test_enum_from_value(self) -> None:
        assert EnumValidatorMode("strict") is EnumValidatorMode.STRICT
        assert EnumValidatorMode("migration_audit") is EnumValidatorMode.MIGRATION_AUDIT

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumValidatorMode("not_a_real_mode")

    def test_enum_equality_with_string(self) -> None:
        assert EnumValidatorMode.STRICT == "strict"
        assert EnumValidatorMode.MIGRATION_AUDIT == "migration_audit"


@pytest.mark.unit
class TestEnumValidatorModeSerialization:
    """Test JSON / YAML / Pydantic round-trip safety."""

    def test_json_serialization_via_value(self) -> None:
        data = {"mode": EnumValidatorMode.STRICT.value}
        assert json.dumps(data) == '{"mode": "strict"}'

    def test_yaml_round_trip(self) -> None:
        data = {"mode": EnumValidatorMode.MIGRATION_AUDIT.value}
        loaded = yaml.safe_load(yaml.dump(data))
        assert loaded["mode"] == "migration_audit"
        assert EnumValidatorMode(loaded["mode"]) is EnumValidatorMode.MIGRATION_AUDIT

    def test_pydantic_field_assignment(self) -> None:
        class M(BaseModel):
            mode: EnumValidatorMode

        m = M(mode=EnumValidatorMode.STRICT)
        assert m.mode is EnumValidatorMode.STRICT

    def test_pydantic_string_coercion(self) -> None:
        class M(BaseModel):
            mode: EnumValidatorMode

        m = M(mode="migration_audit")
        assert m.mode is EnumValidatorMode.MIGRATION_AUDIT

    def test_pydantic_invalid_raises(self) -> None:
        class M(BaseModel):
            mode: EnumValidatorMode

        with pytest.raises(ValidationError):
            M(mode="bogus_mode")

    def test_pydantic_model_dump(self) -> None:
        class M(BaseModel):
            mode: EnumValidatorMode

        m = M(mode=EnumValidatorMode.STRICT)
        assert m.model_dump() == {"mode": "strict"}

    def test_pydantic_model_dump_json(self) -> None:
        class M(BaseModel):
            mode: EnumValidatorMode

        m = M(mode=EnumValidatorMode.MIGRATION_AUDIT)
        assert m.model_dump_json() == '{"mode":"migration_audit"}'


@pytest.mark.unit
class TestEnumValidatorModeExports:
    """Confirm the enum import path resolves."""

    def test_import_via_module(self) -> None:
        from omnibase_core.enums import enum_validator_mode

        assert enum_validator_mode.EnumValidatorMode is EnumValidatorMode


@pytest.mark.unit
class TestModelCorpusValidationReportConstruction:
    """Test construction with required and optional fields."""

    def test_minimal_pass_record(self) -> None:
        report = ModelCorpusValidationReport(
            path=Path("foo/contract.yaml"),
            bucket=EnumContractBucket.NODE_ROOT_CONTRACT,
            mode=EnumValidatorMode.STRICT,
            passed=True,
            normalized=False,
        )
        assert report.passed is True
        assert report.errors == []
        assert report.normalization_flags == []
        assert report.normalized is False

    def test_minimal_fail_record_with_errors(self) -> None:
        report = ModelCorpusValidationReport(
            path=Path("bar/contract.yaml"),
            bucket=EnumContractBucket.HANDLER_CONTRACT,
            mode=EnumValidatorMode.MIGRATION_AUDIT,
            passed=False,
            errors=["Field required: input_model"],
            normalized=True,
            normalization_flags=["legacy_input_output_model"],
        )
        assert report.passed is False
        assert report.errors == ["Field required: input_model"]
        assert report.normalized is True
        assert report.normalization_flags == ["legacy_input_output_model"]

    def test_path_is_path_object(self) -> None:
        report = ModelCorpusValidationReport(
            path=Path("baz/contract.yaml"),
            bucket=EnumContractBucket.PACKAGE_CONTRACT,
            mode=EnumValidatorMode.STRICT,
            passed=True,
            normalized=False,
        )
        assert isinstance(report.path, Path)

    def test_pydantic_string_path_coercion(self) -> None:
        report = ModelCorpusValidationReport(
            path="qux/contract.yaml",  # type: ignore[arg-type]
            bucket=EnumContractBucket.PACKAGE_CONTRACT,
            mode=EnumValidatorMode.STRICT,
            passed=True,
            normalized=False,
        )
        assert report.path == Path("qux/contract.yaml")


@pytest.mark.unit
class TestModelCorpusValidationReportImmutability:
    """Frozen + extra=forbid invariants."""

    def test_frozen_blocks_setattr(self) -> None:
        report = ModelCorpusValidationReport(
            path=Path("foo/contract.yaml"),
            bucket=EnumContractBucket.NODE_ROOT_CONTRACT,
            mode=EnumValidatorMode.STRICT,
            passed=False,
            errors=["err"],
            normalized=False,
        )
        with pytest.raises(ValidationError):
            report.passed = True  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelCorpusValidationReport(
                path=Path("foo/contract.yaml"),
                bucket=EnumContractBucket.NODE_ROOT_CONTRACT,
                mode=EnumValidatorMode.STRICT,
                passed=True,
                normalized=False,
                bogus_extra="nope",  # type: ignore[call-arg]
            )

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelCorpusValidationReport(  # type: ignore[call-arg]
                path=Path("foo/contract.yaml"),
                bucket=EnumContractBucket.NODE_ROOT_CONTRACT,
                mode=EnumValidatorMode.STRICT,
                # passed missing
                normalized=False,
            )


@pytest.mark.unit
class TestModelCorpusValidationReportSerialization:
    """JSON / dict round-trip safety; from_attributes wiring."""

    def test_model_dump_preserves_wire_shape(self) -> None:
        report = ModelCorpusValidationReport(
            path=Path("foo/contract.yaml"),
            bucket=EnumContractBucket.NODE_ROOT_CONTRACT,
            mode=EnumValidatorMode.STRICT,
            passed=True,
            normalized=False,
        )
        dumped = report.model_dump(mode="json")
        assert dumped["bucket"] == "node_root_contract"
        assert dumped["mode"] == "strict"
        assert dumped["passed"] is True
        assert dumped["normalized"] is False
        assert dumped["errors"] == []
        assert dumped["normalization_flags"] == []

    def test_round_trip_via_model_validate(self) -> None:
        report = ModelCorpusValidationReport(
            path=Path("foo/contract.yaml"),
            bucket=EnumContractBucket.HANDLER_CONTRACT,
            mode=EnumValidatorMode.MIGRATION_AUDIT,
            passed=False,
            errors=["e1", "e2"],
            normalized=True,
            normalization_flags=["legacy_event_bus"],
        )
        round_tripped = ModelCorpusValidationReport.model_validate(
            report.model_dump(mode="json")
        )
        assert round_tripped == report

    def test_from_attributes_construction(self) -> None:
        class _Source:
            path = Path("foo/contract.yaml")
            bucket = EnumContractBucket.NODE_ROOT_CONTRACT
            mode = EnumValidatorMode.STRICT
            passed = True
            errors: list[str] = []
            normalized = False
            normalization_flags: list[str] = []

        report = ModelCorpusValidationReport.model_validate(
            _Source(), from_attributes=True
        )
        assert report.passed is True
        assert report.bucket is EnumContractBucket.NODE_ROOT_CONTRACT
        assert report.mode is EnumValidatorMode.STRICT
