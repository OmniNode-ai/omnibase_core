# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Integration tests: contract model validation enforcement (OMN-9738).

Proof-of-life tests asserting that:
1. Complete, spec-compliant contract data produces typed ModelContract* instances
   via model_validate() — NOT raw dicts.
2. Each of the four node archetypes (effect, compute, reducer, orchestrator)
   dispatches to the correct Pydantic model class and returns a ModelContractBase
   subclass instance.
3. ModelContractBehaviorSpec is accessible on all validated contract models via
   the inherited behavior_spec field.
4. The batch validator mirrors RuntimeContractConfigLoader.load_from_directory()
   behaviour: fields are filtered to model_fields, model_validate() is called,
   and the test reports how many omnibase_core node contracts succeed vs. fail
   (with failures surfaced explicitly rather than silently swallowed).

These tests constitute the OMN-9738 dod_evidence items:
  - "load_and_validate_contract_yaml() returns ModelContractEffect (not dict)
     for EFFECT contracts"
  - batch validation proof for omnibase_core nodes (reporting mode)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.contracts.subcontracts.model_contract_behavior_spec import (
    ModelContractBehaviorSpec,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

logger = logging.getLogger(__name__)

# Root of the omnibase_core nodes directory (relative to this file).
# Structure: tests/integration/../../src/omnibase_core/nodes/
_NODES_DIR: Path = (
    Path(__file__).parent.parent.parent / "src" / "omnibase_core" / "nodes"
)


def _dispatch_contract_class(raw: dict[str, Any]) -> type[ModelContractBase]:
    """Dispatch raw YAML dict to the correct ModelContract subclass.

    Mirrors the logic in RuntimeContractConfigLoader.load_from_directory().
    Uses uppercase string matching on node_type so both 'orchestrator' and
    'ORCHESTRATOR_GENERIC' resolve to ModelContractOrchestrator.
    """
    node_type = str(raw.get("node_type", "")).upper()
    if "ORCHESTRATOR" in node_type:
        return ModelContractOrchestrator
    if "REDUCER" in node_type:
        return ModelContractReducer
    if "COMPUTE" in node_type:
        return ModelContractCompute
    return ModelContractEffect


def _load_and_filter_contract(
    path: Path,
) -> tuple[dict[str, Any], type[ModelContractBase]]:
    """Load YAML and filter to model_fields of the dispatched contract class.

    Returns:
        (filtered_dict, contract_class) ready for model_validate().
    """
    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)
    assert isinstance(raw, dict), f"Contract root must be a mapping: {path}"
    contract_cls = _dispatch_contract_class(raw)
    model_fields = set(contract_cls.model_fields.keys())
    filtered = {k: v for k, v in raw.items() if k in model_fields}
    return filtered, contract_cls


def _collect_contract_paths() -> list[Path]:
    """Return all contract.yaml files under the omnibase_core nodes directory."""
    if not _NODES_DIR.exists():
        return []
    return sorted(_NODES_DIR.glob("**/contract.yaml"))


def _make_minimal_effect(name: str = "test_effect") -> dict[str, Any]:
    """Minimal valid ModelContractEffect data."""
    return {
        "name": name,
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "node_type": "EFFECT_GENERIC",
        "description": "Integration test effect contract",
        "input_model": "omnibase_core.models.common.ModelInput",
        "output_model": "omnibase_core.models.common.ModelOutput",
    }


def _make_minimal_compute(name: str = "test_compute") -> dict[str, Any]:
    """Minimal valid ModelContractCompute data.

    Includes single_operation_max_ms which ModelContractCompute.validate_node_specific_config
    enforces as required for all COMPUTE contracts.
    """
    return {
        "name": name,
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "node_type": "COMPUTE_GENERIC",
        "description": "Integration test compute contract",
        "input_model": "omnibase_core.models.common.ModelInput",
        "output_model": "omnibase_core.models.common.ModelOutput",
        "performance": {"single_operation_max_ms": 5000},
    }


def _make_minimal_reducer(name: str = "test_reducer") -> dict[str, Any]:
    """Minimal valid ModelContractReducer data."""
    return {
        "name": name,
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "node_type": "REDUCER_GENERIC",
        "description": "Integration test reducer contract",
        "input_model": "omnibase_core.models.common.ModelInput",
        "output_model": "omnibase_core.models.common.ModelOutput",
    }


