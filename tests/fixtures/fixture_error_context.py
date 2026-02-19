# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test fixtures for ModelErrorContext using Pydantic bypass pattern.

⚠️ WARNING: Uses model_construct() for test performance.
NEVER use these patterns in production code (src/).
"""

from omnibase_core.models.common.model_error_context import ModelErrorContext
from tests.fixtures.fixture_base import TestFixtureBase


class ErrorContextFixtures(TestFixtureBase):
    """Fast test fixtures for ModelErrorContext.

    Performance Benefits:
        - Standard construction: ~100-200μs per model (due to schema validation)
        - Bypass construction: ~2-10μs per model
        - ~20-50x speedup for error handling tests

    Example Usage:
        def test_error_handling():
            # Fast error context creation
            error_ctx = ErrorContextFixtures.simple()
            assert error_ctx.file_path is None

            # With file location
            error_ctx = ErrorContextFixtures.with_location(
                file_path="test.py",
                line_number=42
            )
    """

    @staticmethod
    def simple(**overrides) -> ModelErrorContext:
        """Create a simple error context with no details.

        Args:
            **overrides: Override default field values

        Returns:
            ModelErrorContext with minimal data
        """
        return TestFixtureBase.construct(
            ModelErrorContext,
            file_path=None,
            line_number=None,
            column_number=None,
            function_name=None,
            module_name=None,
            stack_trace=None,
            additional_context={},
            **overrides,
        )

    @staticmethod
    def with_location(
        file_path: str = "test_file.py", line_number: int = 42, **overrides
    ) -> ModelErrorContext:
        """Create error context with file location.

        Args:
            file_path: Path to the file
            line_number: Line number in the file
            **overrides: Override default field values

        Returns:
            ModelErrorContext with file location
        """
        return TestFixtureBase.construct(
            ModelErrorContext,
            file_path=file_path,
            line_number=line_number,
            column_number=None,
            function_name=None,
            module_name=None,
            stack_trace=None,
            additional_context={},
            **overrides,
        )

    @staticmethod
    def with_stack_trace(
        stack_trace: str = "Traceback (most recent call last):\n  ...", **overrides
    ) -> ModelErrorContext:
        """Create error context with stack trace.

        Args:
            stack_trace: Stack trace string
            **overrides: Override default field values

        Returns:
            ModelErrorContext with stack trace
        """
        return TestFixtureBase.construct(
            ModelErrorContext,
            file_path="test_file.py",
            line_number=42,
            column_number=10,
            function_name="test_function",
            module_name="test_module",
            stack_trace=stack_trace,
            additional_context={},
            **overrides,
        )

    @staticmethod
    def many(count: int, **base_fields) -> list[ModelErrorContext]:
        """Create many error context instances efficiently.

        Args:
            count: Number of instances to create
            **base_fields: Base field values for all instances

        Returns:
            List of ModelErrorContext instances
        """
        defaults = {
            "file_path": None,
            "line_number": None,
            "column_number": None,
            "function_name": None,
            "module_name": None,
            "stack_trace": None,
            "additional_context": {},
        }
        defaults.update(base_fields)
        return TestFixtureBase.construct_many(
            ModelErrorContext, count=count, **defaults
        )
