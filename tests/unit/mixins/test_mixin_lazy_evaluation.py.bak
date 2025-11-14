"""
Comprehensive unit tests for MixinLazyEvaluation.

Tests cover:
- Lazy property creation and caching
- Lazy model dump functionality
- Lazy serialization of nested objects
- Lazy string conversion
- Cache invalidation
- Cache statistics
- Lazy cached decorator
- Memory efficiency
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.mixins.mixin_lazy_evaluation import MixinLazyEvaluation, lazy_cached
from omnibase_core.mixins.mixin_lazy_value import MixinLazyValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestMixinLazyEvaluationBasicBehavior:
    """Test basic MixinLazyEvaluation initialization and behaviors."""

    def test_mixin_initialization(self):
        """Test MixinLazyEvaluation initializes properly."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        assert isinstance(node, MixinLazyEvaluation)
        assert hasattr(node, "_lazy_cache")
        assert isinstance(node._lazy_cache, dict)

    def test_mixin_in_multiple_inheritance(self):
        """Test MixinLazyEvaluation works in multiple inheritance."""

        class BaseNode:
            pass

        class TestNode(MixinLazyEvaluation, BaseNode):
            pass

        node = TestNode()
        assert isinstance(node, MixinLazyEvaluation)
        assert isinstance(node, BaseNode)


class TestLazyProperty:
    """Test lazy_property functionality."""

    def test_lazy_property_creation(self):
        """Test creating a lazy property."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()

        def compute_value():
            return "computed"

        lazy_val = node.lazy_property("test_key", compute_value)

        assert isinstance(lazy_val, MixinLazyValue)
        assert lazy_val.get() == "computed"

    def test_lazy_property_caching(self):
        """Test lazy property caching behavior."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        call_count = {"count": 0}

        def compute_expensive():
            call_count["count"] += 1
            return "expensive_result"

        lazy_val = node.lazy_property("expensive", compute_expensive, cache=True)

        # First access computes
        result1 = lazy_val.get()
        assert call_count["count"] == 1

        # Second access uses cache
        result2 = lazy_val.get()
        assert call_count["count"] == 1  # Not incremented
        assert result1 == result2

    def test_lazy_property_no_caching(self):
        """Test lazy property without caching."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        call_count = {"count": 0}

        def compute_value():
            call_count["count"] += 1
            return "result"

        lazy_val = node.lazy_property("no_cache", compute_value, cache=False)

        # Each access recomputes
        result1 = lazy_val.get()
        result2 = lazy_val.get()

        assert call_count["count"] == 2
        assert result1 == result2

    def test_lazy_property_reuse(self):
        """Test reusing existing lazy property."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()

        def compute1():
            return "value1"

        def compute2():
            return "value2"

        # First registration
        lazy1 = node.lazy_property("shared_key", compute1)
        result1 = lazy1.get()

        # Second registration with same key - should return existing
        lazy2 = node.lazy_property("shared_key", compute2)
        result2 = lazy2.get()

        assert lazy1 is lazy2
        assert result1 == result2 == "value1"  # Uses first computation


class TestLazyModelDump:
    """Test lazy_model_dump functionality."""

    def test_lazy_model_dump_basic(self):
        """Test lazy model dump with Pydantic model."""

        class TestModel(MixinLazyEvaluation, BaseModel):
            name: str = "test"
            value: int = 42

        model = TestModel()
        lazy_dump = model.lazy_model_dump()

        assert isinstance(lazy_dump, MixinLazyValue)
        result = lazy_dump.get()

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_lazy_model_dump_with_exclude(self):
        """Test lazy model dump with field exclusion."""

        class TestModel(MixinLazyEvaluation, BaseModel):
            name: str = "test"
            secret: str = "hidden"
            value: int = 42

        model = TestModel()
        lazy_dump = model.lazy_model_dump(exclude={"secret"})

        result = lazy_dump.get()

        assert "name" in result
        assert "value" in result
        assert "secret" not in result

    def test_lazy_model_dump_with_alias(self):
        """Test lazy model dump with field aliases."""

        class TestModel(MixinLazyEvaluation, BaseModel):
            internal_name: str = "test"

            class Config:
                fields = {"internal_name": {"alias": "name"}}

        model = TestModel()
        lazy_dump = model.lazy_model_dump(by_alias=True)

        result = lazy_dump.get()
        assert isinstance(result, dict)

    def test_lazy_model_dump_non_basemodel_raises_error(self):
        """Test lazy model dump raises error for non-BaseModel."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        lazy_dump = node.lazy_model_dump()

        with pytest.raises(ModelOnexError) as exc_info:
            lazy_dump.get()

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH


class TestLazySerializeNested:
    """Test lazy_serialize_nested functionality."""

    def test_lazy_serialize_nested_with_object(self):
        """Test lazy serialization of nested object."""

        class NestedModel(BaseModel):
            nested_value: str = "nested"

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        nested = NestedModel()

        lazy_serialized = node.lazy_serialize_nested(nested, "nested_obj")
        result = lazy_serialized.get()

        assert isinstance(result, dict)
        assert result["nested_value"] == "nested"

    def test_lazy_serialize_nested_with_none(self):
        """Test lazy serialization with None object."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        lazy_serialized = node.lazy_serialize_nested(None, "null_obj")

        result = lazy_serialized.get()
        assert result is None


