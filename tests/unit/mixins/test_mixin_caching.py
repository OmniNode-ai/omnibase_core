"""
Tests for MixinCaching - Result caching mixin.

Coverage target: 60%+ (stub implementation with straightforward testing)
"""

import pytest

from omnibase_core.mixins.mixin_caching import MixinCaching


class MockNode(MixinCaching):
    """Mock node class that uses MixinCaching."""


@pytest.mark.unit
class TestMixinCachingInit:
    """Test suite for MixinCaching initialization."""

    def test_init_sets_cache_enabled(self):
        """Test that __init__ sets _cache_enabled to True."""
        node = MockNode()
        assert node._cache_enabled is True

    def test_init_creates_empty_cache_dict(self):
        """Test that __init__ creates empty _cache_data dict."""
        node = MockNode()
        assert node._cache_data == {}
        assert isinstance(node._cache_data, dict)


@pytest.mark.unit
class TestGenerateCacheKey:
    """Test suite for generate_cache_key method."""

    def test_generate_key_from_dict(self):
        """Test cache key generation from dictionary."""
        node = MockNode()
        data = {"key1": "value1", "key2": "value2"}

        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64  # SHA256 hash length
        # Same data should produce same key
        assert cache_key == node.generate_cache_key(data)

    def test_generate_key_from_string(self):
        """Test cache key generation from string."""
        node = MockNode()
        data = "test_string"

        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64
        # Different strings should produce different keys
        assert cache_key != node.generate_cache_key("different_string")

    def test_generate_key_from_int(self):
        """Test cache key generation from integer."""
        node = MockNode()
        data = 12345

        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64

    def test_generate_key_from_list(self):
        """Test cache key generation from list."""
        node = MockNode()
        data = [1, 2, 3, "test"]

        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64

    def test_generate_key_consistent_for_same_dict(self):
        """Test that same dictionary produces same key."""
        node = MockNode()
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 2, "a": 1}  # Different order, but same content

        # Should produce same key due to sort_keys=True in JSON serialization
        key1 = node.generate_cache_key(dict1)
        key2 = node.generate_cache_key(dict2)

        assert key1 == key2

    def test_generate_key_handles_non_serializable_data(self):
        """Test cache key generation with non-JSON-serializable data."""
        node = MockNode()

        # Object that can't be serialized to JSON
        class CustomObject:
            def __str__(self):
                return "custom_object"

        data = CustomObject()

        # Should fallback to str() and not raise error
        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64

    def test_generate_key_different_for_different_data(self):
        """Test that different data produces different keys."""
        node = MockNode()

        key1 = node.generate_cache_key({"data": "value1"})
        key2 = node.generate_cache_key({"data": "value2"})

        assert key1 != key2


@pytest.mark.unit
class TestGetCached:
    """Test suite for get_cached method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_get_cached_returns_none_when_not_found(self):
        """Test that get_cached returns None for non-existent key."""
        node = MockNode()

        result = await node.get_cached("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_get_cached_returns_value_when_found(self):
        """Test that get_cached returns stored value."""
        node = MockNode()
        cache_key = "test_key"
        cache_value = {"result": "success"}

        # Manually set cache value
        node._cache_data[cache_key] = cache_value

        result = await node.get_cached(cache_key)

        assert result == cache_value

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_get_cached_respects_disabled_flag(self):
        """Test that get_cached returns None when caching is disabled."""
        node = MockNode()
        cache_key = "test_key"
        cache_value = "test_value"

        # Set cache value
        node._cache_data[cache_key] = cache_value

        # Disable caching
        node._cache_enabled = False

        result = await node.get_cached(cache_key)

        assert result is None


@pytest.mark.unit
class TestSetCached:
    """Test suite for set_cached method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_set_cached_stores_value(self):
        """Test that set_cached stores value in cache."""
        node = MockNode()
        cache_key = "test_key"
        cache_value = "test_value"

        await node.set_cached(cache_key, cache_value)

        assert node._cache_data[cache_key] == cache_value

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_set_cached_with_ttl(self):
        """Test that set_cached accepts TTL parameter (even though it's ignored in stub)."""
        node = MockNode()
        cache_key = "test_key"
        cache_value = "test_value"

        # TTL is ignored in stub implementation, but should not raise error
        await node.set_cached(cache_key, cache_value, ttl_seconds=600)

        assert node._cache_data[cache_key] == cache_value

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_set_cached_overwrites_existing_value(self):
        """Test that set_cached overwrites existing cached value."""
        node = MockNode()
        cache_key = "test_key"

        await node.set_cached(cache_key, "value1")
        assert node._cache_data[cache_key] == "value1"

        await node.set_cached(cache_key, "value2")
        assert node._cache_data[cache_key] == "value2"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_set_cached_respects_disabled_flag(self):
        """Test that set_cached does not store when caching is disabled."""
        node = MockNode()
        node._cache_enabled = False

        await node.set_cached("test_key", "test_value")

        assert "test_key" not in node._cache_data

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_set_cached_handles_complex_values(self):
        """Test that set_cached can store complex data structures."""
        node = MockNode()
        complex_value = {
            "nested": {"data": [1, 2, 3]},
            "list": ["a", "b", "c"],
        }

        await node.set_cached("complex_key", complex_value)

        assert node._cache_data["complex_key"] == complex_value


