# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for feature_flags field on ModelContractBase."""

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_feature_flag_category import EnumFeatureFlagCategory
from omnibase_core.models.contracts import (
    ModelAlgorithmConfig,
    ModelAlgorithmFactorConfig,
    ModelContractCompute,
    ModelPerformanceRequirements,
)
from omnibase_core.models.contracts.model_contract_feature_flag import (
    ModelContractFeatureFlag,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _create_minimal_compute(**overrides: object) -> ModelContractCompute:
    """Create a minimal valid ModelContractCompute for testing."""
    defaults: dict[str, object] = {
        "name": "test_node",
        "contract_version": ModelSemVer(major=1, minor=0, patch=0),
        "description": "Test compute contract",
        "node_type": EnumNodeType.COMPUTE_GENERIC,
        "input_model": "omnibase_core.models.ModelTestInput",
        "output_model": "omnibase_core.models.ModelTestOutput",
        "algorithm": ModelAlgorithmConfig(
            algorithm_type="test",
            factors={
                "f1": ModelAlgorithmFactorConfig(
                    weight=1.0,
                    calculation_method="default",
                ),
            },
        ),
        "performance": ModelPerformanceRequirements(single_operation_max_ms=1000),
    }
    defaults.update(overrides)
    return ModelContractCompute(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestContractBaseFeatureFlags:
    """Tests for feature_flags field on ModelContractBase."""

    @pytest.mark.unit
    def test_empty_feature_flags_default(self) -> None:
        """Contracts without feature_flags default to empty list."""
        contract = _create_minimal_compute()
        assert contract.feature_flags == []

    @pytest.mark.unit
    def test_populated_feature_flags(self) -> None:
        """Contracts can declare feature flags."""
        flags = [
            ModelContractFeatureFlag(
                name="pattern_enforcement",
                env_var="ENABLE_PATTERN_ENFORCEMENT",
                category=EnumFeatureFlagCategory.INTELLIGENCE,
            ),
        ]
        contract = _create_minimal_compute(feature_flags=flags)
        assert len(contract.feature_flags) == 1
        assert contract.feature_flags[0].name == "pattern_enforcement"
        assert (
            contract.feature_flags[0].category == EnumFeatureFlagCategory.INTELLIGENCE
        )

    @pytest.mark.unit
    def test_multiple_flags(self) -> None:
        """Multiple flags can be declared."""
        flags = [
            ModelContractFeatureFlag(name="flag_a", default_value=True),
            ModelContractFeatureFlag(name="flag_b", default_value=False),
        ]
        contract = _create_minimal_compute(feature_flags=flags)
        assert len(contract.feature_flags) == 2
        assert contract.feature_flags[0].name == "flag_a"
        assert contract.feature_flags[1].name == "flag_b"

    @pytest.mark.unit
    def test_feature_flags_from_dict(self) -> None:
        """Feature flags parse from dict representation (simulates YAML loading)."""
        contract = _create_minimal_compute(
            feature_flags=[
                {
                    "name": "real_time_events",
                    "default_value": False,
                    "env_var": "ENABLE_REAL_TIME_EVENTS",
                    "category": "dashboard",
                },
            ],
        )
        assert len(contract.feature_flags) == 1
        flag = contract.feature_flags[0]
        assert flag.name == "real_time_events"
        assert flag.default_value is False
        assert flag.env_var == "ENABLE_REAL_TIME_EVENTS"
        assert flag.category == EnumFeatureFlagCategory.DASHBOARD