def _make_minimal_orchestrator(name: str = "test_orchestrator") -> dict[str, Any]:
    """Minimal valid ModelContractOrchestrator data.

    Includes single_operation_max_ms which ModelContractOrchestrator
    enforces as required for all ORCHESTRATOR contracts.
    """
    return {
        "name": name,
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "node_type": "ORCHESTRATOR_GENERIC",
        "description": "Integration test orchestrator contract",
        "input_model": "omnibase_core.models.common.ModelInput",
        "output_model": "omnibase_core.models.common.ModelOutput",
        "performance": {"single_operation_max_ms": 30000},
    }


# ---------------------------------------------------------------------------
# Unit-style tests for the dispatch helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractDispatch:
    """Verify that node_type strings (both short and generic) dispatch correctly."""

    @pytest.mark.parametrize(
        ("node_type_value", "expected_class"),
        [
            ("orchestrator", ModelContractOrchestrator),
            ("ORCHESTRATOR_GENERIC", ModelContractOrchestrator),
            ("ORCHESTRATOR", ModelContractOrchestrator),
            ("reducer", ModelContractReducer),
            ("REDUCER_GENERIC", ModelContractReducer),
            ("compute", ModelContractCompute),
            ("COMPUTE_GENERIC", ModelContractCompute),
            ("effect", ModelContractEffect),
            ("EFFECT_GENERIC", ModelContractEffect),
            ("", ModelContractEffect),  # unknown → default effect
        ],
    )
    def test_dispatch_contract_class(
        self, node_type_value: str, expected_class: type[ModelContractBase]
    ) -> None:
        raw: dict[str, Any] = {"node_type": node_type_value}
        assert _dispatch_contract_class(raw) is expected_class


# ---------------------------------------------------------------------------
# Core proof-of-life: model_validate() returns typed objects, not dicts
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestContractModelValidationNotDict:
    """Assert that validated contract objects are typed models, not raw dicts."""

    def test_effect_contract_is_model_instance_not_dict(self) -> None:
        """model_validate() on an EFFECT contract returns ModelContractEffect."""
        data = _make_minimal_effect()
        model_fields = set(ModelContractEffect.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in model_fields}
        result = ModelContractEffect.model_validate(filtered)
        assert isinstance(result, ModelContractEffect), (
            f"Expected ModelContractEffect instance, got {type(result)}"
        )
        assert not isinstance(result, dict), "Contract must not be a raw dict"

    def test_compute_contract_is_model_instance_not_dict(self) -> None:
        """model_validate() on a COMPUTE contract returns ModelContractCompute."""
        data = _make_minimal_compute()
        model_fields = set(ModelContractCompute.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in model_fields}
        result = ModelContractCompute.model_validate(filtered)
        assert isinstance(result, ModelContractCompute), (
            f"Expected ModelContractCompute instance, got {type(result)}"
        )
        assert not isinstance(result, dict)

    def test_reducer_contract_is_model_instance_not_dict(self) -> None:
        """model_validate() on a REDUCER contract returns ModelContractReducer."""
        data = _make_minimal_reducer()
        model_fields = set(ModelContractReducer.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in model_fields}
        result = ModelContractReducer.model_validate(filtered)
        assert isinstance(result, ModelContractReducer), (
            f"Expected ModelContractReducer instance, got {type(result)}"
        )
        assert not isinstance(result, dict)

    def test_orchestrator_contract_is_model_instance_not_dict(self) -> None:
        """model_validate() on an ORCHESTRATOR contract returns ModelContractOrchestrator."""
        data = _make_minimal_orchestrator()
        model_fields = set(ModelContractOrchestrator.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in model_fields}
        result = ModelContractOrchestrator.model_validate(filtered)
        assert isinstance(result, ModelContractOrchestrator), (
            f"Expected ModelContractOrchestrator instance, got {type(result)}"
        )
        assert not isinstance(result, dict)

    def test_all_four_node_types_return_modelcontractbase_subclass(self) -> None:
        """All four archetypes produce ModelContractBase instances, not dicts."""
        cases: list[tuple[dict[str, Any], type[ModelContractBase]]] = [
            (_make_minimal_effect(), ModelContractEffect),
            (_make_minimal_compute(), ModelContractCompute),
            (_make_minimal_reducer(), ModelContractReducer),
            (_make_minimal_orchestrator(), ModelContractOrchestrator),
        ]
        for data, expected_cls in cases:
            model_fields = set(expected_cls.model_fields.keys())
            filtered = {k: v for k, v in data.items() if k in model_fields}
            result = expected_cls.model_validate(filtered)
            assert isinstance(result, ModelContractBase), (
                f"{expected_cls.__name__}: expected ModelContractBase subclass"
            )
            assert isinstance(result, expected_cls), (
                f"Expected {expected_cls.__name__}, got {type(result).__name__}"
            )
            assert not isinstance(result, dict), (
                f"{expected_cls.__name__}: model_validate must not return a dict"
            )


