# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for NodeCompute high-complexity branches.

Targets CCN hotspots in node_compute.py:
- register_computation: duplicate type and non-callable guards
- execute_compute: contract validation branches (missing input_state, missing algorithm)
- process: pure mode, unknown computation type, parallel fallback
- get_computation_metrics: pure mode vs full mode
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_algorithm_config import ModelAlgorithmConfig
from omnibase_core.models.contracts.model_algorithm_factor_config import (
    ModelAlgorithmFactorConfig,
)
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_performance_requirements import (
    ModelPerformanceRequirements,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.nodes.node_compute import NodeCompute

pytestmark = pytest.mark.unit


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer(enable_service_registry=False)


@pytest.fixture
def pure_node(container: ModelONEXContainer) -> NodeCompute[Any, Any]:
    node = NodeCompute(container)
    node._cache = None
    node._timing_service = None
    node._parallel_executor = None
    return node


@pytest.fixture
def algorithm_config() -> ModelAlgorithmConfig:
    return ModelAlgorithmConfig(
        algorithm_type="default",
        factors={
            "main": ModelAlgorithmFactorConfig(weight=1.0, calculation_method="direct")
        },
    )


@pytest.fixture
def perf_requirements() -> ModelPerformanceRequirements:
    return ModelPerformanceRequirements(
        single_operation_max_ms=1000.0,
        max_memory_mb=512.0,
    )


def _make_contract(
    algorithm: ModelAlgorithmConfig | None,
    perf: ModelPerformanceRequirements,
    input_state: dict[str, ModelSchemaValue] | None = None,
) -> ModelContractCompute:
    return ModelContractCompute(
        name="TestContract",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        description="test",
        node_type=EnumNodeType.COMPUTE_GENERIC,
        input_model="omnibase_core.models.ModelTestInput",
        output_model="omnibase_core.models.ModelTestOutput",
        algorithm=algorithm,
        performance=perf,
        input_state=input_state,
    )


class TestRegisterComputation:
    def test_duplicate_registration_raises(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        with pytest.raises(ModelOnexError) as exc_info:
            pure_node.register_computation("default", lambda x: x)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "already registered" in exc_info.value.message

    def test_non_callable_raises(self, pure_node: NodeCompute[Any, Any]) -> None:
        with pytest.raises(ModelOnexError) as exc_info:
            pure_node.register_computation("my_type", "not_a_function")  # type: ignore[arg-type]
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "callable" in exc_info.value.message

    def test_valid_registration_succeeds(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        pure_node.register_computation("square", lambda x: x * x)
        assert "square" in pure_node.computation_registry

    def test_builtin_computations_registered(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        assert "default" in pure_node.computation_registry
        assert "string_uppercase" in pure_node.computation_registry
        assert "sum_numbers" in pure_node.computation_registry


class TestExecuteCompute:
    @pytest.mark.asyncio
    async def test_invalid_contract_type_raises(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        with pytest.raises(ModelOnexError) as exc_info:
            await pure_node.execute_compute("not_a_contract")  # type: ignore[arg-type]
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "ModelContractCompute" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_missing_input_state_raises(
        self,
        pure_node: NodeCompute[Any, Any],
        algorithm_config: ModelAlgorithmConfig,
        perf_requirements: ModelPerformanceRequirements,
    ) -> None:
        contract = _make_contract(algorithm_config, perf_requirements, input_state=None)
        with pytest.raises(ModelOnexError) as exc_info:
            await pure_node.execute_compute(contract)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "input_state" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_missing_algorithm_raises(
        self,
        pure_node: NodeCompute[Any, Any],
        perf_requirements: ModelPerformanceRequirements,
    ) -> None:
        contract = _make_contract(
            None,
            perf_requirements,
            input_state={
                "key": ModelSchemaValue(string_value="test", value_type="string")
            },
        )
        with pytest.raises(ModelOnexError) as exc_info:
            await pure_node.execute_compute(contract)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "algorithm" in exc_info.value.message


class TestProcessPureMode:
    @pytest.mark.asyncio
    async def test_default_computation_identity(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        data = {"key": "value"}
        input_data = ModelComputeInput(
            data=data,
            computation_type="default",
            operation_id=uuid4(),
        )
        output = await pure_node.process(input_data)
        assert output.result == data

    @pytest.mark.asyncio
    async def test_string_uppercase_computation(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        input_data = ModelComputeInput(
            data="hello world",
            computation_type="string_uppercase",
            operation_id=uuid4(),
        )
        output = await pure_node.process(input_data)
        assert output.result == "HELLO WORLD"

    @pytest.mark.asyncio
    async def test_sum_numbers_computation(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        input_data = ModelComputeInput(
            data=[1.0, 2.0, 3.0],
            computation_type="sum_numbers",
            operation_id=uuid4(),
        )
        output = await pure_node.process(input_data)
        assert output.result == 6.0

    @pytest.mark.asyncio
    async def test_unknown_computation_type_raises(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        input_data = ModelComputeInput(
            data="anything",
            computation_type="nonexistent_type",
            operation_id=uuid4(),
        )
        with pytest.raises(ModelOnexError) as exc_info:
            await pure_node.process(input_data)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "nonexistent_type" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_pure_mode_reports_no_cache_hit(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        input_data = ModelComputeInput(
            data="test",
            computation_type="string_uppercase",
            cache_enabled=True,
            operation_id=uuid4(),
        )
        output = await pure_node.process(input_data)
        assert output.cache_hit is False

    @pytest.mark.asyncio
    async def test_pure_mode_processing_time_zero(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        input_data = ModelComputeInput(
            data="test",
            computation_type="default",
            operation_id=uuid4(),
        )
        output = await pure_node.process(input_data)
        assert output.processing_time_ms == 0.0

    @pytest.mark.asyncio
    async def test_parallel_disabled_when_no_executor(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        input_data = ModelComputeInput(
            data=[1, 2, 3],
            computation_type="sum_numbers",
            parallel_enabled=True,
            operation_id=uuid4(),
        )
        output = await pure_node.process(input_data)
        assert output.parallel_execution_used is False

    @pytest.mark.asyncio
    async def test_string_uppercase_wrong_type_raises(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        input_data = ModelComputeInput(
            data=123,
            computation_type="string_uppercase",
            operation_id=uuid4(),
        )
        with pytest.raises(ModelOnexError) as exc_info:
            await pure_node.process(input_data)
        # ModelOnexError from computation func re-raises as-is (VALIDATION_ERROR)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


class TestGetComputationMetrics:
    @pytest.mark.asyncio
    async def test_pure_mode_metrics_has_execution_mode(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        metrics = await pure_node.get_computation_metrics()
        assert "execution_mode" in metrics
        assert metrics["execution_mode"]["pure_mode"] == 1.0
        assert metrics["execution_mode"]["cache_enabled"] == 0.0
        assert metrics["execution_mode"]["parallel_enabled"] == 0.0

    @pytest.mark.asyncio
    async def test_pure_mode_no_cache_performance_section(
        self, pure_node: NodeCompute[Any, Any]
    ) -> None:
        metrics = await pure_node.get_computation_metrics()
        assert "cache_performance" not in metrics
