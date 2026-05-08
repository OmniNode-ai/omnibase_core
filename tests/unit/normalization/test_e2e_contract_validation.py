# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""End-to-end verification of the contract validation pipeline (OMN-9773, parent OMN-9757).

Phase 6 — validates the complete pipeline path:
  corpus classification → normalization (migration_audit mode) → Pydantic validation

Ten representative contracts are exercised across all four node types (EFFECT_GENERIC,
COMPUTE_GENERIC, REDUCER_GENERIC, ORCHESTRATOR_GENERIC) and three repos
(omnibase_core, omnibase_infra, onex_change_control).

Test matrix (10 fixtures):

  Fixture 1  — EFFECT_GENERIC,       canonical shape,  STRICT: pass, AUDIT: pass
  Fixture 2  — COMPUTE_GENERIC,      canonical shape,  STRICT: pass, AUDIT: pass
  Fixture 3  — REDUCER_GENERIC,      canonical shape,  STRICT: pass, AUDIT: pass
  Fixture 4  — ORCHESTRATOR_GENERIC, canonical shape,  STRICT: pass, AUDIT: pass
  Fixture 5  — EFFECT_GENERIC,       legacy shape,     STRICT: fail, AUDIT: pass
  Fixture 6  — COMPUTE_GENERIC,      legacy shape,     STRICT: fail, AUDIT: pass
  Fixture 7  — REDUCER_GENERIC,      legacy shape,     STRICT: fail, AUDIT: pass
  Fixture 8  — ORCHESTRATOR_GENERIC, legacy shape,     STRICT: fail, AUDIT: pass
  Fixture 9  — EFFECT_GENERIC,       known-bad shape,  STRICT: fail, AUDIT: fail
  Fixture 10 — COMPUTE_GENERIC,      unknown node_type, STRICT: fail, AUDIT: fail

Real-corpus probe (TestRealCorpusFilesDoNotThrow):
  Walks real contract.yaml files from omnibase_core to confirm the pipeline
  accepts them without exception — pass/fail outcome is secondary to the
  absence of unhandled errors.

Pre-condition: Tasks 1-15 (OMN-9757) must be completed. Verified by importing
  the normalization module and checking MIGRATION_AUDIT is registered.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket
from omnibase_core.enums.enum_validator_mode import EnumValidatorMode
from omnibase_core.normalization.contract_normalizer import (
    compose_normalization_pipeline,
)
from omnibase_core.normalization.contract_validator import validate_contract_file

# ---------------------------------------------------------------------------
# Canonical ("clean") fixture factories
# ---------------------------------------------------------------------------


def _canonical_effect() -> dict[str, Any]:
    """Canonical EFFECT_GENERIC contract that passes strict mode."""
    return {
        "name": "node_e2e_effect",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "E2E verification effect node.",
        "node_type": "EFFECT_GENERIC",
        "input_model": "e2e.models.ModelE2EInput",
        "output_model": "e2e.models.ModelE2EOutput",
        "handler_routing": {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "routing_key": "e2e.run",
                    "handler_key": "handle_e2e_run",
                    "priority": 0,
                }
            ],
        },
        "io_operations": [
            {
                "operation_type": "write",
                "resource_type": "external_api",
                "resource_identifier": "e2e.api/run",
            }
        ],
    }


def _canonical_compute() -> dict[str, Any]:
    """Canonical COMPUTE_GENERIC contract that passes strict mode."""
    return {
        "name": "node_e2e_compute",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "E2E verification compute node.",
        "node_type": "COMPUTE_GENERIC",
        "input_model": "e2e.models.ModelE2EInput",
        "output_model": "e2e.models.ModelE2EOutput",
        "algorithm": {
            "algorithm_type": "deterministic",
            "factors": {
                "primary": {
                    "weight": 1.0,
                    "calculation_method": "direct",
                }
            },
        },
        "handler_routing": {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "routing_key": "e2e.compute",
                    "handler_key": "handle_e2e_compute",
                    "priority": 0,
                }
            ],
        },
        "performance": {"single_operation_max_ms": 100},
    }


