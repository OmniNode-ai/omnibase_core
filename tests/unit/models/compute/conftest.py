"""Shared fixtures for compute-related tests.

Provides reusable fixtures for:
- ModelComputeSubcontract creation
- ModelComputeExecutionContext creation
- ModelComputePipelineStep creation
- Common transformation configs

These fixtures reduce test boilerplate and ensure consistent test data.
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_case_mode import EnumCaseMode
from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.enums.enum_trim_mode import EnumTrimMode
from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)
from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import (
    ModelComputeSubcontract,
)
from omnibase_core.models.transformations.model_transform_case_config import (
    ModelTransformCaseConfig,
)
from omnibase_core.models.transformations.model_transform_trim_config import (
    ModelTransformTrimConfig,
)


@pytest.fixture
def sample_operation_id():
    """Generate a sample operation ID for tests."""
    return uuid4()


@pytest.fixture
def sample_correlation_id():
    """Generate a sample correlation ID for tests."""
    return uuid4()


@pytest.fixture
def sample_execution_context(sample_operation_id):
    """Create a sample ModelComputeExecutionContext for tests.

    Returns:
        ModelComputeExecutionContext with operation_id set
    """
    return ModelComputeExecutionContext(operation_id=sample_operation_id)


@pytest.fixture
def sample_execution_context_full(sample_operation_id, sample_correlation_id):
    """Create a ModelComputeExecutionContext with all fields populated.

    Returns:
        ModelComputeExecutionContext with operation_id, correlation_id, and node_id
    """
    return ModelComputeExecutionContext(
        operation_id=sample_operation_id,
        correlation_id=sample_correlation_id,
        node_id="test-node-123",
    )


@pytest.fixture
def uppercase_transform_config():
    """Create uppercase transformation config."""
    return ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)


@pytest.fixture
def lowercase_transform_config():
    """Create lowercase transformation config."""
    return ModelTransformCaseConfig(mode=EnumCaseMode.LOWER)


@pytest.fixture
def trim_both_config():
    """Create trim both sides config."""
    return ModelTransformTrimConfig(mode=EnumTrimMode.BOTH)


@pytest.fixture
def identity_pipeline_step():
    """Create an identity transformation pipeline step.

    Returns:
        ModelComputePipelineStep configured for identity transformation
    """
    return ModelComputePipelineStep(
        step_name="identity",
        step_type=EnumComputeStepType.TRANSFORMATION,
        transformation_type=EnumTransformationType.IDENTITY,
    )


@pytest.fixture
def uppercase_pipeline_step(uppercase_transform_config):
    """Create an uppercase transformation pipeline step.

    Returns:
        ModelComputePipelineStep configured for uppercase case conversion
    """
    return ModelComputePipelineStep(
        step_name="to_upper",
        step_type=EnumComputeStepType.TRANSFORMATION,
        transformation_type=EnumTransformationType.CASE_CONVERSION,
        transformation_config=uppercase_transform_config,
    )


@pytest.fixture
def trim_pipeline_step(trim_both_config):
    """Create a trim transformation pipeline step.

    Returns:
        ModelComputePipelineStep configured for trimming whitespace
    """
    return ModelComputePipelineStep(
        step_name="trim",
        step_type=EnumComputeStepType.TRANSFORMATION,
        transformation_type=EnumTransformationType.TRIM,
        transformation_config=trim_both_config,
    )


@pytest.fixture
def empty_compute_subcontract():
    """Create a ModelComputeSubcontract with an empty pipeline.

    Returns:
        ModelComputeSubcontract with no pipeline steps
    """
    return ModelComputeSubcontract(
        operation_name="empty_op",
        operation_version="1.0.0",
        pipeline=[],
    )


@pytest.fixture
def simple_compute_subcontract(uppercase_pipeline_step):
    """Create a simple ModelComputeSubcontract with one pipeline step.

    Returns:
        ModelComputeSubcontract with single uppercase transformation
    """
    return ModelComputeSubcontract(
        operation_name="text_upper",
        operation_version="1.0.0",
        pipeline=[uppercase_pipeline_step],
    )


@pytest.fixture
def multi_step_compute_subcontract(trim_pipeline_step, uppercase_pipeline_step):
    """Create a ModelComputeSubcontract with multiple pipeline steps.

    Returns:
        ModelComputeSubcontract with trim then uppercase transformations
    """
    return ModelComputeSubcontract(
        operation_name="text_normalize",
        operation_version="1.0.0",
        pipeline=[trim_pipeline_step, uppercase_pipeline_step],
    )


@pytest.fixture
def compute_subcontract_with_timeout(uppercase_pipeline_step):
    """Create a ModelComputeSubcontract with pipeline timeout configured.

    Returns:
        ModelComputeSubcontract with 5 second timeout
    """
    return ModelComputeSubcontract(
        operation_name="timed_op",
        operation_version="1.0.0",
        pipeline=[uppercase_pipeline_step],
        pipeline_timeout_ms=5000,
    )