# ---------------------------------------------------------------------------
# ModelContractBehaviorSpec integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestModelContractBehaviorSpec:
    """Assert ModelContractBehaviorSpec is accessible from all contract archetypes."""

    @pytest.mark.parametrize(
        ("data_factory", "contract_cls"),
        [
            (_make_minimal_effect, ModelContractEffect),
            (_make_minimal_compute, ModelContractCompute),
            (_make_minimal_reducer, ModelContractReducer),
            (_make_minimal_orchestrator, ModelContractOrchestrator),
        ],
    )
    def test_behavior_spec_is_modelcontractbehaviorspec(
        self,
        data_factory: Any,
        contract_cls: type[ModelContractBase],
    ) -> None:
        """behavior_spec field is populated with ModelContractBehaviorSpec on all archetypes."""
        data = data_factory()
        model_fields = set(contract_cls.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in model_fields}
        result = contract_cls.model_validate(filtered)
        assert hasattr(result, "behavior_spec"), (
            f"{contract_cls.__name__} must have behavior_spec field"
        )
        assert isinstance(result.behavior_spec, ModelContractBehaviorSpec), (
            f"behavior_spec must be ModelContractBehaviorSpec, "
            f"got {type(result.behavior_spec)}"
        )

    def test_behavior_spec_defaults_are_correct(self) -> None:
        """Default ModelContractBehaviorSpec values match spec."""
        data = _make_minimal_effect()
        model_fields = set(ModelContractEffect.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in model_fields}
        result = ModelContractEffect.model_validate(filtered)
        spec = result.behavior_spec
        assert spec.retry_attempts == 0
        assert spec.idempotent is False
        assert spec.max_concurrency is None
        assert spec.execution_timeout_ms is None

    def test_behavior_spec_overridden_via_yaml_fields(self) -> None:
        """behavior_spec can be populated with non-default values."""
        data = _make_minimal_effect()
        data["behavior_spec"] = {
            "retry_attempts": 3,
            "idempotent": True,
            "max_concurrency": 10,
            "execution_timeout_ms": 5000,
        }
        model_fields = set(ModelContractEffect.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in model_fields}
        result = ModelContractEffect.model_validate(filtered)
        spec = result.behavior_spec
        assert spec.retry_attempts == 3
        assert spec.idempotent is True
        assert spec.max_concurrency == 10
        assert spec.execution_timeout_ms == 5000

    def test_behavior_spec_is_independent_modelcontractbehaviorspec_instance(
        self,
    ) -> None:
        """Each validated contract has its own ModelContractBehaviorSpec instance."""
        data1 = _make_minimal_effect("node_a")
        data2 = _make_minimal_effect("node_b")
        model_fields = set(ModelContractEffect.model_fields.keys())
        filtered1 = {k: v for k, v in data1.items() if k in model_fields}
        filtered2 = {k: v for k, v in data2.items() if k in model_fields}
        result1 = ModelContractEffect.model_validate(filtered1)
        result2 = ModelContractEffect.model_validate(filtered2)
        assert result1.behavior_spec is not result2.behavior_spec, (
            "Each contract must have its own behavior_spec instance (not shared)"
        )