class TestLazyStringConversion:
    """Test lazy_string_conversion functionality."""

    def test_lazy_string_conversion_with_basemodel(self):
        """Test lazy string conversion with BaseModel."""

        class TestModel(BaseModel):
            name: str = "test"

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        model = TestModel()

        lazy_str = node.lazy_string_conversion(model, "model_obj")
        result = lazy_str.get()

        assert isinstance(result, str)
        assert "test" in result

    def test_lazy_string_conversion_with_none(self):
        """Test lazy string conversion with None."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        lazy_str = node.lazy_string_conversion(None, "null_obj")

        result = lazy_str.get()
        assert result == ""

    def test_lazy_string_conversion_without_model_dump(self):
        """Test lazy string conversion for objects without model_dump."""

        class SimpleObject:
            def __str__(self):
                return "simple_object"

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        obj = SimpleObject()

        lazy_str = node.lazy_string_conversion(obj, "simple_obj")
        result = lazy_str.get()

        assert result == "simple_object"


class TestCacheInvalidation:
    """Test cache invalidation functionality."""

    def test_invalidate_all_cache(self):
        """Test invalidating entire lazy cache."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()

        # Create multiple lazy properties
        node.lazy_property("key1", lambda: "value1").get()
        node.lazy_property("key2", lambda: "value2").get()
        node.lazy_property("key3", lambda: "value3").get()

        # All should be computed
        assert all(lv.is_computed() for lv in node._lazy_cache.values())

        # Invalidate all
        node.invalidate_lazy_cache()

        # All should be invalidated
        assert not any(lv.is_computed() for lv in node._lazy_cache.values())

    def test_invalidate_cache_by_pattern(self):
        """Test invalidating cache by pattern."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()

        # Create lazy properties with different patterns
        node.lazy_property("user_data", lambda: "user").get()
        node.lazy_property("user_profile", lambda: "profile").get()
        node.lazy_property("system_config", lambda: "config").get()

        # All computed
        assert all(lv.is_computed() for lv in node._lazy_cache.values())

        # Invalidate only "user" pattern
        node.invalidate_lazy_cache(pattern="user")

        # Check which are invalidated
        assert not node._lazy_cache["user_data"].is_computed()
        assert not node._lazy_cache["user_profile"].is_computed()
        assert node._lazy_cache["system_config"].is_computed()


class TestCacheStatistics:
    """Test cache statistics functionality."""

    def test_get_cache_stats_empty(self):
        """Test cache stats with empty cache."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        stats = node.get_lazy_cache_stats()

        assert stats["total_entries"] == 0
        assert stats["computed_entries"] == 0
        assert stats["pending_entries"] == 0
        assert stats["cache_hit_ratio"] == 0.0

    def test_get_cache_stats_partial(self):
        """Test cache stats with partially computed cache."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()

        # Create some lazy properties
        node.lazy_property("computed1", lambda: "val1").get()
        node.lazy_property("computed2", lambda: "val2").get()
        node.lazy_property("pending1", lambda: "val3")  # Not computed
        node.lazy_property("pending2", lambda: "val4")  # Not computed

        stats = node.get_lazy_cache_stats()

        assert stats["total_entries"] == 4
        assert stats["computed_entries"] == 2
        assert stats["pending_entries"] == 2
        assert stats["cache_hit_ratio"] == 0.5

    def test_get_cache_stats_all_computed(self):
        """Test cache stats with all entries computed."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()

        # Create and compute all
        node.lazy_property("key1", lambda: "val1").get()
        node.lazy_property("key2", lambda: "val2").get()

        stats = node.get_lazy_cache_stats()

        assert stats["total_entries"] == 2
        assert stats["computed_entries"] == 2
        assert stats["pending_entries"] == 0
        assert stats["cache_hit_ratio"] == 1.0


