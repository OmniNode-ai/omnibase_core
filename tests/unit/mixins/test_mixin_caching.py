"""
Tests for MixinCaching - Result caching mixin with L1/L2 support.

Coverage target: 60%+ (comprehensive testing of L1/L2 coordination)

Test Categories:
    - TestMixinCachingInit: Initialization tests
    - TestGenerateCacheKey: Cache key generation tests
    - TestGetCached: L1/L2 read path tests
    - TestSetCached: L1/L2 write path tests
    - TestInvalidateCache: Invalidation tests
    - TestClearCache: Clear cache tests
    - TestGetCacheStats: Statistics tests
    - TestCachingIntegration: End-to-end workflow tests
    - TestTTLEnforcement: TTL expiration tests
    - TestL2Coordination: L1/L2 coordination tests
    - TestGracefulDegradation: Fallback behavior tests
    - TestBackwardCompatibility: Existing behavior tests
"""

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omnibase_core.mixins.mixin_caching import MixinCaching
from omnibase_core.protocols.cache import ProtocolCacheBackend


class MockNode(MixinCaching):
    """Mock node class that uses MixinCaching."""


class MockCacheBackend:
    """Mock L2 cache backend implementing ProtocolCacheBackend."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._ttls: dict[str, int | None] = {}

    async def get(self, key: str) -> Any | None:
        return self._data.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._data[key] = value
        self._ttls[key] = ttl_seconds

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._ttls.pop(key, None)

    async def clear(self) -> None:
        self._data.clear()
        self._ttls.clear()

    async def exists(self, key: str) -> bool:
        return key in self._data


class FailingCacheBackend:
    """Mock L2 cache backend that always fails."""

    async def get(self, key: str) -> Any | None:
        raise ConnectionError("Redis connection failed")

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        raise ConnectionError("Redis connection failed")

    async def delete(self, key: str) -> None:
        raise ConnectionError("Redis connection failed")

    async def clear(self) -> None:
        raise ConnectionError("Redis connection failed")

    async def exists(self, key: str) -> bool:
        raise ConnectionError("Redis connection failed")


@pytest.mark.unit
class TestMixinCachingInit:
    """Test suite for MixinCaching initialization."""

    @pytest.mark.timeout(60)
    def test_init_sets_cache_enabled(self):
        """Test that __init__ sets _cache_enabled to True."""
        node = MockNode()
        assert node._cache_enabled is True

    @pytest.mark.timeout(60)
    def test_init_creates_empty_cache_dict(self):
        """Test that __init__ creates empty _cache_data dict."""
        node = MockNode()
        assert node._cache_data == {}
        assert isinstance(node._cache_data, dict)

    @pytest.mark.timeout(60)
    def test_init_with_no_backend(self):
        """Test initialization without L2 backend."""
        node = MockNode()
        assert node._cache_backend is None
        assert node.has_l2_backend() is False

    @pytest.mark.timeout(60)
    def test_init_with_backend(self):
        """Test initialization with L2 backend."""
        backend = MockCacheBackend()
        node = MockNode(backend=backend)
        assert node._cache_backend is backend
        assert node.has_l2_backend() is True

    @pytest.mark.timeout(60)
    def test_init_with_default_ttl(self):
        """Test initialization with default TTL."""
        node = MockNode(default_ttl_seconds=300)
        assert node._default_ttl_seconds == 300

    @pytest.mark.timeout(60)
    def test_init_without_default_ttl(self):
        """Test initialization without default TTL."""
        node = MockNode()
        assert node._default_ttl_seconds is None


@pytest.mark.unit
class TestGenerateCacheKey:
    """Test suite for generate_cache_key method."""

    @pytest.mark.timeout(60)
    def test_generate_key_from_dict(self):
        """Test cache key generation from dictionary."""
        node = MockNode()
        data = {"key1": "value1", "key2": "value2"}

        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64  # SHA256 hash length
        # Same data should produce same key
        assert cache_key == node.generate_cache_key(data)

    @pytest.mark.timeout(60)
    def test_generate_key_from_string(self):
        """Test cache key generation from string."""
        node = MockNode()
        data = "test_string"

        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64
        # Different strings should produce different keys
        assert cache_key != node.generate_cache_key("different_string")

    @pytest.mark.timeout(60)
    def test_generate_key_from_int(self):
        """Test cache key generation from integer."""
        node = MockNode()
        data = 12345

        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64

    @pytest.mark.timeout(60)
    def test_generate_key_from_list(self):
        """Test cache key generation from list."""
        node = MockNode()
        data = [1, 2, 3, "test"]

        cache_key = node.generate_cache_key(data)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64

    @pytest.mark.timeout(60)
    def test_generate_key_consistent_for_same_dict(self):
        """Test that same dictionary produces same key."""
        node = MockNode()
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 2, "a": 1}  # Different order, but same content

        # Should produce same key due to sort_keys=True in JSON serialization
        key1 = node.generate_cache_key(dict1)
        key2 = node.generate_cache_key(dict2)

        assert key1 == key2

    @pytest.mark.timeout(60)
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

    @pytest.mark.timeout(60)
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
    @pytest.mark.timeout(60)
    async def test_get_cached_returns_none_when_not_found(self):
        """Test that get_cached returns None for non-existent key."""
        node = MockNode()

        result = await node.get_cached("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_cached_returns_value_when_found_in_l1(self):
        """Test that get_cached returns L1 cached value."""
        node = MockNode()
        cache_key = "test_key"
        cache_value = {"result": "success"}

        # Manually set L1 cache value (value, expiry)
        node._cache_data[cache_key] = (cache_value, None)

        result = await node.get_cached(cache_key)

        assert result == cache_value

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_cached_respects_disabled_flag(self):
        """Test that get_cached returns None when caching is disabled."""
        node = MockNode()
        cache_key = "test_key"
        cache_value = "test_value"

        # Set cache value
        node._cache_data[cache_key] = (cache_value, None)

        # Disable caching
        node._cache_enabled = False

        result = await node.get_cached(cache_key)

        assert result is None


@pytest.mark.unit
class TestSetCached:
    """Test suite for set_cached method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_stores_value_in_l1(self):
        """Test that set_cached stores value in L1 cache."""
        node = MockNode()
        cache_key = "test_key"
        cache_value = "test_value"

        await node.set_cached(cache_key, cache_value)

        value, expiry = node._cache_data[cache_key]
        assert value == cache_value
        assert expiry is None  # No TTL set

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_with_ttl(self):
        """Test that set_cached stores value with TTL."""
        node = MockNode()
        cache_key = "test_key"
        cache_value = "test_value"

        await node.set_cached(cache_key, cache_value, ttl_seconds=600)

        value, expiry = node._cache_data[cache_key]
        assert value == cache_value
        assert expiry is not None
        assert expiry > time.time()  # Expiry is in the future

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_overwrites_existing_value(self):
        """Test that set_cached overwrites existing cached value."""
        node = MockNode()
        cache_key = "test_key"

        await node.set_cached(cache_key, "value1")
        value1, _ = node._cache_data[cache_key]
        assert value1 == "value1"

        await node.set_cached(cache_key, "value2")
        value2, _ = node._cache_data[cache_key]
        assert value2 == "value2"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_respects_disabled_flag(self):
        """Test that set_cached does not store when caching is disabled."""
        node = MockNode()
        node._cache_enabled = False

        await node.set_cached("test_key", "test_value")

        assert "test_key" not in node._cache_data

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_cached_handles_complex_values(self):
        """Test that set_cached can store complex data structures."""
        node = MockNode()
        complex_value = {
            "nested": {"data": [1, 2, 3]},
            "list": ["a", "b", "c"],
        }

        await node.set_cached("complex_key", complex_value)

        value, _ = node._cache_data["complex_key"]
        assert value == complex_value


