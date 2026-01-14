"""Tests for effect_boundary decorator.

Part of OMN-1147: Effect Classification System test suite.
"""

import asyncio

import pytest

from omnibase_core.decorators.decorator_effect_boundary import (
    EFFECT_BOUNDARY_ATTR,
    effect_boundary,
    get_effect_boundary,
    has_effect_boundary,
)
from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel
from omnibase_core.models.effects.model_effect_boundary import ModelEffectBoundary


@pytest.mark.unit
class TestEffectBoundaryDecorator:
    """Test cases for the @effect_boundary decorator."""

    def test_decorator_preserves_function_signature(self) -> None:
        """Test that decorator preserves the original function signature."""

        @effect_boundary("test.boundary")
        def sample_func(arg1: str, arg2: int, kwarg1: str = "default") -> str:
            return f"{arg1}-{arg2}-{kwarg1}"

        # Check function can still be called correctly
        result = sample_func("hello", 42, kwarg1="custom")
        assert result == "hello-42-custom"

        # Check with defaults
        result2 = sample_func("test", 123)
        assert result2 == "test-123-default"

    def test_decorator_preserves_docstring(self) -> None:
        """Test that decorator preserves the original function docstring."""

        @effect_boundary("test.boundary")
        def documented_func() -> None:
            """This is the original docstring for the function."""

        assert (
            documented_func.__doc__
            == "This is the original docstring for the function."
        )

    def test_decorator_preserves_function_name(self) -> None:
        """Test that decorator preserves the original function name."""

        @effect_boundary("test.boundary")
        def named_function() -> None:
            pass

        assert named_function.__name__ == "named_function"

    def test_get_effect_boundary_retrieves_metadata(self) -> None:
        """Test get_effect_boundary() retrieves attached metadata."""

        @effect_boundary(
            "user_service.fetch",
            categories=[EnumEffectCategory.NETWORK],
            policy=EnumEffectPolicyLevel.STRICT,
        )
        def fetch_user(user_id: str) -> dict:
            return {"id": user_id}

        boundary = get_effect_boundary(fetch_user)

        assert boundary is not None
        assert isinstance(boundary, ModelEffectBoundary)
        assert boundary.boundary_id == "user_service.fetch"
        assert boundary.default_policy == EnumEffectPolicyLevel.STRICT

    def test_has_effect_boundary_returns_true_for_decorated(self) -> None:
        """Test has_effect_boundary() returns True for decorated functions."""

        @effect_boundary("test.boundary")
        def decorated_func() -> None:
            pass

        assert has_effect_boundary(decorated_func) is True

    def test_has_effect_boundary_returns_false_for_undecorated(self) -> None:
        """Test has_effect_boundary() returns False for undecorated functions."""

        def undecorated_func() -> None:
            pass

        assert has_effect_boundary(undecorated_func) is False

    def test_decorated_function_executes_correctly(self) -> None:
        """Test that decorated function still executes its original logic."""

        @effect_boundary("test.compute")
        def compute(x: int, y: int) -> int:
            return x * y + 10

        assert compute(3, 4) == 22
        assert compute(0, 100) == 10
        assert compute(-5, 2) == 0

    def test_multiple_categories_in_decorator(self) -> None:
        """Test decorator with multiple effect categories."""

        @effect_boundary(
            "data_service.sync",
            categories=[
                EnumEffectCategory.NETWORK,
                EnumEffectCategory.DATABASE,
                EnumEffectCategory.FILESYSTEM,
            ],
        )
        def sync_data() -> None:
            pass

        boundary = get_effect_boundary(sync_data)
        assert boundary is not None
        assert len(boundary.classifications) == 3

        categories = {c.category for c in boundary.classifications}
        assert EnumEffectCategory.NETWORK in categories
        assert EnumEffectCategory.DATABASE in categories
        assert EnumEffectCategory.FILESYSTEM in categories

    def test_default_policy_value(self) -> None:
        """Test that default policy is WARN when not specified."""

        @effect_boundary("test.boundary")
        def func_with_defaults() -> None:
            pass

        boundary = get_effect_boundary(func_with_defaults)
        assert boundary is not None
        assert boundary.default_policy == EnumEffectPolicyLevel.WARN

    def test_async_function_decoration(self) -> None:
        """Test that async functions can be decorated."""

        @effect_boundary(
            "async_service.fetch",
            categories=[EnumEffectCategory.NETWORK],
            policy=EnumEffectPolicyLevel.MOCKED,
        )
        async def async_fetch(url: str) -> dict:
            return {"url": url, "data": "response"}

        # Verify metadata is attached
        boundary = get_effect_boundary(async_fetch)
        assert boundary is not None
        assert boundary.boundary_id == "async_service.fetch"
        assert boundary.default_policy == EnumEffectPolicyLevel.MOCKED

        # Verify async function still works
        result = asyncio.run(async_fetch("https://api.example.com"))
        assert result["url"] == "https://api.example.com"

    def test_determinism_marker_default_true(self) -> None:
        """Test that determinism_marker defaults to True."""

        @effect_boundary("test.boundary")
        def func() -> None:
            pass

        boundary = get_effect_boundary(func)
        assert boundary is not None
        assert boundary.determinism_marker is True

    def test_determinism_marker_can_be_false(self) -> None:
        """Test that determinism_marker can be set to False."""

        @effect_boundary("test.boundary", determinism_marker=False)
        def func() -> None:
            pass

        boundary = get_effect_boundary(func)
        assert boundary is not None
        assert boundary.determinism_marker is False

    def test_isolation_mechanisms_parameter(self) -> None:
        """Test isolation_mechanisms parameter is passed through."""

        @effect_boundary(
            "db_service.query",
            isolation_mechanisms=["DATABASE_READONLY_SNAPSHOT", "MOCK_TIME"],
        )
        def query_db() -> None:
            pass

        boundary = get_effect_boundary(query_db)
        assert boundary is not None
        assert boundary.has_isolation_mechanism("DATABASE_READONLY_SNAPSHOT") is True
        assert boundary.has_isolation_mechanism("MOCK_TIME") is True

    def test_description_parameter(self) -> None:
        """Test description parameter is used in classifications."""

        @effect_boundary(
            "api.call",
            categories=[EnumEffectCategory.NETWORK],
            description="External API call to third-party service",
        )
        def call_api() -> None:
            pass

        boundary = get_effect_boundary(call_api)
        assert boundary is not None
        assert len(boundary.classifications) == 1
        assert (
            boundary.classifications[0].description
            == "External API call to third-party service"
        )

    def test_description_fallback_to_boundary_id(self) -> None:
        """Test description falls back to boundary_id when not provided."""

        @effect_boundary(
            "my.boundary.id",
            categories=[EnumEffectCategory.TIME],
        )
        def func() -> None:
            pass

        boundary = get_effect_boundary(func)
        assert boundary is not None
        assert len(boundary.classifications) == 1
        assert "my.boundary.id" in boundary.classifications[0].description

    def test_effect_boundary_attribute_name(self) -> None:
        """Test that EFFECT_BOUNDARY_ATTR constant is correct."""
        assert EFFECT_BOUNDARY_ATTR == "_effect_boundary"

        @effect_boundary("test.boundary")
        def func() -> None:
            pass

        assert hasattr(func, EFFECT_BOUNDARY_ATTR)
        assert getattr(func, EFFECT_BOUNDARY_ATTR) is not None

    def test_get_effect_boundary_returns_none_for_undecorated(self) -> None:
        """Test get_effect_boundary() returns None for undecorated functions."""

        def plain_func() -> None:
            pass

        assert get_effect_boundary(plain_func) is None

    def test_all_policy_levels_work(self) -> None:
        """Test decorator works with all policy levels."""
        for policy_level in EnumEffectPolicyLevel:

            @effect_boundary(f"test.{policy_level}", policy=policy_level)
            def func() -> None:
                pass

            boundary = get_effect_boundary(func)
            assert boundary is not None
            assert boundary.default_policy == policy_level

    def test_all_categories_work(self) -> None:
        """Test decorator works with all effect categories."""
        all_categories = list(EnumEffectCategory)

        @effect_boundary("test.all_categories", categories=all_categories)
        def func() -> None:
            pass

        boundary = get_effect_boundary(func)
        assert boundary is not None
        assert len(boundary.classifications) == len(EnumEffectCategory)

    def test_empty_categories_list(self) -> None:
        """Test decorator with empty categories list."""

        @effect_boundary("test.no_categories", categories=[])
        def func() -> None:
            pass

        boundary = get_effect_boundary(func)
        assert boundary is not None
        assert len(boundary.classifications) == 0

    def test_none_categories(self) -> None:
        """Test decorator with categories=None (default)."""

        @effect_boundary("test.default_categories")
        def func() -> None:
            pass

        boundary = get_effect_boundary(func)
        assert boundary is not None
        assert len(boundary.classifications) == 0

    def test_classifications_have_nondeterministic_true(self) -> None:
        """Test that created classifications have nondeterministic=True."""

        @effect_boundary(
            "test.nondeterministic",
            categories=[EnumEffectCategory.RANDOM],
        )
        def func() -> None:
            pass

        boundary = get_effect_boundary(func)
        assert boundary is not None
        assert len(boundary.classifications) == 1
        assert boundary.classifications[0].nondeterministic is True

    def test_boundary_model_is_frozen(self) -> None:
        """Test that the attached boundary model is immutable."""

        @effect_boundary("test.frozen")
        def func() -> None:
            pass

        boundary = get_effect_boundary(func)
        assert boundary is not None

        # ModelEffectBoundary is frozen - this should raise
        with pytest.raises(Exception):  # ValidationError for Pydantic
            boundary.boundary_id = "modified"  # type: ignore[misc]

    def test_function_with_type_hints(self) -> None:
        """Test decorator works with fully type-hinted functions."""

        @effect_boundary(
            "typed.function",
            categories=[EnumEffectCategory.DATABASE],
        )
        def typed_func(
            required_arg: str,
            optional_arg: int | None = None,
            *args: str,
            **kwargs: int,
        ) -> dict[str, object]:
            return {
                "required": required_arg,
                "optional": optional_arg,
                "args": args,
                "kwargs": kwargs,
            }

        # Function still works
        result = typed_func("test", 42, "extra", key=100)
        assert result["required"] == "test"
        assert result["optional"] == 42

        # Metadata attached
        assert has_effect_boundary(typed_func) is True

    def test_method_decoration(self) -> None:
        """Test decorator can be applied to class methods."""

        class Service:
            @effect_boundary(
                "service.method",
                categories=[EnumEffectCategory.NETWORK],
            )
            def fetch_data(self, item_id: str) -> dict:
                return {"id": item_id}

        service = Service()
        result = service.fetch_data("123")
        assert result["id"] == "123"

        # Check metadata on unbound method
        boundary = get_effect_boundary(Service.fetch_data)
        assert boundary is not None
        assert boundary.boundary_id == "service.method"

    def test_staticmethod_decoration(self) -> None:
        """Test decorator can be applied to static methods."""

        class Utility:
            @staticmethod
            @effect_boundary("utility.static", categories=[EnumEffectCategory.TIME])
            def get_timestamp() -> str:
                return "2025-01-01"

        result = Utility.get_timestamp()
        assert result == "2025-01-01"

        # Static methods work differently - check if boundary is accessible
        boundary = get_effect_boundary(Utility.get_timestamp)
        assert boundary is not None

    def test_multiple_decorators_on_same_function(self) -> None:
        """Test that effect_boundary can coexist with other decorators."""

        def logging_decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        @logging_decorator
        @effect_boundary("test.multi_decorated")
        def multi_decorated() -> str:
            return "result"

        # Function works
        assert multi_decorated() == "result"

        # The order matters - effect_boundary metadata is on the inner wrapper,
        # but logging_decorator wraps it without preserving the attribute.
        # get_effect_boundary cannot find the metadata through the outer wrapper.
        boundary = get_effect_boundary(multi_decorated)
        assert boundary is None, (
            "Outer decorator does not preserve effect boundary attribute, "
            "so get_effect_boundary should return None"
        )