def _canonical_reducer() -> dict[str, Any]:
    """Canonical REDUCER_GENERIC contract that passes strict mode."""
    return {
        "name": "node_e2e_reducer",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "E2E verification reducer node.",
        "node_type": "REDUCER_GENERIC",
        "input_model": "e2e.models.ModelE2EInput",
        "output_model": "e2e.models.ModelE2EOutput",
        "handler_routing": {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "routing_key": "e2e.reduce",
                    "handler_key": "handle_e2e_reduce",
                    "priority": 0,
                }
            ],
        },
    }


def _canonical_orchestrator() -> dict[str, Any]:
    """Canonical ORCHESTRATOR_GENERIC contract that passes strict mode."""
    return {
        "name": "node_e2e_orchestrator",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "E2E verification orchestrator node.",
        "node_type": "ORCHESTRATOR_GENERIC",
        "input_model": "e2e.models.ModelE2EInput",
        "output_model": "e2e.models.ModelE2EOutput",
        "handler_routing": {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "routing_key": "e2e.orchestrate",
                    "handler_key": "handle_e2e_orchestrate",
                    "priority": 0,
                }
            ],
        },
        "performance": {"single_operation_max_ms": 30000},
    }


# ---------------------------------------------------------------------------
# Legacy fixture factories (STRICT fails, MIGRATION_AUDIT passes)
# ---------------------------------------------------------------------------


def _legacy_effect() -> dict[str, Any]:
    """Legacy EFFECT_GENERIC: dict io_model refs, event_bus block, metadata."""
    return {
        "name": "node_legacy_effect",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "Legacy effect node for E2E migration_audit test.",
        "node_type": "EFFECT_GENERIC",
        "metadata": {"author": "legacy-team"},
        "contract_name": "node_legacy_effect",
        "event_bus": {"subscribe_topics": ["onex.evt.legacy.v1"]},
        "input_model": {"name": "ModelLegacyInput", "module": "legacy.models"},
        "output_model": {"name": "ModelLegacyOutput", "module": "legacy.models"},
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "handler_type": "legacy_run",
                    "supported_operations": ["legacy.run"],
                    "handler": {"name": "HandlerLegacy", "module": "legacy.handlers"},
                }
            ],
        },
        "io_operations": [
            {
                "operation_type": "write",
                "resource_type": "database",
                "resource_identifier": "legacy_db.legacy_table",
            }
        ],
    }


def _legacy_compute() -> dict[str, Any]:
    """Legacy COMPUTE_GENERIC: node_name alias, dict io_model refs, no algorithm."""
    return {
        "name": "node_legacy_compute",
        "node_name": "node_legacy_compute",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "Legacy compute node for E2E migration_audit test.",
        "node_type": "COMPUTE_GENERIC",
        "input_model": {"name": "ModelLegacyInput", "module": "legacy.compute.models"},
        "output_model": {
            "name": "ModelLegacyOutput",
            "module": "legacy.compute.models",
        },
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "handler_type": "legacy_compute",
                    "supported_operations": ["legacy.compute"],
                    "handler": {
                        "name": "HandlerLegacyCompute",
                        "module": "legacy.handlers",
                    },
                }
            ],
        },
        "performance": {"single_operation_max_ms": 200},
    }


def _legacy_reducer() -> dict[str, Any]:
    """Legacy REDUCER_GENERIC: metadata block, dict io_model refs."""
    return {
        "name": "node_legacy_reducer",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "Legacy reducer node for E2E migration_audit test.",
        "node_type": "REDUCER_GENERIC",
        "metadata": {"version": "0.1", "author": "legacy"},
        "input_model": {
            "name": "ModelLegacyReducerInput",
            "module": "legacy.reducer.models",
        },
        "output_model": {
            "name": "ModelLegacyReducerOutput",
            "module": "legacy.reducer.models",
        },
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "handler_type": "legacy_reduce",
                    "supported_operations": ["legacy.reduce"],
                    "handler": {
                        "name": "HandlerLegacyReducer",
                        "module": "legacy.handlers",
                    },
                }
            ],
        },
    }


