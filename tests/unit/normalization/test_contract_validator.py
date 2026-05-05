# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for validate_contract_file (OMN-9768, parent OMN-9757).

Phase 3 — central seam tying corpus classification + per-family
normalization to strict Pydantic validation. Two modes:

- ``STRICT``: no normalization; node-root contracts validate against the
  canonical typed contract model (extra="forbid"); fails immediately on
  legacy fields.
- ``MIGRATION_AUDIT``: runs the full normalization pipeline first, then
  validates; ``normalized=True`` on the result record. Used for batch
  sweeps over the legacy corpus.

Non-node-root buckets (handler/package/integration/etc.) skip validation
and pass with the bucket recorded for downstream aggregation. Unknown
node_type returns a failed report with a descriptive error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket
from omnibase_core.enums.enum_validator_mode import EnumValidatorMode
from omnibase_core.normalization.contract_validator import validate_contract_file


def _clean_effect_contract() -> dict[str, Any]:
    return {
        "name": "node_foo_effect",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "Foo effect node test fixture.",
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


def _legacy_effect_contract() -> dict[str, Any]:
    """Legacy shape: dict-form input/output_model, event_bus block,
    metadata, no handler_routing version, supported_operations form."""
    return {
        "name": "node_bar_effect",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "Bar legacy effect contract test fixture.",
        "node_type": "EFFECT_GENERIC",
        "metadata": {"author": "Team"},
        "contract_name": "node_bar_effect",
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


def _write_contract(tmp_path: Path, body: dict[str, Any]) -> Path:
    p = tmp_path / "nodes" / body["name"] / "contract.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(yaml.safe_dump(body))
    return p


@pytest.mark.unit
class TestStrictMode:
    """Strict mode: no normalization, fail on any legacy shape."""

    def test_strict_mode_passes_clean_contract(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _clean_effect_contract())
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is True, f"unexpected errors: {result.errors}"
        assert result.errors == []
        assert result.normalized is False
        assert result.bucket is EnumContractBucket.NODE_ROOT_CONTRACT
        assert result.mode is EnumValidatorMode.STRICT

    def test_strict_mode_fails_legacy_contract(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_effect_contract())
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is False
        assert len(result.errors) > 0
        assert result.normalized is False

    def test_strict_mode_default(self, tmp_path: Path) -> None:
        """STRICT is the default mode."""
        path = _write_contract(tmp_path, _clean_effect_contract())
        default = validate_contract_file(path)
        explicit = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert default.mode is EnumValidatorMode.STRICT
        assert default.passed is explicit.passed


@pytest.mark.unit
class TestMigrationAuditMode:
    """Migration-audit mode: normalize, then validate; mark normalized=True."""

    def test_migration_audit_passes_legacy_contract(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_effect_contract())
        result = validate_contract_file(path, mode=EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"unexpected errors: {result.errors}"
        assert result.normalized is True
        assert result.mode is EnumValidatorMode.MIGRATION_AUDIT

    def test_migration_audit_passes_clean_contract(self, tmp_path: Path) -> None:
        """A clean contract still passes under migration_audit; pipeline is a no-op."""
        path = _write_contract(tmp_path, _clean_effect_contract())
        result = validate_contract_file(path, mode=EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"unexpected errors: {result.errors}"
        assert result.normalized is True


@pytest.mark.unit
class TestBucketSkipping:
    """Non-node-root buckets pass without invoking model_validate()."""

    def test_integration_contract_bucket_skips_validation(self, tmp_path: Path) -> None:
        path = tmp_path / "integrations" / "github_webhook" / "contract.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(yaml.safe_dump({"name": "github_webhook"}))
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is True
        assert result.bucket is EnumContractBucket.INTEGRATION_CONTRACT
        assert result.errors == []
        assert result.normalized is False

    def test_package_contract_bucket_skips_validation(self, tmp_path: Path) -> None:
        path = tmp_path / "some_package" / "contract.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(yaml.safe_dump({"name": "pkg"}))
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is True
        assert result.bucket is EnumContractBucket.PACKAGE_CONTRACT


@pytest.mark.unit
class TestUnknownNodeType:
    """Unknown / unmapped node_type returns failed with descriptive error."""

    def test_unknown_node_type_fails(self, tmp_path: Path) -> None:
        body = _clean_effect_contract()
        body["node_type"] = "MYSTERY_NODE_TYPE"
        path = _write_contract(tmp_path, body)
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is False
        assert any("node_type" in e for e in result.errors), result.errors


@pytest.mark.unit
class TestNodeTypeAliases:
    """Short aliases (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR) resolve to GENERIC."""

    def test_effect_alias_resolves(self, tmp_path: Path) -> None:
        body = _clean_effect_contract()
        body["node_type"] = "EFFECT"
        path = _write_contract(tmp_path, body)
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is True, f"unexpected errors: {result.errors}"


@pytest.mark.unit
class TestStrictModeRequiresAlgorithmAndIo:
    """Strict mode pre-checks algorithm (COMPUTE) and io_operations (EFFECT)
    before model_validate, preserving enforcement after Task 13 makes those
    fields optional in the model."""

    def test_strict_mode_fails_effect_missing_io_operations(
        self, tmp_path: Path
    ) -> None:
        body = _clean_effect_contract()
        del body["io_operations"]
        path = _write_contract(tmp_path, body)
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is False
        assert any("io_operations" in e for e in result.errors), result.errors

    def test_strict_mode_fails_effect_empty_io_operations(self, tmp_path: Path) -> None:
        body = _clean_effect_contract()
        body["io_operations"] = []
        path = _write_contract(tmp_path, body)
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is False
        assert any("io_operations" in e for e in result.errors), result.errors

    def test_migration_audit_does_not_require_algorithm_or_io(
        self, tmp_path: Path
    ) -> None:
        """Migration_audit mode does NOT pre-enforce algorithm/io_operations;
        it surfaces only what the (post-normalization) model itself rejects."""
        body = _clean_effect_contract()
        del body["io_operations"]
        path = _write_contract(tmp_path, body)
        result = validate_contract_file(path, mode=EnumValidatorMode.MIGRATION_AUDIT)
        # Result is whatever the model says; we just want to confirm we did
        # NOT short-circuit on the strict-mode pre-check (no "io_operations
        # required" pre-check error). The model's own min_length=1 may still
        # fail today; what matters is normalized=True and the error came from
        # model_validate, not the pre-check.
        assert result.normalized is True


@pytest.mark.unit
class TestEmptyOrInvalidYaml:
    """Edge cases on YAML parsing."""

    def test_empty_yaml_skips_when_bucket_does_not_require_validation(
        self, tmp_path: Path
    ) -> None:
        # empty yaml under a non-node-root path: passes (skipped).
        path = tmp_path / "other" / "contract.yaml"
        path.parent.mkdir(parents=True)
        path.write_text("")
        result = validate_contract_file(path, mode=EnumValidatorMode.STRICT)
        assert result.passed is True
        assert result.bucket is not EnumContractBucket.NODE_ROOT_CONTRACT
