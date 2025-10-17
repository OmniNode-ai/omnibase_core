"""Test fixtures for ModelContext using Pydantic bypass pattern.

⚠️ WARNING: Uses model_construct() for test performance.
NEVER use these patterns in production code (src/).
"""

from omnibase_core.models.core.model_context import ModelContext
from tests.fixtures.fixture_base import TestFixtureBase


class ContextFixtures(TestFixtureBase):
    """Fast test fixtures for ModelContext.

    Performance Benefits:
        - Standard construction: ~50-100μs per model
        - Bypass construction: ~1-5μs per model
        - ~20-100x speedup for large test suites

    Example Usage:
        def test_my_function():
            # Fast fixture creation
            context = ContextFixtures.simple()
            result = my_function(context)
            assert result.success
    """

    @staticmethod
    def simple(**overrides) -> ModelContext:
        """Create a simple context for basic tests.

        Args:
            **overrides: Override default field values

        Returns:
            ModelContext with minimal test data
        """
        return TestFixtureBase.construct(ModelContext, data={}, **overrides)

    @staticmethod
    def with_data(**overrides) -> ModelContext:
        """Create context with sample data.

        Args:
            **overrides: Override default field values

        Returns:
            ModelContext with test data
        """
        return TestFixtureBase.construct(
            ModelContext,
            data={
                "user_id": "test-user-123",
                "request_id": "req-456",
                "environment": "test",
            },
            **overrides,
        )

    @staticmethod
    def many(count: int, **base_fields) -> list[ModelContext]:
        """Create many context instances efficiently.

        Args:
            count: Number of instances to create
            **base_fields: Base field values for all instances

        Returns:
            List of ModelContext instances
        """
        defaults = {"data": {}}
        defaults.update(base_fields)
        return TestFixtureBase.construct_many(ModelContext, count=count, **defaults)
