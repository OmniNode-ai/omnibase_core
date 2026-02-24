# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for optional contract loader caching (OMN-554).

Covers:
- ContractLoaderCache: get/put/invalidate/clear, TTL expiry, disabled cache,
  hit/miss/eviction metrics, hit_ratio, evict_expired, reset_stats, mtime-based
  key invalidation.
- load_contract_cached: cache miss then hit, uses default cache, custom cache,
  disabled cache (ttl=0), propagates ModelOnexError from load_contract.
- get_default_cache: lazily created, same instance on repeated calls.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.contracts.contract_loader import (
    ContractLoaderCache,
    get_default_cache,
    load_contract_cached,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_yaml(tmp_path: Path) -> Path:
    """A minimal valid contract YAML file."""
    f = tmp_path / "basic.yaml"
    f.write_text("node_name: test_node\nnode_type: COMPUTE_GENERIC\n")
    return f


@pytest.fixture
def another_yaml(tmp_path: Path) -> Path:
    """A second distinct contract YAML file."""
    f = tmp_path / "another.yaml"
    f.write_text("node_name: other_node\nnode_type: EFFECT_GENERIC\n")
    return f


@pytest.fixture
def fresh_cache() -> ContractLoaderCache:
    """A cache instance with no TTL (entries never expire)."""
    return ContractLoaderCache(ttl_seconds=None)


# ---------------------------------------------------------------------------
# ContractLoaderCache — basic get/put
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractLoaderCacheBasic:
    """Basic get/put behaviour."""

    def test_get_on_empty_cache_returns_none(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        result = fresh_cache.get(basic_yaml)
        assert result is None

    def test_put_and_get_returns_value(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        contract: dict[str, object] = {"node_name": "test_node"}
        fresh_cache.put(basic_yaml, contract)
        retrieved = fresh_cache.get(basic_yaml)
        assert retrieved == contract

    def test_put_and_get_with_resolved_path(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        """put() and get() both resolve paths; unresolved path should also work."""
        contract: dict[str, object] = {"node_name": "test_node"}
        fresh_cache.put(basic_yaml.resolve(), contract)
        assert fresh_cache.get(basic_yaml) == contract

    def test_put_overwrites_existing_entry(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "v1"})
        fresh_cache.put(basic_yaml, {"node_name": "v2"})
        assert fresh_cache.get(basic_yaml) == {"node_name": "v2"}

    def test_two_distinct_paths_stored_independently(
        self,
        fresh_cache: ContractLoaderCache,
        basic_yaml: Path,
        another_yaml: Path,
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "a"})
        fresh_cache.put(another_yaml, {"node_name": "b"})
        assert fresh_cache.get(basic_yaml) == {"node_name": "a"}
        assert fresh_cache.get(another_yaml) == {"node_name": "b"}


# ---------------------------------------------------------------------------
# ContractLoaderCache — mtime-based key invalidation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractLoaderCacheMtimeInvalidation:
    """Cache key includes mtime; file modification produces a miss."""

    def test_modified_file_causes_cache_miss(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        contract_v1: dict[str, object] = {"node_name": "v1"}
        fresh_cache.put(basic_yaml, contract_v1)

        # Modify the file to change its mtime
        # Use a time in the future to ensure mtime changes
        new_mtime = basic_yaml.stat().st_mtime + 1.0
        import os

        os.utime(basic_yaml, (new_mtime, new_mtime))

        # The original cache entry used the old mtime key — should be a miss now
        result = fresh_cache.get(basic_yaml)
        assert result is None

    def test_unmodified_file_still_hits(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        contract: dict[str, object] = {"node_name": "test"}
        fresh_cache.put(basic_yaml, contract)
        # No modification — should still hit
        assert fresh_cache.get(basic_yaml) == contract


# ---------------------------------------------------------------------------
# ContractLoaderCache — TTL expiry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractLoaderCacheTTL:
    """TTL-based entry expiry."""

    def test_entry_expires_after_ttl(
        self, basic_yaml: Path
    ) -> None:
        cache = ContractLoaderCache(ttl_seconds=1)
        cache.put(basic_yaml, {"node_name": "ttl_test"})
        assert cache.get(basic_yaml) is not None  # alive

        # Advance time past expiry using monotonic mock
        future_time = time.monotonic() + 2.0
        with patch("omnibase_core.contracts.contract_loader.time") as mock_time:
            mock_time.monotonic.return_value = future_time
            result = cache.get(basic_yaml)

        assert result is None

    def test_entry_alive_before_ttl(
        self, basic_yaml: Path
    ) -> None:
        cache = ContractLoaderCache(ttl_seconds=3600)
        cache.put(basic_yaml, {"node_name": "alive"})
        assert cache.get(basic_yaml) == {"node_name": "alive"}

    def test_no_ttl_entry_never_expires(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "immortal"})
        # Simulate a very large future time
        far_future = time.monotonic() + 1_000_000_000.0
        with patch("omnibase_core.contracts.contract_loader.time") as mock_time:
            mock_time.monotonic.return_value = far_future
            result = fresh_cache.get(basic_yaml)
        assert result == {"node_name": "immortal"}


# ---------------------------------------------------------------------------
# ContractLoaderCache — disabled (ttl=0)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractLoaderCacheDisabled:
    """Cache with zero/negative TTL behaves as a no-op."""

    @pytest.mark.parametrize("ttl", [0, -1, -100])
    def test_disabled_put_is_noop(self, basic_yaml: Path, ttl: int) -> None:
        cache = ContractLoaderCache(ttl_seconds=ttl)
        cache.put(basic_yaml, {"node_name": "noop"})
        assert cache.get(basic_yaml) is None

    @pytest.mark.parametrize("ttl", [0, -1])
    def test_disabled_stats_show_not_enabled(self, ttl: int) -> None:
        cache = ContractLoaderCache(ttl_seconds=ttl)
        stats = cache.get_stats()
        assert stats["enabled"] is False


# ---------------------------------------------------------------------------
# ContractLoaderCache — invalidate / clear
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractLoaderCacheInvalidation:
    """Explicit invalidation and clear."""

    def test_invalidate_removes_entry(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "x"})
        removed = fresh_cache.invalidate(basic_yaml)
        assert removed is True
        assert fresh_cache.get(basic_yaml) is None

    def test_invalidate_nonexistent_returns_false(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        assert fresh_cache.invalidate(basic_yaml) is False

    def test_clear_removes_all_entries(
        self,
        fresh_cache: ContractLoaderCache,
        basic_yaml: Path,
        another_yaml: Path,
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "a"})
        fresh_cache.put(another_yaml, {"node_name": "b"})
        count = fresh_cache.clear()
        assert count == 2
        assert fresh_cache.get(basic_yaml) is None
        assert fresh_cache.get(another_yaml) is None

    def test_clear_empty_cache_returns_zero(
        self, fresh_cache: ContractLoaderCache
    ) -> None:
        assert fresh_cache.clear() == 0


# ---------------------------------------------------------------------------
# ContractLoaderCache — metrics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractLoaderCacheMetrics:
    """Hit/miss/eviction counters and hit_ratio."""

    def test_initial_stats_all_zero(self, fresh_cache: ContractLoaderCache) -> None:
        stats = fresh_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0
        assert stats["entries"] == 0
        assert stats["hit_ratio"] == 0.0
        assert stats["enabled"] is True

    def test_miss_increments_miss_counter(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.get(basic_yaml)
        assert fresh_cache.get_stats()["misses"] == 1

    def test_hit_increments_hit_counter(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "x"})
        fresh_cache.get(basic_yaml)
        assert fresh_cache.get_stats()["hits"] == 1

    def test_invalidate_increments_eviction_counter(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "x"})
        fresh_cache.invalidate(basic_yaml)
        assert fresh_cache.get_stats()["evictions"] == 1

    def test_clear_increments_eviction_counter(
        self,
        fresh_cache: ContractLoaderCache,
        basic_yaml: Path,
        another_yaml: Path,
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "a"})
        fresh_cache.put(another_yaml, {"node_name": "b"})
        fresh_cache.clear()
        assert fresh_cache.get_stats()["evictions"] == 2

    def test_hit_ratio_calculated_correctly(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "x"})
        fresh_cache.get(basic_yaml)  # hit
        fresh_cache.get(basic_yaml)  # hit
        # Miss on a different path (not put)
        fresh_cache.get(Path("/nonexistent/path.yaml"))  # miss
        stats = fresh_cache.get_stats()
        # 2 hits, 1 miss -> ratio = 2/3
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert abs(stats["hit_ratio"] - 2 / 3) < 1e-9

    def test_reset_stats_clears_counters(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "x"})
        fresh_cache.get(basic_yaml)  # hit
        fresh_cache.get(Path("/nonexistent.yaml"))  # miss
        fresh_cache.reset_stats()
        stats = fresh_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0

    def test_reset_stats_does_not_clear_entries(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "x"})
        fresh_cache.reset_stats()
        # Entry should still be accessible
        assert fresh_cache.get(basic_yaml) == {"node_name": "x"}

    def test_expired_entry_increments_miss_and_eviction(
        self, basic_yaml: Path
    ) -> None:
        cache = ContractLoaderCache(ttl_seconds=1)
        cache.put(basic_yaml, {"node_name": "x"})

        future_time = time.monotonic() + 2.0
        with patch("omnibase_core.contracts.contract_loader.time") as mock_time:
            mock_time.monotonic.return_value = future_time
            cache.get(basic_yaml)  # should miss and evict

        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["evictions"] == 1


