"""Base class for test fixtures using Pydantic bypass patterns.

⚠️ WARNING: This module uses Pydantic validation bypass for test performance.
NEVER import or use these patterns in production code (src/).

The pre-commit hook 'no-pydantic-bypass-in-prod' enforces this restriction.
"""

from copy import deepcopy
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class TestFixtureBase:
    """Base class for test fixtures with safe Pydantic bypass patterns.

    Why Bypass Validation in Tests:
        - Validation is expensive (10-100x slower than direct construction)
        - Tests create thousands of model instances
        - Test data is known-valid by construction
        - Production code always validates at boundaries

    Safety Guarantees:
        - Only used in tests/ directory (enforced by pre-commit hook)
        - Models are still type-checked by mypy
        - Integration tests validate real data flows
        - Pre-commit hook blocks bypass patterns in src/

    Usage:
        class MyFixture(TestFixtureBase):
            @staticmethod
            def create_effect_input(**overrides):
                return TestFixtureBase.construct(
                    ModelEffectInput,
                    operation="test_op",
                    parameters={},
                    **overrides
                )

    Performance Impact:
        - Standard construction: ~100-1000μs per model (with validation)
        - Bypass construction: ~1-10μs per model (no validation)
        - Speedup: 10-100x faster for large test suites

    Thread Safety:
        - Construction methods are thread-safe (no shared state)
        - Constructed models follow Pydantic's thread-safety guarantees
    """

    @staticmethod
    def construct(model_class: type[T], **field_values) -> T:
        """Construct model bypassing Pydantic validation.

        ⚠️ ONLY USE IN TESTS - NEVER IN PRODUCTION CODE (src/)

        This method uses model_construct() to bypass all Pydantic validation,
        type coercion, and default value computation. This is ONLY safe in tests
        where you know the data is valid by construction.

        Args:
            model_class: The Pydantic model class to construct
            **field_values: Field values to set (no validation applied)

        Returns:
            Model instance with validation bypassed

        Example:
            # Fast test fixture creation (no validation overhead)
            input_data = TestFixtureBase.construct(
                ModelEffectInput,
                operation="test",
                parameters={"key": "value"}
            )

        Performance:
            - ~1-10μs per model (vs ~100-1000μs with validation)
            - Useful when creating many test fixtures

        Enforcement:
            - Pre-commit hook prevents use in src/ directory
            - Validation script: scripts/validation/validate_no_pydantic_bypass.py
        """
        return model_class.model_construct(**field_values)

    @staticmethod
    def construct_many(model_class: type[T], count: int, **base_fields) -> list[T]:
        """Construct many model instances efficiently.

        Creates multiple instances with incremental IDs for list-based tests.
        Each instance gets a deep copy of base_fields to avoid shared state.

        Args:
            model_class: The Pydantic model class
            count: Number of instances to create
            **base_fields: Base field values for all instances

        Returns:
            List of model instances

        Example:
            # Create 100 test inputs with unique IDs
            inputs = TestFixtureBase.construct_many(
                ModelEffectInput,
                count=100,
                operation="test",
                parameters={}
            )

        Performance:
            - Useful for batch processing tests
            - ~10-1000μs for 100 models (vs ~10-100ms with validation)
        """
        items: list[T] = []
        model_fields = getattr(model_class, "model_fields", {}) or {}
        has_id_field = "id" in model_fields
        for i in range(count):
            fields = deepcopy(base_fields)
            if has_id_field:
                fields["id"] = i
            items.append(model_class.model_construct(**fields))
        return items