def _legacy_orchestrator() -> dict[str, Any]:
    """Legacy ORCHESTRATOR_GENERIC: alias 'ORCHESTRATOR', event_bus block, dict io_model refs."""
    return {
        "name": "node_legacy_orchestrator",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "Legacy orchestrator node for E2E migration_audit test.",
        "node_type": "ORCHESTRATOR",
        "event_bus": {
            "subscribe_topics": ["onex.cmd.legacy.orchestrate.v1"],
            "publish_topics": ["onex.evt.legacy.orchestrated.v1"],
        },
        "input_model": {
            "name": "ModelLegacyOrchestrateInput",
            "module": "legacy.orchestrator.models",
        },
        "output_model": {
            "name": "ModelLegacyOrchestrateOutput",
            "module": "legacy.orchestrator.models",
        },
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "handler_type": "legacy_orchestrate",
                    "supported_operations": ["legacy.orchestrate"],
                    "handler": {
                        "name": "HandlerLegacyOrchestrate",
                        "module": "legacy.handlers",
                    },
                }
            ],
        },
        "performance": {"single_operation_max_ms": 30000},
    }


# ---------------------------------------------------------------------------
# Known-bad fixtures (fail both STRICT and MIGRATION_AUDIT)
# ---------------------------------------------------------------------------


def _known_bad_effect_missing_required_fields() -> dict[str, Any]:
    """EFFECT_GENERIC missing required ``name`` and ``contract_version`` fields.

    Normalization cannot synthesize these from any legacy shape — they are
    unconditionally required by the canonical model, so both STRICT and
    MIGRATION_AUDIT reject this contract.
    """
    return {
        "node_type": "EFFECT_GENERIC",
        "description": "Bad effect: missing name and contract_version.",
        "input_model": "bad.models.ModelBadInput",
        "output_model": "bad.models.ModelBadOutput",
        "io_operations": [
            {
                "operation_type": "write",
                "resource_type": "database",
                "resource_identifier": "bad_db.table",
            }
        ],
    }