class TestLazyCachedDecorator:
    """Test lazy_cached decorator functionality."""

    def test_lazy_cached_decorator_basic(self):
        """Test lazy_cached decorator on method."""

        class TestNode(MixinLazyEvaluation):
            @lazy_cached()
            def expensive_operation(self):
                return "expensive_result"

        node = TestNode()
        result1 = node.expensive_operation()

        assert isinstance(result1, MixinLazyValue)
        assert result1.get() == "expensive_result"

    def test_lazy_cached_decorator_with_custom_key(self):
        """Test lazy_cached decorator with custom cache key."""

        class TestNode(MixinLazyEvaluation):
            @lazy_cached(cache_key="custom_key")
            def operation(self):
                return "result"

        node = TestNode()
        lazy_result = node.operation()

        assert "custom_key" in node._lazy_cache
        assert lazy_result.get() == "result"

    def test_lazy_cached_decorator_with_arguments(self):
        """Test lazy_cached decorator on method with arguments."""

        class TestNode(MixinLazyEvaluation):
            @lazy_cached()
            def operation_with_args(self, x, y):
                return x + y

        node = TestNode()

        result1 = node.operation_with_args(1, 2)
        result2 = node.operation_with_args(3, 4)

        assert result1.get() == 3
        assert result2.get() == 7


class TestMemoryEfficiency:
    """Test memory efficiency of lazy evaluation."""

    def test_lazy_evaluation_defers_computation(self):
        """Test that lazy evaluation doesn't compute until accessed."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()
        call_count = {"count": 0}

        def expensive_compute():
            call_count["count"] += 1
            return "expensive"

        # Create lazy property but don't access
        lazy_val = node.lazy_property("deferred", expensive_compute)

        # Should not have computed yet
        assert call_count["count"] == 0
        assert not lazy_val.is_computed()

        # Now access it
        result = lazy_val.get()

        # Should have computed
        assert call_count["count"] == 1
        assert lazy_val.is_computed()
        assert result == "expensive"

    def test_memory_efficiency_reporting(self):
        """Test memory efficiency calculation in stats."""

        class TestNode(MixinLazyEvaluation):
            pass

        node = TestNode()

        # Create 10 lazy properties, compute only 3
        for i in range(10):
            lazy_val = node.lazy_property(f"key{i}", lambda i=i: f"val{i}")
            if i < 3:
                lazy_val.get()

        stats = node.get_lazy_cache_stats()

        # 7 out of 10 are pending = 70% memory efficiency
        assert stats["memory_efficiency"] == "70.0%"


class TestIntegrationScenarios:
    """Integration tests for lazy evaluation patterns."""

    def test_combined_lazy_operations(self):
        """Test combining multiple lazy operations."""

        class ComplexModel(MixinLazyEvaluation, BaseModel):
            name: str = "test"
            value: int = 42

        model = ComplexModel()

        # Lazy model dump
        lazy_dump = model.lazy_model_dump()

        # Lazy string conversion
        lazy_str = model.lazy_string_conversion(model, "self")

        # Lazy property
        lazy_prop = model.lazy_property("computed", lambda: "result")

        # Check all are lazy values
        assert isinstance(lazy_dump, MixinLazyValue)
        assert isinstance(lazy_str, MixinLazyValue)
        assert isinstance(lazy_prop, MixinLazyValue)

        # Access them
        dump_result = lazy_dump.get()
        str_result = lazy_str.get()
        prop_result = lazy_prop.get()

        assert isinstance(dump_result, dict)
        assert isinstance(str_result, str)
        assert prop_result == "result"

    def test_lazy_evaluation_workflow(self):
        """Test typical lazy evaluation workflow."""

        class DataProcessor(MixinLazyEvaluation, BaseModel):
            raw_data: list[int] = [1, 2, 3, 4, 5]

            def get_stats(self):
                """Compute expensive statistics lazily."""
                return self.lazy_property("stats", self._compute_stats)

            def _compute_stats(self):
                # Expensive computation
                return {
                    "sum": sum(self.raw_data),
                    "avg": sum(self.raw_data) / len(self.raw_data),
                    "max": max(self.raw_data),
                    "min": min(self.raw_data),
                }

        processor = DataProcessor()

        # Stats not computed yet
        stats = processor.get_lazy_cache_stats()
        assert stats["total_entries"] == 0

        # Access stats
        lazy_stats = processor.get_stats()
        result = lazy_stats.get()

        assert result["sum"] == 15
        assert result["avg"] == 3.0

        # Stats now cached
        stats = processor.get_lazy_cache_stats()
        assert stats["computed_entries"] == 1