@pytest.mark.unit
class TestInvalidateCache:
    """Test suite for invalidate_cache method."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
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
    @pytest.mark.timeout(60)
    async def test_invalidate_cache_nonexistent_key(self):
        """Test that invalidate_cache handles non-existent key gracefully."""
        node = MockNode()

        # Should not raise error
        await node.invalidate_cache("nonexistent_key")

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
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
    @pytest.mark.timeout(60)
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
    @pytest.mark.timeout(60)
    async def test_clear_cache_on_empty_cache(self):
        """Test that clear_cache handles empty cache gracefully."""
        node = MockNode()

        # Should not raise error
        await node.clear_cache()

        assert node._cache_data == {}


@pytest.mark.unit
class TestGetCacheStats:
    """Test suite for get_cache_stats method."""

    @pytest.mark.timeout(60)
    def test_get_cache_stats_structure(self):
        """Test that get_cache_stats returns proper structure."""
        node = MockNode()

        stats = node.get_cache_stats()

        assert isinstance(stats, dict)
        assert "enabled" in stats
        assert "entries" in stats
        assert "keys" in stats

    @pytest.mark.timeout(60)
    def test_get_cache_stats_enabled_flag(self):
        """Test that get_cache_stats includes enabled flag."""
        node = MockNode()

        stats = node.get_cache_stats()
        assert stats["enabled"] is True

        node._cache_enabled = False
        stats = node.get_cache_stats()
        assert stats["enabled"] is False

    @pytest.mark.timeout(60)
    def test_get_cache_stats_entry_count(self):
        """Test that get_cache_stats reports correct entry count."""
        node = MockNode()

        # Empty cache
        stats = node.get_cache_stats()
        assert stats["entries"] == 0

        # Add entries (using new format: value, expiry)
        node._cache_data["key1"] = ("value1", None)
        node._cache_data["key2"] = ("value2", None)

        stats = node.get_cache_stats()
        assert stats["entries"] == 2

    @pytest.mark.timeout(60)
    def test_get_cache_stats_keys_list(self):
        """Test that get_cache_stats includes list of keys."""
        node = MockNode()

        node._cache_data["key1"] = ("value1", None)
        node._cache_data["key2"] = ("value2", None)

        stats = node.get_cache_stats()

        assert isinstance(stats["keys"], list)
        assert "key1" in stats["keys"]
        assert "key2" in stats["keys"]
        assert len(stats["keys"]) == 2


@pytest.mark.unit
class TestCachingIntegration:
    """Integration tests for MixinCaching workflow."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
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
    @pytest.mark.timeout(60)
    async def test_cache_with_ttl_parameter(self):
        """Test caching workflow with TTL."""
        node = MockNode()

        data = "test_data"
        cache_key = node.generate_cache_key(data)

        # Set with TTL
        await node.set_cached(cache_key, "cached_result", ttl_seconds=300)

        # Should be retrievable
        result = await node.get_cached(cache_key)
        assert result == "cached_result"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
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

        # Re-enable caching
        node._cache_enabled = True

        # Can now get old value (value2 was not stored)
        assert await node.get_cached(cache_key) == "value1"