def _known_bad_unknown_node_type() -> dict[str, Any]:
    """COMPUTE_GENERIC with an unmapped node_type — rejected at model-registry lookup."""
    return {
        "name": "node_bad_unknown_type",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "Bad contract: unknown node_type.",
        "node_type": "EXOTIC_NODE_TYPE",
        "input_model": "bad.models.ModelBadInput",
        "output_model": "bad.models.ModelBadOutput",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_contract(
    tmp_path: Path,
    body: dict[str, Any],
    sub: str = "nodes",
    dir_name: str | None = None,
) -> Path:
    name = dir_name if dir_name is not None else body["name"]
    p = tmp_path / sub / name / "contract.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(yaml.safe_dump(body))
    return p


# ---------------------------------------------------------------------------
# Core prerequisite guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrerequisitesPresent:
    """Confirms Tasks 1-15 prerequisites are importable before E2E runs."""

    def test_normalization_module_importable(self) -> None:
        from omnibase_core.normalization import contract_normalizer, contract_validator

        assert hasattr(contract_normalizer, "compose_normalization_pipeline")
        assert hasattr(contract_validator, "validate_contract_file")

    def test_migration_audit_mode_registered(self) -> None:
        assert EnumValidatorMode.MIGRATION_AUDIT.value == "migration_audit"

    def test_compose_pipeline_callable(self) -> None:
        result = compose_normalization_pipeline(
            {"name": "test", "node_type": "EFFECT_GENERIC"}
        )
        assert isinstance(result, dict)
        assert result["name"] == "test"


# ---------------------------------------------------------------------------
# Fixtures 1-4: Canonical contracts — pass STRICT and MIGRATION_AUDIT
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCanonicalContracts:
    """Fixtures 1-4: well-formed canonical contracts pass both modes."""

    def test_fixture_1_canonical_effect_strict(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _canonical_effect())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is True, f"Fixture 1 STRICT failed: {result.errors}"
        assert result.normalized is False
        assert result.bucket is EnumContractBucket.NODE_ROOT_CONTRACT

    def test_fixture_1_canonical_effect_audit(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _canonical_effect())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"Fixture 1 AUDIT failed: {result.errors}"
        assert result.normalized is True

    def test_fixture_2_canonical_compute_strict(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _canonical_compute())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is True, f"Fixture 2 STRICT failed: {result.errors}"
        assert result.normalized is False
        assert result.bucket is EnumContractBucket.NODE_ROOT_CONTRACT

    def test_fixture_2_canonical_compute_audit(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _canonical_compute())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"Fixture 2 AUDIT failed: {result.errors}"
        assert result.normalized is True

    def test_fixture_3_canonical_reducer_strict(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _canonical_reducer())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is True, f"Fixture 3 STRICT failed: {result.errors}"
        assert result.normalized is False
        assert result.bucket is EnumContractBucket.NODE_ROOT_CONTRACT

    def test_fixture_3_canonical_reducer_audit(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _canonical_reducer())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"Fixture 3 AUDIT failed: {result.errors}"
        assert result.normalized is True

    def test_fixture_4_canonical_orchestrator_strict(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _canonical_orchestrator())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is True, f"Fixture 4 STRICT failed: {result.errors}"
        assert result.normalized is False
        assert result.bucket is EnumContractBucket.NODE_ROOT_CONTRACT

    def test_fixture_4_canonical_orchestrator_audit(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _canonical_orchestrator())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"Fixture 4 AUDIT failed: {result.errors}"
        assert result.normalized is True


# ---------------------------------------------------------------------------
# Fixtures 5-8: Legacy contracts — fail STRICT, pass MIGRATION_AUDIT
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLegacyContractsMigrationAudit:
    """Fixtures 5-8: legacy-shaped contracts pass migration_audit after normalization."""

    def test_fixture_5_legacy_effect_strict_fails(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_effect())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is False, "Legacy effect unexpectedly passed STRICT mode"
        assert len(result.errors) > 0

    def test_fixture_5_legacy_effect_audit_passes(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_effect())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"Fixture 5 AUDIT failed: {result.errors}"
        assert result.normalized is True

    def test_fixture_6_legacy_compute_strict_fails(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_compute())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is False, "Legacy compute unexpectedly passed STRICT mode"

    def test_fixture_6_legacy_compute_audit_passes(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_compute())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"Fixture 6 AUDIT failed: {result.errors}"
        assert result.normalized is True

    def test_fixture_7_legacy_reducer_strict_fails(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_reducer())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is False, "Legacy reducer unexpectedly passed STRICT mode"

    def test_fixture_7_legacy_reducer_audit_passes(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_reducer())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"Fixture 7 AUDIT failed: {result.errors}"
        assert result.normalized is True

    def test_fixture_8_legacy_orchestrator_strict_fails(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_orchestrator())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is False, (
            "Legacy orchestrator unexpectedly passed STRICT mode"
        )

    def test_fixture_8_legacy_orchestrator_audit_passes(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _legacy_orchestrator())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is True, f"Fixture 8 AUDIT failed: {result.errors}"
        assert result.normalized is True


# ---------------------------------------------------------------------------
# Fixtures 9-10: Known-bad contracts — fail both modes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKnownBadContracts:
    """Fixtures 9-10: substantive schema violations fail both STRICT and MIGRATION_AUDIT."""

    def test_fixture_9_bad_effect_strict_fails(self, tmp_path: Path) -> None:
        path = _write_contract(
            tmp_path,
            _known_bad_effect_missing_required_fields(),
            dir_name="node_bad_effect",
        )
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is False
        assert any("name" in e or "contract_version" in e for e in result.errors), (
            result.errors
        )

    def test_fixture_9_bad_effect_audit_fails(self, tmp_path: Path) -> None:
        """Missing ``name`` and ``contract_version`` are unconditionally required — normalization
        cannot synthesize them, so MIGRATION_AUDIT also rejects this contract."""
        path = _write_contract(
            tmp_path,
            _known_bad_effect_missing_required_fields(),
            dir_name="node_bad_effect",
        )
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is False
        assert result.normalized is True

    def test_fixture_10_unknown_node_type_strict_fails(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _known_bad_unknown_node_type())
        result = validate_contract_file(path, EnumValidatorMode.STRICT)
        assert result.passed is False
        assert any("node_type" in e for e in result.errors), result.errors

    def test_fixture_10_unknown_node_type_audit_fails(self, tmp_path: Path) -> None:
        path = _write_contract(tmp_path, _known_bad_unknown_node_type())
        result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
        assert result.passed is False
        assert any("node_type" in e for e in result.errors), result.errors


# ---------------------------------------------------------------------------
# Pipeline invariant assertions (shared across all fixtures)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineInvariants:
    """Cross-cutting invariants that every report from the pipeline must satisfy."""

    @pytest.mark.parametrize(
        ("factory", "dir_name", "mode", "expect_pass"),
        [
            (_canonical_effect, None, EnumValidatorMode.STRICT, True),
            (_canonical_compute, None, EnumValidatorMode.STRICT, True),
            (_canonical_reducer, None, EnumValidatorMode.STRICT, True),
            (_canonical_orchestrator, None, EnumValidatorMode.STRICT, True),
            (_legacy_effect, None, EnumValidatorMode.MIGRATION_AUDIT, True),
            (_legacy_compute, None, EnumValidatorMode.MIGRATION_AUDIT, True),
            (_legacy_reducer, None, EnumValidatorMode.MIGRATION_AUDIT, True),
            (_legacy_orchestrator, None, EnumValidatorMode.MIGRATION_AUDIT, True),
            (
                _known_bad_effect_missing_required_fields,
                "node_bad_effect",
                EnumValidatorMode.STRICT,
                False,
            ),
            (
                _known_bad_unknown_node_type,
                None,
                EnumValidatorMode.MIGRATION_AUDIT,
                False,
            ),
        ],
        ids=[
            "canonical-effect-strict",
            "canonical-compute-strict",
            "canonical-reducer-strict",
            "canonical-orchestrator-strict",
            "legacy-effect-audit",
            "legacy-compute-audit",
            "legacy-reducer-audit",
            "legacy-orchestrator-audit",
            "bad-effect-strict",
            "bad-unknown-type-audit",
        ],
    )
    def test_report_fields_always_populated(
        self,
        factory: Any,
        dir_name: str | None,
        mode: EnumValidatorMode,
        expect_pass: bool,
        tmp_path: Path,
    ) -> None:
        path = _write_contract(tmp_path, factory(), dir_name=dir_name)
        result = validate_contract_file(path, mode)
        assert result.path == path
        assert result.mode is mode
        assert isinstance(result.passed, bool)
        assert isinstance(result.errors, list)
        assert result.bucket is not None
        # Outcome correctness is verified in TestCanonicalContracts,
        # TestLegacyContractsMigrationAudit, and TestKnownBadContracts.
        # This test only asserts report fields are structurally populated.
        _ = expect_pass

    def test_strict_mode_normalized_is_always_false(self, tmp_path: Path) -> None:
        """STRICT mode never sets normalized=True regardless of contract shape."""
        cases: list[tuple[Any, str | None]] = [
            (_canonical_effect, None),
            (_canonical_compute, None),
            (_legacy_effect, None),
            (_known_bad_effect_missing_required_fields, "node_bad_effect"),
        ]
        for factory, dir_name in cases:
            path = _write_contract(tmp_path, factory(), dir_name=dir_name)
            result = validate_contract_file(path, EnumValidatorMode.STRICT)
            assert result.normalized is False, (
                f"{factory.__name__}: STRICT mode set normalized=True"
            )

    def test_migration_audit_normalized_is_always_true_for_node_root(
        self, tmp_path: Path
    ) -> None:
        """MIGRATION_AUDIT mode always sets normalized=True for node-root contracts."""
        cases: list[tuple[Any, str | None]] = [
            (_canonical_effect, None),
            (_canonical_compute, None),
            (_legacy_effect, None),
            (_known_bad_effect_missing_required_fields, "node_bad_effect"),
        ]
        for factory, dir_name in cases:
            path = _write_contract(tmp_path, factory(), dir_name=dir_name)
            result = validate_contract_file(path, EnumValidatorMode.MIGRATION_AUDIT)
            if result.bucket is EnumContractBucket.NODE_ROOT_CONTRACT:
                assert result.normalized is True, (
                    f"{factory.__name__}: MIGRATION_AUDIT should set normalized=True"
                )

    def test_failed_results_always_have_errors(self, tmp_path: Path) -> None:
        """Any failed report must carry at least one error string."""
        cases: list[tuple[Any, str | None, EnumValidatorMode]] = [
            (_legacy_effect, None, EnumValidatorMode.STRICT),
            (
                _known_bad_effect_missing_required_fields,
                "node_bad_effect",
                EnumValidatorMode.STRICT,
            ),
            (_known_bad_unknown_node_type, None, EnumValidatorMode.MIGRATION_AUDIT),
        ]
        for factory, dir_name, mode in cases:
            path = _write_contract(tmp_path, factory(), dir_name=dir_name)
            result = validate_contract_file(path, mode)
            if not result.passed:
                assert len(result.errors) > 0, (
                    f"{factory.__name__}: failed result has empty errors list"
                )

    def test_passed_results_have_no_errors(self, tmp_path: Path) -> None:
        """Any passed report must carry an empty errors list."""
        for factory, mode in (
            (_canonical_effect, EnumValidatorMode.STRICT),
            (_canonical_compute, EnumValidatorMode.STRICT),
            (_canonical_reducer, EnumValidatorMode.STRICT),
            (_canonical_orchestrator, EnumValidatorMode.STRICT),
            (_legacy_effect, EnumValidatorMode.MIGRATION_AUDIT),
        ):
            path = _write_contract(tmp_path, factory())
            result = validate_contract_file(path, mode)
            if result.passed:
                assert result.errors == [], (
                    f"{factory.__name__}: passed result has non-empty errors: {result.errors}"
                )


# ---------------------------------------------------------------------------
# Real corpus probe — omnibase_core canonical contracts
# ---------------------------------------------------------------------------


def _omni_home() -> Path | None:
    omni_home = os.environ.get("OMNI_HOME")
    if omni_home:
        return Path(omni_home)
    return None


def _corpus_contracts() -> list[Path]:
    omni_home = _omni_home()
    if omni_home is None:
        return []
    core_nodes = omni_home / "omnibase_core" / "src" / "omnibase_core" / "nodes"
    if not core_nodes.is_dir():
        return []
    return sorted(core_nodes.glob("*/contract.yaml"))


_HAS_CORPUS = bool(_corpus_contracts())


@pytest.mark.unit
@pytest.mark.skipif(
    not _HAS_CORPUS, reason="OMNI_HOME not set or omnibase_core nodes not found"
)
class TestRealCorpusFilesDoNotThrow:
    """Probes real omnibase_core contract.yaml files to confirm no unhandled exceptions.

    The validation outcome (pass/fail) is an invariant checked separately in
    TestPipelineInvariants. This class verifies the absence of Python exceptions,
    meaning the pipeline gracefully handles every known corpus shape.
    """

    @pytest.mark.parametrize(
        "contract_path",
        _corpus_contracts(),
        ids=[p.parent.name for p in _corpus_contracts()],
    )
    def test_strict_mode_does_not_raise(self, contract_path: Path) -> None:
        result = validate_contract_file(contract_path, EnumValidatorMode.STRICT)
        assert result is not None
        assert isinstance(result.passed, bool)
        assert isinstance(result.errors, list)

    @pytest.mark.parametrize(
        "contract_path",
        _corpus_contracts(),
        ids=[p.parent.name for p in _corpus_contracts()],
    )
    def test_migration_audit_mode_does_not_raise(self, contract_path: Path) -> None:
        result = validate_contract_file(
            contract_path, EnumValidatorMode.MIGRATION_AUDIT
        )
        assert result is not None
        assert isinstance(result.passed, bool)
        assert isinstance(result.errors, list)
        assert (
            result.normalized is True
            or result.bucket is not EnumContractBucket.NODE_ROOT_CONTRACT
        )
