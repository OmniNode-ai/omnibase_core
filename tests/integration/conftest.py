"""Shared fixtures for integration tests.

Provides reusable fixtures for:
- ModelComputeExecutionContext creation
- Common test utilities for pipeline integration tests

These fixtures reduce test boilerplate and ensure consistent test data.

Note:
    Integration tests using these fixtures should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

from collections.abc import Callable
from uuid import uuid4

import pytest

from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)

# Type alias for the context factory callable
ComputeContextFactory = Callable[[], ModelComputeExecutionContext]


@pytest.fixture
def compute_execution_context_factory() -> ComputeContextFactory:
    """Factory fixture that creates a new execution context each time called.

    This fixture is used by TestComputePipelineIntegration to create unique
    execution contexts for each pipeline invocation. It provides:
    - Unique operation_id for each context
    - Unique correlation_id for tracing
    - Fresh context without accumulated state

    Useful when you need multiple distinct contexts in a single test, such as
    verifying that pipeline executions are independent.

    Returns:
        ComputeContextFactory: A callable that returns a new
            ModelComputeExecutionContext with unique IDs each time it's called.

    Example:
        def test_pipeline(self, compute_execution_context_factory):
            context1 = compute_execution_context_factory()
            context2 = compute_execution_context_factory()
            assert context1.operation_id != context2.operation_id
    """

    def _create_context() -> ModelComputeExecutionContext:
        return ModelComputeExecutionContext(
            operation_id=uuid4(),
            correlation_id=uuid4(),
        )

    return _create_context
