# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ModelCapabilityCaching handler.

TDD tests - written FIRST before implementation.

This handler replaces MixinCaching with a composition-based approach.
No inheritance required - the handler is a standalone Pydantic model that
can be used via composition with any component needing caching.

Ticket: OMN-1112

Coverage target: 60%+ (stub implementation with defensive attribute handling)
"""

import pytest

from omnibase_core.pipeline.handlers.model_capability_caching import (
    ModelCapabilityCaching,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def caching_handler() -> ModelCapabilityCaching:
    """Create a default ModelCapabilityCaching handler.

    Returns:
        ModelCapabilityCaching instance with default settings.
    """
    return ModelCapabilityCaching()


@pytest.fixture
def disabled_caching_handler() -> ModelCapabilityCaching:
    """Create a disabled ModelCapabilityCaching handler.

    Returns:
        ModelCapabilityCaching instance with caching disabled.
    """
    return ModelCapabilityCaching(enabled=False)


@pytest.fixture
def custom_ttl_handler() -> ModelCapabilityCaching:
    """Create a ModelCapabilityCaching handler with custom TTL.

    Returns:
        ModelCapabilityCaching instance with 600s TTL.
    """
    return ModelCapabilityCaching(default_ttl_seconds=600)


# =============================================================================
# Test Initialization
# =============================================================================


@pytest.mark.unit
class TestModelCapabilityCachingInit:
    """Test initialization of ModelCapabilityCaching."""

    def test_default_initialization(self) -> None:
        """Handler initializes with sensible defaults."""
        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        handler = ModelCapabilityCaching()

        assert handler.enabled is True
        assert handler.default_ttl_seconds == 3600

    def test_initialization_with_custom_ttl(self) -> None:
        """Handler accepts custom TTL value."""
        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        handler = ModelCapabilityCaching(default_ttl_seconds=600)

        assert handler.enabled is True
        assert handler.default_ttl_seconds == 600

    def test_initialization_disabled(self) -> None:
        """Handler can be initialized in disabled state."""
        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        handler = ModelCapabilityCaching(enabled=False)

        assert handler.enabled is False
        assert handler.default_ttl_seconds == 3600

    def test_initialization_with_all_options(self) -> None:
        """Handler accepts all configuration options."""
        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        handler = ModelCapabilityCaching(enabled=False, default_ttl_seconds=120)

        assert handler.enabled is False
        assert handler.default_ttl_seconds == 120

    def test_is_pydantic_model(self) -> None:
        """Handler is a Pydantic BaseModel (not a mixin)."""
        from pydantic import BaseModel

        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        handler = ModelCapabilityCaching()

        assert isinstance(handler, BaseModel)


# =============================================================================
# Test generate_cache_key
# =============================================================================


@pytest.mark.unit
class TestGenerateCacheKey:
    """Test generate_cache_key method."""

    def test_generate_cache_key_from_dict(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Cache key is generated from dict data."""
        data = {"user_id": 123, "action": "process"}

        key = caching_handler.generate_cache_key(data)

        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 hex digest is 64 chars

    def test_generate_cache_key_from_string(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Cache key is generated from string data."""
        data = "simple string input"

        key = caching_handler.generate_cache_key(data)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_generate_cache_key_consistency(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Same data produces same cache key (deterministic)."""
        data = {"a": 1, "b": 2}

        key1 = caching_handler.generate_cache_key(data)
        key2 = caching_handler.generate_cache_key(data)

        assert key1 == key2

    def test_generate_cache_key_dict_order_independence(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Dict key order does not affect cache key (uses sort_keys)."""
        data1 = {"b": 2, "a": 1}
        data2 = {"a": 1, "b": 2}

        key1 = caching_handler.generate_cache_key(data1)
        key2 = caching_handler.generate_cache_key(data2)

        assert key1 == key2

    def test_generate_cache_key_different_data_different_keys(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Different data produces different cache keys."""
        data1 = {"value": 1}
        data2 = {"value": 2}

        key1 = caching_handler.generate_cache_key(data1)
        key2 = caching_handler.generate_cache_key(data2)

        assert key1 != key2

    def test_generate_cache_key_handles_non_serializable(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Non-JSON-serializable data falls back to str() representation."""

        class CustomObject:
            def __str__(self) -> str:
                return "custom_repr"

        obj = CustomObject()

        # Should not raise, should return a valid key
        key = caching_handler.generate_cache_key(obj)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_generate_cache_key_nested_dict(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Cache key works with nested dictionaries."""
        data = {"outer": {"inner": {"deep": "value"}}, "list": [1, 2, 3]}

        key = caching_handler.generate_cache_key(data)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_generate_cache_key_with_none(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Cache key handles None values."""
        data = {"key": None}

        key = caching_handler.generate_cache_key(data)

        assert isinstance(key, str)
        assert len(key) == 64


# =============================================================================
# Test get_cached (async)
# =============================================================================


@pytest.mark.unit
class TestGetCached:
    """Test get_cached async method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_cached_returns_none_when_not_found(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cached returns None for non-existent key."""
        result = await caching_handler.get_cached("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_cached_returns_stored_value(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cached returns previously stored value."""
        cache_key = "test_key"
        test_value = {"data": "test_value", "count": 42}

        await caching_handler.set_cached(cache_key, test_value)
        result = await caching_handler.get_cached(cache_key)

        assert result == test_value

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_cached_returns_none_when_disabled(
        self, disabled_caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cached returns None when caching is disabled."""
        # First store something (though it won't be stored due to disabled)
        cache_key = "test_key"
        test_value = "test_value"

        await disabled_caching_handler.set_cached(cache_key, test_value)
        result = await disabled_caching_handler.get_cached(cache_key)

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_cached_various_value_types(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cached works with various value types."""
        test_cases = [
            ("string_key", "simple string"),
            ("int_key", 12345),
            ("float_key", 3.14159),
            ("list_key", [1, 2, 3, "four"]),
            ("dict_key", {"nested": {"value": True}}),
            ("bool_key", True),
            ("none_key", None),
        ]

        for key, value in test_cases:
            await caching_handler.set_cached(key, value)
            result = await caching_handler.get_cached(key)
            assert result == value, f"Failed for key={key}, value={value}"


# =============================================================================
# Test set_cached (async)
# =============================================================================


@pytest.mark.unit
class TestSetCached:
    """Test set_cached async method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_stores_value(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """set_cached stores value successfully."""
        cache_key = "store_key"
        test_value = {"stored": True}

        await caching_handler.set_cached(cache_key, test_value)
        result = await caching_handler.get_cached(cache_key)

        assert result == test_value

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_respects_enabled_flag(
        self, disabled_caching_handler: ModelCapabilityCaching
    ) -> None:
        """set_cached does not store when disabled."""
        cache_key = "store_key"
        test_value = {"stored": True}

        await disabled_caching_handler.set_cached(cache_key, test_value)

        # Get stats to verify nothing was stored
        stats = disabled_caching_handler.get_cache_stats()
        assert stats["entries"] == 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_overwrites_existing(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """set_cached overwrites existing value for same key."""
        cache_key = "overwrite_key"
        value1 = "first_value"
        value2 = "second_value"

        await caching_handler.set_cached(cache_key, value1)
        await caching_handler.set_cached(cache_key, value2)
        result = await caching_handler.get_cached(cache_key)

        assert result == value2

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_with_custom_ttl(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """set_cached accepts custom TTL (stored for future backend use)."""
        cache_key = "ttl_key"
        test_value = "ttl_value"

        # Should not raise even though TTL is not implemented in stub
        await caching_handler.set_cached(cache_key, test_value, ttl_seconds=60)
        result = await caching_handler.get_cached(cache_key)

        assert result == test_value

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_multiple_keys(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """set_cached can store multiple different keys."""
        entries = [
            ("key1", "value1"),
            ("key2", "value2"),
            ("key3", "value3"),
        ]

        for key, value in entries:
            await caching_handler.set_cached(key, value)

        for key, expected_value in entries:
            result = await caching_handler.get_cached(key)
            assert result == expected_value


# =============================================================================
# Test invalidate_cache (async)
# =============================================================================


@pytest.mark.unit
class TestInvalidateCache:
    """Test invalidate_cache async method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_invalidate_cache_removes_key(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """invalidate_cache removes the specified key."""
        cache_key = "to_remove"
        await caching_handler.set_cached(cache_key, "some_value")

        await caching_handler.invalidate_cache(cache_key)
        result = await caching_handler.get_cached(cache_key)

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_invalidate_cache_handles_nonexistent_key(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """invalidate_cache does not raise for nonexistent key."""
        # Should not raise
        await caching_handler.invalidate_cache("never_existed")

        # Verify handler still works
        stats = caching_handler.get_cache_stats()
        assert stats["enabled"] is True

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_invalidate_cache_only_affects_specified_key(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """invalidate_cache only removes the specified key, not others."""
        await caching_handler.set_cached("keep_me", "value1")
        await caching_handler.set_cached("remove_me", "value2")

        await caching_handler.invalidate_cache("remove_me")

        assert await caching_handler.get_cached("keep_me") == "value1"
        assert await caching_handler.get_cached("remove_me") is None


# =============================================================================
# Test clear_cache (async)
# =============================================================================


@pytest.mark.unit
class TestClearCache:
    """Test clear_cache async method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_clear_cache_removes_all_entries(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """clear_cache removes all cached entries."""
        # Store multiple entries
        await caching_handler.set_cached("key1", "value1")
        await caching_handler.set_cached("key2", "value2")
        await caching_handler.set_cached("key3", "value3")

        await caching_handler.clear_cache()

        assert await caching_handler.get_cached("key1") is None
        assert await caching_handler.get_cached("key2") is None
        assert await caching_handler.get_cached("key3") is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_clear_cache_on_empty_cache(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """clear_cache works on empty cache without error."""
        # Should not raise
        await caching_handler.clear_cache()

        stats = caching_handler.get_cache_stats()
        assert stats["entries"] == 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_clear_cache_stats_reflect_cleared(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Stats reflect cleared state after clear_cache."""
        await caching_handler.set_cached("key1", "value1")
        await caching_handler.set_cached("key2", "value2")

        stats_before = caching_handler.get_cache_stats()
        assert stats_before["entries"] == 2

        await caching_handler.clear_cache()

        stats_after = caching_handler.get_cache_stats()
        assert stats_after["entries"] == 0
        assert stats_after["keys"] == []


# =============================================================================
# Test get_cache_stats
# =============================================================================


@pytest.mark.unit
class TestGetCacheStats:
    """Test get_cache_stats method."""

    def test_get_cache_stats_returns_typed_dict(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cache_stats returns TypedDictCacheStats structure."""
        stats = caching_handler.get_cache_stats()

        assert "enabled" in stats
        assert "entries" in stats
        assert "keys" in stats

    def test_get_cache_stats_initial_state(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cache_stats shows correct initial state."""
        stats = caching_handler.get_cache_stats()

        assert stats["enabled"] is True
        assert stats["entries"] == 0
        assert stats["keys"] == []

    def test_get_cache_stats_disabled_handler(
        self, disabled_caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cache_stats shows disabled state."""
        stats = disabled_caching_handler.get_cache_stats()

        assert stats["enabled"] is False
        assert stats["entries"] == 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_cache_stats_reflects_entries(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cache_stats correctly counts entries."""
        await caching_handler.set_cached("key1", "value1")
        await caching_handler.set_cached("key2", "value2")

        stats = caching_handler.get_cache_stats()

        assert stats["entries"] == 2
        assert set(stats["keys"]) == {"key1", "key2"}

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_cache_stats_after_invalidation(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """get_cache_stats reflects invalidation."""
        await caching_handler.set_cached("key1", "value1")
        await caching_handler.set_cached("key2", "value2")
        await caching_handler.invalidate_cache("key1")

        stats = caching_handler.get_cache_stats()

        assert stats["entries"] == 1
        assert stats["keys"] == ["key2"]


# =============================================================================
# Test Instance Isolation
# =============================================================================


@pytest.mark.unit
class TestInstanceIsolation:
    """Test cache isolation between handler instances."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_cache_isolation_per_instance(self) -> None:
        """Each handler instance has its own isolated cache."""
        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        handler1 = ModelCapabilityCaching()
        handler2 = ModelCapabilityCaching()

        await handler1.set_cached("shared_key", "handler1_value")
        await handler2.set_cached("shared_key", "handler2_value")

        result1 = await handler1.get_cached("shared_key")
        result2 = await handler2.get_cached("shared_key")

        assert result1 == "handler1_value"
        assert result2 == "handler2_value"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_clear_cache_does_not_affect_other_instances(self) -> None:
        """Clearing one instance does not affect others."""
        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        handler1 = ModelCapabilityCaching()
        handler2 = ModelCapabilityCaching()

        await handler1.set_cached("key", "value1")
        await handler2.set_cached("key", "value2")

        await handler1.clear_cache()

        assert await handler1.get_cached("key") is None
        assert await handler2.get_cached("key") == "value2"


# =============================================================================
# Test Handler Independence (No Mixin Required)
# =============================================================================


@pytest.mark.unit
class TestHandlerIndependence:
    """Test that handler works standalone without mixin inheritance."""

    def test_handler_works_standalone(self) -> None:
        """Handler can be used without inheriting from a mixin."""
        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        # Handler should be usable as a standalone component
        handler = ModelCapabilityCaching()

        # Should have all expected methods
        assert hasattr(handler, "generate_cache_key")
        assert hasattr(handler, "get_cached")
        assert hasattr(handler, "set_cached")
        assert hasattr(handler, "invalidate_cache")
        assert hasattr(handler, "clear_cache")
        assert hasattr(handler, "get_cache_stats")

    def test_handler_not_a_mixin(self) -> None:
        """Handler is not designed as a mixin (Pydantic model instead)."""
        from pydantic import BaseModel

        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        handler = ModelCapabilityCaching()

        # Should be a Pydantic model
        assert isinstance(handler, BaseModel)

        # Should NOT require cooperative inheritance
        # (no need for super().__init__() chains like mixins)

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_handler_composition_pattern(self) -> None:
        """Handler supports composition pattern (embedding in other classes)."""
        from pydantic import BaseModel

        from omnibase_core.pipeline.handlers.model_capability_caching import (
            ModelCapabilityCaching,
        )

        class MyService(BaseModel):
            """Example service using caching via composition."""

            cache: ModelCapabilityCaching = ModelCapabilityCaching()

            async def expensive_operation(self, key: str) -> str:
                cache_key = self.cache.generate_cache_key({"key": key})
                cached = await self.cache.get_cached(cache_key)
                if cached is not None:
                    return str(cached)

                # Simulate expensive operation
                result = f"computed_{key}"
                await self.cache.set_cached(cache_key, result)
                return result

        service = MyService()

        # First call computes
        result1 = await service.expensive_operation("test")
        assert result1 == "computed_test"

        # Second call should get cached value
        result2 = await service.expensive_operation("test")
        assert result2 == "computed_test"

        # Verify it's in cache
        stats = service.cache.get_cache_stats()
        assert stats["entries"] == 1


# =============================================================================
# Test Edge Cases
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_generate_cache_key_empty_dict(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Empty dict produces valid cache key."""
        key = caching_handler.generate_cache_key({})

        assert isinstance(key, str)
        assert len(key) == 64

    def test_generate_cache_key_empty_string(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Empty string produces valid cache key."""
        key = caching_handler.generate_cache_key("")

        assert isinstance(key, str)
        assert len(key) == 64

    def test_generate_cache_key_empty_list(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Empty list produces valid cache key."""
        key = caching_handler.generate_cache_key([])

        assert isinstance(key, str)
        assert len(key) == 64

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_empty_string_key(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Empty string key is valid."""
        await caching_handler.set_cached("", "empty_key_value")
        result = await caching_handler.get_cached("")

        assert result == "empty_key_value"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_unicode_key(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Unicode characters in key are handled."""
        unicode_key = "key_with_unicode_"
        await caching_handler.set_cached(unicode_key, "unicode_value")
        result = await caching_handler.get_cached(unicode_key)

        assert result == "unicode_value"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_large_value(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Large values can be cached."""
        large_value = {"data": "x" * 10000}  # 10KB of data
        await caching_handler.set_cached("large_key", large_value)
        result = await caching_handler.get_cached("large_key")

        assert result == large_value

    def test_generate_cache_key_circular_reference_fallback(
        self, caching_handler: ModelCapabilityCaching
    ) -> None:
        """Circular references fall back to str() representation."""
        circular: dict[str, object] = {}
        circular["self"] = circular

        # Should not raise, should fall back to str()
        key = caching_handler.generate_cache_key(circular)

        assert isinstance(key, str)
        assert len(key) == 64