# ---------------------------------------------------------------------------
# ContractLoaderCache — evict_expired
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractLoaderCacheEvictExpired:
    """evict_expired() bulk removes stale entries."""

    def test_evict_expired_removes_stale_entries(self, basic_yaml: Path) -> None:
        cache = ContractLoaderCache(ttl_seconds=1)
        cache.put(basic_yaml, {"node_name": "x"})

        future_time = time.monotonic() + 2.0
        with patch("omnibase_core.contracts.contract_loader.time") as mock_time:
            mock_time.monotonic.return_value = future_time
            evicted = cache.evict_expired()

        assert evicted == 1
        assert cache.get_stats()["entries"] == 0

    def test_evict_expired_does_not_remove_live_entries(
        self, basic_yaml: Path
    ) -> None:
        cache = ContractLoaderCache(ttl_seconds=3600)
        cache.put(basic_yaml, {"node_name": "x"})
        evicted = cache.evict_expired()
        assert evicted == 0
        assert cache.get_stats()["entries"] == 1

    def test_evict_expired_with_no_ttl_removes_nothing(
        self, fresh_cache: ContractLoaderCache, basic_yaml: Path
    ) -> None:
        fresh_cache.put(basic_yaml, {"node_name": "x"})
        evicted = fresh_cache.evict_expired()
        assert evicted == 0