@pytest.mark.unit
class TestTTLEnforcement:
    """Test suite for TTL enforcement in L1 cache."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_expired_entry_returns_none(self):
        """Test that expired entries return None on get."""
        node = MockNode()
        cache_key = "test_key"

        # Set entry with past expiry time
        past_time = time.time() - 10  # 10 seconds ago
        node._cache_data[cache_key] = ("cached_value", past_time)

        result = await node.get_cached(cache_key)

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_expired_entry_is_removed(self):
        """Test that expired entries are removed on access."""
        node = MockNode()
        cache_key = "test_key"

        # Set entry with past expiry time
        past_time = time.time() - 10
        node._cache_data[cache_key] = ("cached_value", past_time)

        # Access the entry
        await node.get_cached(cache_key)

        # Entry should be removed
        assert cache_key not in node._cache_data

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_non_expired_entry_returns_value(self):
        """Test that non-expired entries return their value."""
        node = MockNode()
        cache_key = "test_key"

        # Set entry with future expiry time
        future_time = time.time() + 3600  # 1 hour from now
        node._cache_data[cache_key] = ("cached_value", future_time)

        result = await node.get_cached(cache_key)

        assert result == "cached_value"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_no_ttl_entry_never_expires(self):
        """Test that entries without TTL never expire."""
        node = MockNode()
        cache_key = "test_key"

        # Set entry without expiry
        node._cache_data[cache_key] = ("cached_value", None)

        result = await node.get_cached(cache_key)

        assert result == "cached_value"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_default_ttl_is_applied(self):
        """Test that default TTL is applied when no explicit TTL is set."""
        node = MockNode(default_ttl_seconds=300)
        cache_key = "test_key"

        await node.set_cached(cache_key, "value")

        value, expiry = node._cache_data[cache_key]
        assert value == "value"
        assert expiry is not None
        # Expiry should be approximately 300 seconds from now
        assert 295 < (expiry - time.time()) < 305

    @pytest.mark.timeout(60)
    def test_get_cache_stats_cleans_expired_entries(self):
        """Test that get_cache_stats cleans up expired entries."""
        node = MockNode()

        # Add one valid entry and one expired entry
        future_time = time.time() + 3600
        past_time = time.time() - 10
        node._cache_data["valid_key"] = ("valid_value", future_time)
        node._cache_data["expired_key"] = ("expired_value", past_time)

        stats = node.get_cache_stats()

        # Only valid entry should remain
        assert stats["entries"] == 1
        assert "valid_key" in stats["keys"]
        assert "expired_key" not in stats["keys"]


@pytest.mark.unit
class TestL2Coordination:
    """Test suite for L1/L2 cache coordination."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_from_l2_on_l1_miss(self):
        """Test that L2 is checked when L1 misses."""
        backend = MockCacheBackend()
        backend._data["test_key"] = {"from": "l2"}
        node = MockNode(backend=backend)

        result = await node.get_cached("test_key")

        assert result == {"from": "l2"}

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_l1_populated_from_l2_hit(self):
        """Test that L1 is populated when L2 hits."""
        backend = MockCacheBackend()
        backend._data["test_key"] = {"from": "l2"}
        node = MockNode(backend=backend)

        # First get - should populate L1
        result = await node.get_cached("test_key")
        assert result == {"from": "l2"}

        # Verify L1 was populated
        value, _ = node._cache_data["test_key"]
        assert value == {"from": "l2"}

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_l1_hit_does_not_check_l2(self):
        """Test that L2 is not checked when L1 hits."""
        backend = MockCacheBackend()
        backend._data["test_key"] = {"from": "l2"}
        node = MockNode(backend=backend)

        # Set different value in L1
        node._cache_data["test_key"] = ({"from": "l1"}, None)

        result = await node.get_cached("test_key")

        # Should return L1 value
        assert result == {"from": "l1"}

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_writes_to_both_l1_and_l2(self):
        """Test that set_cached writes to both L1 and L2."""
        backend = MockCacheBackend()
        node = MockNode(backend=backend)

        await node.set_cached("test_key", {"value": "test"}, ttl_seconds=600)

        # Check L1
        value, _ = node._cache_data["test_key"]
        assert value == {"value": "test"}

        # Check L2
        assert backend._data["test_key"] == {"value": "test"}
        assert backend._ttls["test_key"] == 600

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_invalidate_removes_from_both_l1_and_l2(self):
        """Test that invalidate removes from both L1 and L2."""
        backend = MockCacheBackend()
        node = MockNode(backend=backend)

        # Set in both caches
        await node.set_cached("test_key", "value")
        assert "test_key" in node._cache_data
        assert "test_key" in backend._data

        # Invalidate
        await node.invalidate_cache("test_key")

        # Both should be empty
        assert "test_key" not in node._cache_data
        assert "test_key" not in backend._data

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_clear_clears_both_l1_and_l2(self):
        """Test that clear_cache clears both L1 and L2."""
        backend = MockCacheBackend()
        node = MockNode(backend=backend)

        # Set multiple entries
        await node.set_cached("key1", "value1")
        await node.set_cached("key2", "value2")

        # Clear
        await node.clear_cache()

        # Both should be empty
        assert len(node._cache_data) == 0
        assert len(backend._data) == 0