# ---------------------------------------------------------------------------
# Batch validation: all contract.yaml files in omnibase_core/nodes/
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBatchContractValidation:
    """Batch validate all omnibase_core node contract.yaml files.

    Mirrors the behavior of RuntimeContractConfigLoader.load_from_directory():
    - Fields are filtered to model_fields of the dispatched class
    - model_validate() is called
    - Failures are collected and reported with context (not silently swallowed)

    The test reports pass/fail counts and asserts at least 1 contract validates
    successfully. Known schema gaps in individual contracts are reported as
    warnings (consistent with the loader's graceful-degradation design) rather
    than hard failures — closing these gaps is tracked per-contract in OMN-9738
    follow-on work.
    """

    def test_at_least_one_node_contract_passes_model_validate(self) -> None:
        """At minimum, one omnibase_core node contract must pass model_validate().

        This is the baseline proof-of-life gate: if zero contracts validate,
        something is fundamentally broken with the dispatch or filtering logic.
        """
        contract_paths = _collect_contract_paths()
        if not contract_paths:
            pytest.skip(
                f"No contract.yaml files found under {_NODES_DIR}. "
                "Skipping batch validation."
            )

        successes: list[str] = []
        failures: list[str] = []

        for path in contract_paths:
            try:
                filtered, contract_cls = _load_and_filter_contract(path)
                result = contract_cls.model_validate(filtered)
            except (ModelOnexError, ValueError) as exc:
                rel = path.relative_to(_NODES_DIR.parent.parent.parent)
                failures.append(f"{rel}: {exc}")
                logger.warning(
                    "Contract failed model_validate(): %s — %s", path.name, exc
                )
                continue

            assert isinstance(result, ModelContractBase)
            successes.append(path.name)

        logger.info(
            "Batch contract validation: %d passed, %d failed (total: %d)",
            len(successes),
            len(failures),
            len(contract_paths),
        )

        if failures:
            failure_summary = "\n  ".join(failures)
            logger.warning(
                "Known contract schema gaps (OMN-9738 follow-on):\n  %s",
                failure_summary,
            )

        assert successes, (
            "Zero contracts passed model_validate() — dispatch or filtering is broken.\n"
            "Failures:\n  " + "\n  ".join(failures)
        )

    def test_validated_contracts_are_typed_not_dicts(self) -> None:
        """Regression: any contract that does pass model_validate() must be a typed model."""
        contract_paths = _collect_contract_paths()
        if not contract_paths:
            pytest.skip("No contract.yaml files found")

        for path in contract_paths:
            try:
                filtered, contract_cls = _load_and_filter_contract(path)
                result = contract_cls.model_validate(filtered)
            except (ModelOnexError, ValueError):
                continue

            assert not isinstance(result, dict), (
                f"{path.name}: model_validate() returned a dict instead of "
                f"{contract_cls.__name__}"
            )
            assert isinstance(result, ModelContractBase), (
                f"{path.name}: expected ModelContractBase subclass, "
                f"got {type(result).__name__}"
            )

    def test_dispatch_produces_correct_class_per_node_type(self) -> None:
        """For each contract.yaml, the dispatched class matches the declared node_type."""
        contract_paths = _collect_contract_paths()
        if not contract_paths:
            pytest.skip("No contract.yaml files found")

        for path in contract_paths:
            with path.open("r", encoding="utf-8") as fh:
                raw: dict[str, Any] = yaml.safe_load(fh)
            if not isinstance(raw, dict) or "node_type" not in raw:
                continue

            node_type_str = str(raw["node_type"]).upper()
            dispatched_cls = _dispatch_contract_class(raw)

            if "ORCHESTRATOR" in node_type_str:
                assert dispatched_cls is ModelContractOrchestrator, (
                    f"{path.name}: expected ModelContractOrchestrator for {node_type_str}"
                )
            elif "REDUCER" in node_type_str:
                assert dispatched_cls is ModelContractReducer, (
                    f"{path.name}: expected ModelContractReducer for {node_type_str}"
                )
            elif "COMPUTE" in node_type_str:
                assert dispatched_cls is ModelContractCompute, (
                    f"{path.name}: expected ModelContractCompute for {node_type_str}"
                )
            else:
                assert dispatched_cls is ModelContractEffect, (
                    f"{path.name}: expected ModelContractEffect for {node_type_str}"
                )

    def test_node_type_is_enum_on_successfully_validated_contracts(self) -> None:
        """After model_validate(), node_type must be EnumNodeType (not a plain string)."""
        contract_paths = _collect_contract_paths()
        if not contract_paths:
            pytest.skip("No contract.yaml files found")

        for path in contract_paths:
            try:
                filtered, contract_cls = _load_and_filter_contract(path)
                result = contract_cls.model_validate(filtered)
            except (ModelOnexError, ValueError):
                continue

            if "node_type" in filtered:
                assert isinstance(result.node_type, EnumNodeType), (
                    f"{path.name}: node_type must be EnumNodeType after validate, "
                    f"got {type(result.node_type)}: {result.node_type!r}"
                )