# ---------------------------------------------------------------------------
# load_contract_cached — integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadContractCached:
    """load_contract_cached() function behaviour."""

    def test_first_call_is_miss_and_loads_file(
        self, basic_yaml: Path
    ) -> None:
        cache = ContractLoaderCache()
        contract = load_contract_cached(basic_yaml, cache=cache)
        assert contract["node_name"] == "test_node"
        assert cache.get_stats()["misses"] == 1
        assert cache.get_stats()["hits"] == 0

    def test_second_call_is_hit(self, basic_yaml: Path) -> None:
        cache = ContractLoaderCache()
        load_contract_cached(basic_yaml, cache=cache)  # miss
        load_contract_cached(basic_yaml, cache=cache)  # hit
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_cached_result_matches_direct_load(self, basic_yaml: Path) -> None:
        from omnibase_core.contracts.contract_loader import load_contract

        cache = ContractLoaderCache()
        cached = load_contract_cached(basic_yaml, cache=cache)
        direct = load_contract(basic_yaml)
        assert cached == direct

    def test_uses_default_cache_when_none_passed(
        self, basic_yaml: Path
    ) -> None:
        """Calling without explicit cache uses get_default_cache()."""
        default = get_default_cache()
        default.clear()
        default.reset_stats()

        load_contract_cached(basic_yaml)  # should populate default cache

        stats = default.get_stats()
        assert stats["misses"] == 1
        # Clean up
        default.invalidate(basic_yaml)

    def test_disabled_cache_still_returns_correct_contract(
        self, basic_yaml: Path
    ) -> None:
        cache = ContractLoaderCache(ttl_seconds=0)
        contract = load_contract_cached(basic_yaml, cache=cache)
        assert contract["node_name"] == "test_node"

    def test_load_contract_cached_propagates_error(self, tmp_path: Path) -> None:
        """Errors from load_contract are propagated unchanged."""
        missing = tmp_path / "nonexistent.yaml"
        cache = ContractLoaderCache()
        with pytest.raises(ModelOnexError):
            load_contract_cached(missing, cache=cache)

    def test_error_does_not_populate_cache(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.yaml"
        cache = ContractLoaderCache()
        try:
            load_contract_cached(missing, cache=cache)
        except ModelOnexError:
            pass
        # Should not be cached
        assert cache.get(missing) is None
        assert cache.get_stats()["entries"] == 0


# ---------------------------------------------------------------------------
# get_default_cache
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetDefaultCache:
    """get_default_cache() lazy singleton behaviour."""

    def test_returns_contract_loader_cache_instance(self) -> None:
        result = get_default_cache()
        assert isinstance(result, ContractLoaderCache)

    def test_same_instance_on_repeated_calls(self) -> None:
        first = get_default_cache()
        second = get_default_cache()
        assert first is second

    def test_default_cache_has_no_ttl(self) -> None:
        """Default cache entries should never expire automatically."""
        cache = get_default_cache()
        # Accessing private attribute for assertion only in tests
        assert cache._ttl_seconds is None  # noqa: SLF001
