# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for batch_validator (OMN-9769, parent OMN-9757).

Phase 3, Task 12 — batch validator that sweeps a directory tree of contract
YAML files, applying a chosen EnumValidatorMode to each, and returns an
aggregated summary report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket
from omnibase_core.enums.enum_validator_mode import EnumValidatorMode
from omnibase_core.normalization.batch_validator import (
    ModelBatchValidationSummary,
    run_batch_validation,
)


def _clean_effect_contract(name: str = "node_foo_effect") -> dict[str, Any]:
    return {
        "name": name,
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": f"{name} test fixture.",
        "node_type": "EFFECT_GENERIC",
        "input_model": "foo.bar.models.ModelFooRequest",
        "output_model": "foo.bar.models.ModelFooResult",
        "handler_routing": {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "routing_key": "foo.run",
                    "handler_key": "handle_foo_run",
                    "priority": 0,
                }
            ],
        },
        "io_operations": [
            {
                "operation_type": "read",
                "resource_type": "external_api",
                "resource_identifier": "foo.api/run",
            }
        ],
    }


def _legacy_effect_contract(name: str = "node_bar_effect") -> dict[str, Any]:
    return {
        "name": name,
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": f"{name} legacy test fixture.",
        "node_type": "EFFECT_GENERIC",
        "metadata": {"author": "Team"},
        "contract_name": name,
        "event_bus": {"subscribe_topics": ["onex.evt.foo.v1"]},
        "input_model": {"name": "ModelBarRequest", "module": "bar.models"},
        "output_model": {"name": "ModelBarResult", "module": "bar.models"},
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "handler_type": "bar",
                    "supported_operations": ["bar.run"],
                    "handler": {"name": "HandlerBar", "module": "bar"},
                }
            ],
        },
        "io_operations": [
            {
                "operation_type": "write",
                "resource_type": "database",
                "resource_identifier": "bar_db.bar_table",
            }
        ],
    }


def _write_node_contract(tmp_path: Path, body: dict[str, Any]) -> Path:
    p = tmp_path / "nodes" / body["name"] / "contract.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(yaml.safe_dump(body))
    return p


@pytest.mark.unit
class TestModelBatchValidationSummaryConstruction:
    """ModelBatchValidationSummary is the aggregated result from run_batch_validation."""

    def test_summary_fields_exist(self) -> None:
        summary = ModelBatchValidationSummary(
            total=5,
            passed=3,
            failed=2,
            mode=EnumValidatorMode.STRICT,
            reports=[],
        )
        assert summary.total == 5
        assert summary.passed == 3
        assert summary.failed == 2
        assert summary.mode is EnumValidatorMode.STRICT
        assert summary.reports == []

    def test_summary_is_immutable(self) -> None:
        from pydantic import ValidationError

        summary = ModelBatchValidationSummary(
            total=1,
            passed=1,
            failed=0,
            mode=EnumValidatorMode.STRICT,
            reports=[],
        )
        with pytest.raises((ValidationError, TypeError)):
            summary.total = 99  # type: ignore[misc]

    def test_summary_counts_consistent(self) -> None:
        summary = ModelBatchValidationSummary(
            total=4,
            passed=3,
            failed=1,
            mode=EnumValidatorMode.MIGRATION_AUDIT,
            reports=[],
        )
        assert summary.passed + summary.failed == summary.total


