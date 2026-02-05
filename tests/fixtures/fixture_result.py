"""Test fixtures for ModelBaseResult using Pydantic bypass pattern.

⚠️ WARNING: Uses model_construct() for test performance.
NEVER use these patterns in production code (src/).
"""

from omnibase_core.models.core.model_base_result import ModelBaseResult
from tests.fixtures.fixture_base import TestFixtureBase


class ResultFixtures(TestFixtureBase):
    """Fast test fixtures for ModelBaseResult.

    Performance Benefits:
        - Standard construction: ~100-300μs per model (due to nested models)
        - Bypass construction: ~5-15μs per model
        - ~20-60x speedup for result validation tests

    Example Usage:
        def test_success_case():
            # Fast success result creation
            result = ResultFixtures.success()
            assert result.success is True
            assert result.exit_code == 0

        def test_failure_case():
            # Fast failure result creation
            result = ResultFixtures.failure(exit_code=1)
            assert result.success is False
    """

    @staticmethod
    def success(**overrides) -> ModelBaseResult:
        """Create a successful result.

        Args:
            **overrides: Override default field values

        Returns:
            ModelBaseResult indicating success
        """
        return TestFixtureBase.construct(
            ModelBaseResult,
            exit_code=0,
            success=True,
            errors=[],
            metadata=None,
            **overrides,
        )

    @staticmethod
    def failure(exit_code: int = 1, **overrides) -> ModelBaseResult:
        """Create a failure result.

        Args:
            exit_code: Exit code (default 1)
            **overrides: Override default field values

        Returns:
            ModelBaseResult indicating failure
        """
        return TestFixtureBase.construct(
            ModelBaseResult,
            exit_code=exit_code,
            success=False,
            errors=[],
            metadata=None,
            **overrides,
        )

    @staticmethod
    def with_errors(_error_count: int = 1, **overrides) -> ModelBaseResult:
        """Create a failure result with errors.

        Note: This creates empty error list - use with errors override
        to provide actual ModelErrorDetails instances if needed.

        Args:
            _error_count: Number of placeholder errors (not populated)
            **overrides: Override default field values

        Returns:
            ModelBaseResult with error list
        """
        return TestFixtureBase.construct(
            ModelBaseResult,
            exit_code=1,
            success=False,
            errors=[],  # Override with actual errors if needed
            metadata=None,
            **overrides,
        )

    @staticmethod
    def many_success(count: int, **base_fields) -> list[ModelBaseResult]:
        """Create many successful result instances efficiently.

        Args:
            count: Number of instances to create
            **base_fields: Base field values for all instances

        Returns:
            List of successful ModelBaseResult instances
        """
        defaults = {
            "exit_code": 0,
            "success": True,
            "metadata": None,
        }
        defaults.update(base_fields)
        return [
            TestFixtureBase.construct(
                ModelBaseResult,
                **{**defaults, "errors": []},
            )
            for _ in range(count)
        ]
