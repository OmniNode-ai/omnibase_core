"""Shared fixtures for integration tests.

Provides reusable fixtures for:
- ModelComputeExecutionContext creation
- Common test utilities for pipeline integration tests

These fixtures reduce test boilerplate and ensure consistent test data.
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

    Useful when you need multiple distinct contexts in a single test.

    Returns:
        Callable that returns a new ModelComputeExecutionContext each time
    """
    def _create_context() -> ModelComputeExecutionContext:
        return ModelComputeExecutionContext(
            operation_id=uuid4(),
            correlation_id=uuid4(),
        )
    return _create_context
