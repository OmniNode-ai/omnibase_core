# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelConcurrencyContractSpec (OMN-7839).

Covers:
- Defaults (``max_parallel=1``, ``model_concurrency_aware=False``).
- Positive construction with explicit values.
- Rejection of invalid values (``max_parallel < 1``, wrong types).
- Rejection of unknown fields (``extra='forbid'``).
- Serialization roundtrip.
- Integration with ``ModelContractBase`` via a concrete subclass:
  absent concurrency block -> ``None``; present block validates.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts import (
    ModelAlgorithmConfig,
    ModelAlgorithmFactorConfig,
    ModelContractCompute,
    ModelPerformanceRequirements,
)
from omnibase_core.models.contracts.model_concurrency_contract_spec import (
    ModelConcurrencyContractSpec,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _minimal_algorithm() -> ModelAlgorithmConfig:
    return ModelAlgorithmConfig(
        algorithm_type="test_algorithm",
        factors={
            "factor1": ModelAlgorithmFactorConfig(
                weight=1.0,
                calculation_method="default",
            ),
        },
    )


def _minimal_performance() -> ModelPerformanceRequirements:
    return ModelPerformanceRequirements(single_operation_max_ms=1000)


@pytest.mark.unit
class TestModelConcurrencyContractSpecDefaults:
    """Default-field behavior."""

    def test_default_values(self) -> None:
        spec = ModelConcurrencyContractSpec()
        assert spec.max_parallel == 1
        assert spec.model_concurrency_aware is False

    def test_explicit_values(self) -> None:
        spec = ModelConcurrencyContractSpec(
            max_parallel=5,
            model_concurrency_aware=True,
        )
        assert spec.max_parallel == 5
        assert spec.model_concurrency_aware is True


@pytest.mark.unit
class TestModelConcurrencyContractSpecValidation:
    """Negative-path validation."""

    def test_max_parallel_below_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelConcurrencyContractSpec(max_parallel=0)

    def test_max_parallel_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelConcurrencyContractSpec(max_parallel=-3)

    def test_unknown_field_ignored_for_forward_compat(self) -> None:
        """Contract-facing models use ``extra='ignore'`` so future YAML
        contracts declaring fields this model doesn't know about still load."""
        spec = ModelConcurrencyContractSpec(max_parallel=2, bogus_field=True)  # type: ignore[call-arg]
        assert spec.max_parallel == 2
        assert not hasattr(spec, "bogus_field")

    def test_wrong_type_for_model_concurrency_aware_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelConcurrencyContractSpec(model_concurrency_aware="not-a-bool")  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelConcurrencyContractSpecSerialization:
    """Roundtrip dict <-> model."""

    def test_dump_and_reload(self) -> None:
        original = ModelConcurrencyContractSpec(
            max_parallel=8,
            model_concurrency_aware=True,
        )
        payload = original.model_dump()
        assert payload == {
            "max_parallel": 8,
            "model_concurrency_aware": True,
        }
        reloaded = ModelConcurrencyContractSpec.model_validate(payload)
        assert reloaded == original


@pytest.mark.unit
class TestConcurrencyBlockOnContractBase:
    """Exercises the optional ``concurrency`` field on a concrete contract subclass."""

    @staticmethod
    def _base_contract_kwargs() -> dict[str, object]:
        return {
            "name": "node_test_concurrency",
            "contract_version": ModelSemVer(major=1, minor=0, patch=0),
            "description": "Test contract for concurrency block validation.",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "omnibase_core.models.test.ModelInput",
            "output_model": "omnibase_core.models.test.ModelOutput",
            "algorithm": _minimal_algorithm(),
            "performance": _minimal_performance(),
        }

    def test_contract_without_concurrency_defaults_to_none(self) -> None:
        contract = ModelContractCompute(**self._base_contract_kwargs())
        assert contract.concurrency is None

    def test_contract_with_concurrency_block_validates(self) -> None:
        kwargs = self._base_contract_kwargs()
        kwargs["concurrency"] = ModelConcurrencyContractSpec(
            max_parallel=4,
            model_concurrency_aware=True,
        )
        contract = ModelContractCompute(**kwargs)
        assert contract.concurrency is not None
        assert contract.concurrency.max_parallel == 4
        assert contract.concurrency.model_concurrency_aware is True

    def test_contract_accepts_concurrency_dict_from_yaml(self) -> None:
        """Dict input (as produced by YAML loading) is coerced to the model."""
        kwargs = self._base_contract_kwargs()
        kwargs["concurrency"] = {
            "max_parallel": 2,
            "model_concurrency_aware": False,
        }
        contract = ModelContractCompute(**kwargs)
        assert isinstance(contract.concurrency, ModelConcurrencyContractSpec)
        assert contract.concurrency.max_parallel == 2
        assert contract.concurrency.model_concurrency_aware is False

    def test_contract_rejects_invalid_concurrency_block(self) -> None:
        kwargs = self._base_contract_kwargs()
        kwargs["concurrency"] = {"max_parallel": 0}
        with pytest.raises(ValidationError):
            ModelContractCompute(**kwargs)