@pytest.mark.unit
class TestGracefulDegradation:
    """Test suite for graceful degradation when L2 fails."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_falls_back_to_l1_on_l2_error(self):
        """Test that get returns L1 value when L2 fails."""
        backend = FailingCacheBackend()
        node = MockNode(backend=backend)

        # Set value in L1
        node._cache_data["test_key"] = ("from_l1", None)

        # Get should return L1 value despite L2 error
        result = await node.get_cached("test_key")

        assert result == "from_l1"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_returns_none_when_both_l1_and_l2_miss(self):
        """Test that get returns None when both L1 and L2 miss (L2 error)."""
        backend = FailingCacheBackend()
        node = MockNode(backend=backend)

        # No L1 value, L2 will error
        result = await node.get_cached("missing_key")

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_set_succeeds_in_l1_despite_l2_error(self):
        """Test that set stores in L1 even when L2 fails."""
        backend = FailingCacheBackend()
        node = MockNode(backend=backend)

        # Set should not raise, should store in L1
        await node.set_cached("test_key", "value")

        # L1 should have the value
        value, _ = node._cache_data["test_key"]
        assert value == "value"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_invalidate_removes_l1_despite_l2_error(self):
        """Test that invalidate removes from L1 even when L2 fails."""
        backend = FailingCacheBackend()
        node = MockNode(backend=backend)

        # Set in L1
        node._cache_data["test_key"] = ("value", None)

        # Invalidate should not raise
        await node.invalidate_cache("test_key")

        # L1 should be empty
        assert "test_key" not in node._cache_data

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_clear_clears_l1_despite_l2_error(self):
        """Test that clear clears L1 even when L2 fails."""
        backend = FailingCacheBackend()
        node = MockNode(backend=backend)

        # Set in L1
        node._cache_data["key1"] = ("value1", None)
        node._cache_data["key2"] = ("value2", None)

        # Clear should not raise
        await node.clear_cache()

        # L1 should be empty
        assert len(node._cache_data) == 0


@pytest.mark.unit
class TestBackwardCompatibility:
    """Test suite for backward compatibility with existing behavior."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_works_without_backend(self):
        """Test that mixin works without L2 backend (existing behavior)."""
        node = MockNode()

        # Full workflow should work without backend
        cache_key = node.generate_cache_key({"test": "data"})
        await node.set_cached(cache_key, "result")
        result = await node.get_cached(cache_key)

        assert result == "result"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_existing_test_patterns_still_work(self):
        """Test that existing test patterns still work."""
        node = MockNode()

        # Pattern from original tests: directly manipulating _cache_data
        # Note: format changed from object to (object, expiry)
        cache_key = "test_key"
        cache_value = {"result": "success"}

        # Old pattern was: node._cache_data[cache_key] = cache_value
        # New pattern is: node._cache_data[cache_key] = (cache_value, None)
        node._cache_data[cache_key] = (cache_value, None)

        result = await node.get_cached(cache_key)

        assert result == cache_value