@pytest.mark.unit
class TestInvalidateCache:
    """Test suite for invalidate_cache method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_invalidate_cache_removes_key(self):
        """Test that invalidate_cache removes specified key."""
        node = MockNode()
        cache_key = "test_key"

        # Set value first
        await node.set_cached(cache_key, "test_value")
        assert cache_key in node._cache_data

        # Invalidate
        await node.invalidate_cache(cache_key)

        assert cache_key not in node._cache_data

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_invalidate_cache_nonexistent_key(self):
        """Test that invalidate_cache handles non-existent key gracefully."""
        node = MockNode()

        # Should not raise error
        await node.invalidate_cache("nonexistent_key")

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_invalidate_cache_leaves_other_keys(self):
        """Test that invalidate_cache only removes specified key."""
        node = MockNode()

        # Set multiple values
        await node.set_cached("key1", "value1")
        await node.set_cached("key2", "value2")
        await node.set_cached("key3", "value3")

        # Invalidate one key
        await node.invalidate_cache("key2")

        # Other keys should remain
        assert "key1" in node._cache_data
        assert "key2" not in node._cache_data
        assert "key3" in node._cache_data


@pytest.mark.unit
class TestClearCache:
    """Test suite for clear_cache method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_clear_cache_removes_all_entries(self):
        """Test that clear_cache removes all cached entries."""
        node = MockNode()

        # Set multiple values
        await node.set_cached("key1", "value1")
        await node.set_cached("key2", "value2")
        await node.set_cached("key3", "value3")

        assert len(node._cache_data) == 3

        # Clear cache
        await node.clear_cache()

        assert len(node._cache_data) == 0
        assert node._cache_data == {}

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_clear_cache_on_empty_cache(self):
        """Test that clear_cache handles empty cache gracefully."""
        node = MockNode()

        # Should not raise error
        await node.clear_cache()

        assert node._cache_data == {}


@pytest.mark.unit
class TestGetCacheStats:
    """Test suite for get_cache_stats method."""

    def test_get_cache_stats_structure(self):
        """Test that get_cache_stats returns proper structure."""
        node = MockNode()

        stats = node.get_cache_stats()

        assert isinstance(stats, dict)
        assert "enabled" in stats
        assert "entries" in stats
        assert "keys" in stats

    def test_get_cache_stats_enabled_flag(self):
        """Test that get_cache_stats includes enabled flag."""
        node = MockNode()

        stats = node.get_cache_stats()
        assert stats["enabled"] is True

        node._cache_enabled = False
        stats = node.get_cache_stats()
        assert stats["enabled"] is False

    def test_get_cache_stats_entry_count(self):
        """Test that get_cache_stats reports correct entry count."""
        node = MockNode()

        # Empty cache
        stats = node.get_cache_stats()
        assert stats["entries"] == 0

        # Add entries
        node._cache_data["key1"] = "value1"
        node._cache_data["key2"] = "value2"

        stats = node.get_cache_stats()
        assert stats["entries"] == 2

    def test_get_cache_stats_keys_list(self):
        """Test that get_cache_stats includes list of keys."""
        node = MockNode()

        node._cache_data["key1"] = "value1"
        node._cache_data["key2"] = "value2"

        stats = node.get_cache_stats()

        assert isinstance(stats["keys"], list)
        assert "key1" in stats["keys"]
        assert "key2" in stats["keys"]
        assert len(stats["keys"]) == 2


@pytest.mark.unit
class TestCachingIntegration:
    """Integration tests for MixinCaching workflow."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_full_cache_workflow(self):
        """Test complete caching workflow: generate key, set, get, invalidate."""
        node = MockNode()

        # Generate key from data
        data = {"param1": "value1", "param2": 123}
        cache_key = node.generate_cache_key(data)

        # Set cached value
        result_value = {"computed": "result"}
        await node.set_cached(cache_key, result_value)

        # Get cached value
        cached_result = await node.get_cached(cache_key)
        assert cached_result == result_value

        # Check stats
        stats = node.get_cache_stats()
        assert stats["entries"] == 1

        # Invalidate
        await node.invalidate_cache(cache_key)
        assert await node.get_cached(cache_key) is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_cache_with_ttl_parameter(self):
        """Test caching workflow with TTL (ignored in stub but should not error)."""
        node = MockNode()

        data = "test_data"
        cache_key = node.generate_cache_key(data)

        # Set with TTL
        await node.set_cached(cache_key, "cached_result", ttl_seconds=300)

        # Should be retrievable (TTL not enforced in stub)
        result = await node.get_cached(cache_key)
        assert result == "cached_result"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_disabled_cache_workflow(self):
        """Test that caching can be disabled and re-enabled."""
        node = MockNode()
        cache_key = "test_key"

        # Set value with caching enabled
        await node.set_cached(cache_key, "value1")
        assert await node.get_cached(cache_key) == "value1"

        # Disable caching
        node._cache_enabled = False

        # Get should return None
        assert await node.get_cached(cache_key) is None

        # Set should not store
        await node.set_cached(cache_key, "value2")
        # Still has old value in dict, but get returns None
        assert await node.get_cached(cache_key) is None

        # Re-enable caching
        node._cache_enabled = True

        # Can now get old value
        assert await node.get_cached(cache_key) == "value1"
