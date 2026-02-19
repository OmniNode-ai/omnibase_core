# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for NodeCompute contract-to-input conversion.

Tests error handling in NodeCompute._contract_to_input() when input_state is missing.
"""

from typing import Any

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
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


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create test container."""
    return ModelONEXContainer(enable_service_registry=False)


@pytest.fixture
def compute_node(test_container: ModelONEXContainer) -> NodeCompute[Any, Any]:
    """Create NodeCompute instance for testing."""
    return NodeCompute(test_container)


@pytest.fixture
def valid_algorithm_config() -> ModelAlgorithmConfig:
    """Create a valid algorithm configuration for testing."""
    return ModelAlgorithmConfig(
        algorithm_type="default",
        factors={
            "main_factor": ModelAlgorithmFactorConfig(
                weight=1.0,
                calculation_method="direct",
            )
        },
    )


@pytest.fixture
def valid_performance_requirements() -> ModelPerformanceRequirements:
    """Create performance requirements with single_operation_max_ms set."""
    return ModelPerformanceRequirements(
        single_operation_max_ms=1000.0,
        max_memory_mb=512.0,
    )


def create_valid_contract(
    algorithm_config: ModelAlgorithmConfig,
    performance_requirements: ModelPerformanceRequirements,
    input_state: dict[str, ModelSchemaValue] | None = None,
) -> ModelContractCompute:
    """Create a valid ModelContractCompute with specified input_state."""
    return ModelContractCompute(
        name="TestComputeContract",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test compute contract for unit testing",
        node_type=EnumNodeType.COMPUTE_GENERIC,
        input_model="omnibase_core.models.ModelTestInput",
        output_model="omnibase_core.models.ModelTestOutput",
        algorithm=algorithm_config,
        performance=performance_requirements,
        input_state=input_state,
    )


def get_nested_context(error: ModelOnexError) -> dict[str, Any]:
    """Extract the actual context dict from nested error structure.

    ModelOnexError stores context in a nested structure:
    {'additional_context': {'context': {actual context}}}
    """
    context = error.context or {}
    if "additional_context" in context:
        additional = context.get("additional_context", {})
        if isinstance(additional, dict) and "context" in additional:
            return additional.get("context", {})
    return context


@pytest.mark.unit
class TestContractToInputMissingInputState:
    """Test _contract_to_input error handling when input_state is missing."""

    def test_contract_to_input_raises_error_when_input_state_is_none(
        self,
        compute_node: NodeCompute[Any, Any],
        valid_algorithm_config: ModelAlgorithmConfig,
        valid_performance_requirements: ModelPerformanceRequirements,
    ) -> None:
        """Test that _contract_to_input raises ModelOnexError when input_state is None.

        The contract must have a valid input_state field. If input_state is None,
        a VALIDATION_ERROR should be raised with helpful context.
        """
        # Create contract with input_state=None (explicitly None)
        contract = create_valid_contract(
            algorithm_config=valid_algorithm_config,
            performance_requirements=valid_performance_requirements,
            input_state=None,  # Missing input_state
        )

        with pytest.raises(ModelOnexError) as exc_info:
            compute_node._contract_to_input(contract)

        # Verify error details
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "input_state" in error.message.lower()
        assert "valid data" in error.message.lower()

        # Verify context contains helpful information (extract from nested structure)
        nested_context = get_nested_context(error)
        assert "node_id" in nested_context
        assert "hint" in nested_context

    @pytest.mark.asyncio
    async def test_execute_compute_raises_error_when_input_state_missing(
        self,
        compute_node: NodeCompute[Any, Any],
        valid_algorithm_config: ModelAlgorithmConfig,
        valid_performance_requirements: ModelPerformanceRequirements,
    ) -> None:
        """Test that execute_compute raises error when contract has no input_state.

        This tests the public API entry point that calls _contract_to_input.
        """
        contract = create_valid_contract(
            algorithm_config=valid_algorithm_config,
            performance_requirements=valid_performance_requirements,
            input_state=None,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await compute_node.execute_compute(contract)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "input_state" in error.message.lower()

    def test_contract_to_input_succeeds_with_valid_input_state(
        self,
        compute_node: NodeCompute[Any, Any],
        valid_algorithm_config: ModelAlgorithmConfig,
        valid_performance_requirements: ModelPerformanceRequirements,
    ) -> None:
        """Test that _contract_to_input succeeds when input_state is provided.

        This is a positive test to ensure the happy path works correctly.
        """
        # Create contract with valid input_state
        contract = create_valid_contract(
            algorithm_config=valid_algorithm_config,
            performance_requirements=valid_performance_requirements,
            input_state={
                "key": ModelSchemaValue.from_value("value"),
                "data": ModelSchemaValue.from_value([1, 2, 3]),
            },
        )

        # Should not raise - convert successfully
        result = compute_node._contract_to_input(contract)

        assert result is not None
        assert result.data is not None

    def test_contract_to_input_with_empty_dict_input_state(
        self,
        compute_node: NodeCompute[Any, Any],
        valid_algorithm_config: ModelAlgorithmConfig,
        valid_performance_requirements: ModelPerformanceRequirements,
    ) -> None:
        """Test that empty dict input_state is accepted (not None).

        An empty dict {} is valid - only None should fail.
        """
        contract = create_valid_contract(
            algorithm_config=valid_algorithm_config,
            performance_requirements=valid_performance_requirements,
            input_state={},
        )

        # Empty dict is valid input_state - should not raise
        result = compute_node._contract_to_input(contract)

        assert result is not None
        assert result.data == {}

    def test_error_hint_mentions_input_data_deprecation(
        self,
        compute_node: NodeCompute[Any, Any],
        valid_algorithm_config: ModelAlgorithmConfig,
        valid_performance_requirements: ModelPerformanceRequirements,
    ) -> None:
        """Test that error hint mentions input_data is no longer supported.

        The hint should guide users to use input_state instead of the deprecated
        input_data field.
        """
        contract = create_valid_contract(
            algorithm_config=valid_algorithm_config,
            performance_requirements=valid_performance_requirements,
            input_state=None,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            compute_node._contract_to_input(contract)

        error = exc_info.value
        nested_context = get_nested_context(error)
        hint = nested_context.get("hint", "")
        assert "input_data" in hint.lower() or "input_state" in hint.lower()