@pytest.mark.unit
class TestRunBatchValidationStrictMode:
    """run_batch_validation in STRICT mode: clean contracts pass, legacy fail."""

    def test_empty_directory_returns_zero_counts(self, tmp_path: Path) -> None:
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.STRICT)
        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.mode is EnumValidatorMode.STRICT

    def test_single_clean_contract_passes_strict(self, tmp_path: Path) -> None:
        _write_node_contract(tmp_path, _clean_effect_contract())
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.STRICT)
        assert summary.total == 1
        assert summary.passed == 1
        assert summary.failed == 0

    def test_single_legacy_contract_fails_strict(self, tmp_path: Path) -> None:
        _write_node_contract(tmp_path, _legacy_effect_contract())
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.STRICT)
        assert summary.total == 1
        assert summary.failed == 1
        assert summary.passed == 0

    def test_mixed_contracts_correct_counts_strict(self, tmp_path: Path) -> None:
        _write_node_contract(tmp_path, _clean_effect_contract("node_clean_a_effect"))
        _write_node_contract(tmp_path, _clean_effect_contract("node_clean_b_effect"))
        _write_node_contract(tmp_path, _legacy_effect_contract("node_legacy_a_effect"))
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.STRICT)
        # 3 node-root contracts + any non-node contracts under tmp_path
        node_root_reports = [
            r
            for r in summary.reports
            if r.bucket is EnumContractBucket.NODE_ROOT_CONTRACT
        ]
        assert len(node_root_reports) == 3
        passed_node = sum(1 for r in node_root_reports if r.passed)
        failed_node = sum(1 for r in node_root_reports if not r.passed)
        assert passed_node == 2
        assert failed_node == 1

    def test_default_mode_is_strict(self, tmp_path: Path) -> None:
        _write_node_contract(tmp_path, _clean_effect_contract())
        summary = run_batch_validation(tmp_path)
        assert summary.mode is EnumValidatorMode.STRICT

    def test_reports_length_matches_total(self, tmp_path: Path) -> None:
        _write_node_contract(tmp_path, _clean_effect_contract("node_foo_effect"))
        _write_node_contract(tmp_path, _clean_effect_contract("node_bar_effect"))
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.STRICT)
        assert len(summary.reports) == summary.total


@pytest.mark.unit
class TestRunBatchValidationMigrationAuditMode:
    """run_batch_validation in MIGRATION_AUDIT mode: legacy contracts pass after normalize."""

    def test_legacy_contract_passes_migration_audit(self, tmp_path: Path) -> None:
        _write_node_contract(tmp_path, _legacy_effect_contract())
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.MIGRATION_AUDIT)
        assert summary.total == 1
        assert summary.passed == 1
        assert summary.failed == 0

    def test_all_reports_have_normalized_true_for_node_root(
        self, tmp_path: Path
    ) -> None:
        _write_node_contract(tmp_path, _clean_effect_contract())
        _write_node_contract(tmp_path, _legacy_effect_contract())
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.MIGRATION_AUDIT)
        node_root_reports = [
            r
            for r in summary.reports
            if r.bucket is EnumContractBucket.NODE_ROOT_CONTRACT
        ]
        assert all(r.normalized for r in node_root_reports)

    def test_mode_recorded_on_summary(self, tmp_path: Path) -> None:
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.MIGRATION_AUDIT)
        assert summary.mode is EnumValidatorMode.MIGRATION_AUDIT


@pytest.mark.unit
class TestRunBatchValidationRecursiveWalk:
    """Batch validator recurses into subdirectories."""

    def test_contracts_in_nested_dirs_are_found(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nodes" / "node_nested_effect"
        nested.mkdir(parents=True)
        (nested / "contract.yaml").write_text(
            yaml.safe_dump(_clean_effect_contract("node_nested_effect"))
        )
        # Also write a top-level one
        _write_node_contract(tmp_path, _clean_effect_contract("node_top_effect"))
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.STRICT)
        paths = [r.path for r in summary.reports]
        assert any("node_nested_effect" in str(p) for p in paths)
        assert any("node_top_effect" in str(p) for p in paths)

    def test_non_contract_yaml_files_are_ignored(self, tmp_path: Path) -> None:
        _write_node_contract(tmp_path, _clean_effect_contract())
        # Write a non-contract YAML that should be ignored
        other = tmp_path / "config.yaml"
        other.write_text(yaml.safe_dump({"key": "value"}))
        summary = run_batch_validation(tmp_path, mode=EnumValidatorMode.STRICT)
        # config.yaml is not named contract.yaml — must not appear in reports
        assert all(r.path.name == "contract.yaml" for r in summary.reports)