@pytest.mark.unit
class TestProtocolCompliance:
    """Test suite for ProtocolCacheBackend compliance."""

    @pytest.mark.timeout(60)
    def test_mock_backend_is_protocol_compliant(self):
        """Test that MockCacheBackend implements ProtocolCacheBackend."""
        backend = MockCacheBackend()

        # Check protocol compliance via isinstance
        assert isinstance(backend, ProtocolCacheBackend)

    @pytest.mark.timeout(60)
    def test_failing_backend_is_protocol_compliant(self):
        """Test that FailingCacheBackend implements ProtocolCacheBackend."""
        backend = FailingCacheBackend()

        # Check protocol compliance via isinstance
        assert isinstance(backend, ProtocolCacheBackend)


@pytest.mark.unit
class TestRedisBackendImport:
    """Test suite for Redis backend import handling."""

    @pytest.mark.timeout(60)
    def test_redis_available_flag_exists(self):
        """Test that REDIS_AVAILABLE flag is exported."""
        from omnibase_core.infrastructure.cache_backends import REDIS_AVAILABLE

        # Should be bool (True if redis installed, False otherwise)
        assert isinstance(REDIS_AVAILABLE, bool)

    @pytest.mark.timeout(60)
    def test_backend_cache_redis_exported(self):
        """Test that BackendCacheRedis is exported."""
        from omnibase_core.infrastructure.cache_backends import BackendCacheRedis

        # Class should be importable
        assert BackendCacheRedis is not None
