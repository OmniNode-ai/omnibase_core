# Cache Tuning for Production Deployment

**Version:** 1.0.0
**Last Updated:** 2025-10-17
**Status:** Production Ready

---

## Overview

This guide provides best practices for configuring `ModelComputeCacheConfig` to optimize NodeCompute performance in production environments. Proper cache tuning can significantly reduce computational overhead and improve response times.

---

## Memory Implications

### Cache Size Guidelines

Cache memory usage follows this approximate formula:
```text
Total Memory (MB) = (max_size × avg_entry_size_kb) / 1024

**Default Entry Size:** ~1KB per cached computation (varies by computation complexity)

### Workload-Based Recommendations

| Workload Type | Computations/sec | Recommended `max_size` | Estimated Memory | Use Case |
|---------------|------------------|------------------------|------------------|----------|
| **Small** | < 100 | 128 | ~128KB | Development, testing, low-traffic services |
| **Medium** | 100-1000 | 512 | ~512KB | Standard production services |
| **Large** | 1000-5000 | 2048 | ~2MB | High-traffic APIs, data processing pipelines |
| **Very Large** | > 5000 | 4096-8192 | ~4-8MB | Enterprise-scale, real-time analytics |

**Memory Overhead:** Add 20% for cache management structures and metadata.

### Example Configurations

```python
from omnibase_core.models.configuration.model_compute_cache_config import ModelComputeCacheConfig
from omnibase_core.models.container.model_onex_container import create_model_onex_container

# Small workload (development/testing)
small_config = ModelComputeCacheConfig(
    max_size=128,
    ttl_seconds=1800,  # 30 minutes
    eviction_policy="lru",
    enable_stats=True
)

# Medium workload (standard production)
medium_config = ModelComputeCacheConfig(
    max_size=512,
    ttl_seconds=3600,  # 1 hour
    eviction_policy="lru",
    enable_stats=True
)

# Large workload (high-traffic)
large_config = ModelComputeCacheConfig(
    max_size=2048,
    ttl_seconds=7200,  # 2 hours
    eviction_policy="lfu",  # Frequency-based for hot data
    enable_stats=True
)

# Create container with cache config
container = await create_model_onex_container(
    enable_cache=True,
    compute_cache_config=medium_config
)

---

## Eviction Policies

### LRU (Least Recently Used) - Default

**Best For:**
- Time-locality patterns (recent computations likely to repeat)
- Uniform access patterns
- General-purpose caching

**Characteristics:**
- Evicts items not accessed recently
- Good balance between simplicity and effectiveness
- Low overhead (~O(1) access time)

**When to Use:**
- Default choice for most applications
- Unknown or varying access patterns
- Development and testing environments

```python
config = ModelComputeCacheConfig(
    max_size=512,
    eviction_policy="lru"
)

### LFU (Least Frequently Used)

**Best For:**
- Frequency-locality patterns (some computations much more common)
- Hot data workloads (80/20 rule applies)
- Long-running services with stable access patterns

**Characteristics:**
- Evicts items accessed least frequently
- Retains popular computations longer
- Slightly higher overhead than LRU

**When to Use:**
- API endpoints with hot paths
- Report generation with common templates
- Data processing with repeated patterns

```python
config = ModelComputeCacheConfig(
    max_size=1024,
    eviction_policy="lfu"
)

### FIFO (First In, First Out)

**Best For:**
- Streaming data patterns
- Temporal sequences
- Simple cache requirements with minimal overhead

**Characteristics:**
- Evicts oldest entries first
- Lowest overhead (~O(1) operations)
- No access tracking required

**When to Use:**
- Time-series data processing
- Sequential workflows
- Memory-constrained environments

```python
config = ModelComputeCacheConfig(
    max_size=256,
    eviction_policy="fifo"
)

---

## TTL Configuration

### TTL Guidelines

| Computation Type | Recommended TTL | Rationale |
|------------------|-----------------|-----------|
| **Fast computations** (< 10ms) | 300-900s (5-15 min) | Short TTL, quick to recompute |
| **Medium computations** (10-100ms) | 1800-3600s (30-60 min) | Balance between freshness and performance |
| **Expensive computations** (> 100ms) | 3600-7200s (1-2 hours) | Long TTL to amortize cost |
| **Static/immutable data** | None (no expiration) | Data never changes |

### TTL Best Practices

1. **Match TTL to Data Staleness Requirements:**
   ```python
   # Financial data (requires freshness)
   config = ModelComputeCacheConfig(ttl_seconds=300)  # 5 minutes

   # Analytics (can tolerate staleness)
   config = ModelComputeCacheConfig(ttl_seconds=7200)  # 2 hours
   ```

2. **Disable TTL for Immutable Computations:**
   ```python
   # Mathematical constants, hash computations
   config = ModelComputeCacheConfig(ttl_seconds=None)
   ```

3. **Use Short TTL During Deployment:**
   ```python
   # During rolling deployments to flush stale cache quickly
   config = ModelComputeCacheConfig(ttl_seconds=60)  # 1 minute
   ```

---

## Monitoring and Statistics

### Enabling Statistics

Statistics tracking is enabled by default but can be disabled for ultra-low latency requirements:

```python
# Production monitoring (default)
config = ModelComputeCacheConfig(enable_stats=True)

# Ultra-low latency (disable stats)
config = ModelComputeCacheConfig(enable_stats=False)

### Key Metrics to Monitor

```python
from omnibase_core.nodes.node_compute import NodeCompute

# Get cache statistics
node = NodeCompute(container)
stats = node.computation_cache.get_stats()

# Monitor these metrics:
print(f"Hit Rate: {stats['hit_rate']}%")  # Target: > 70%
print(f"Evictions: {stats['evictions']}")  # High evictions = undersized cache
print(f"Expirations: {stats['expirations']}")  # High = TTL too short
print(f"Total Requests: {stats['total_requests']}")

### Performance Targets

| Metric | Good | Warning | Action Required |
|--------|------|---------|-----------------|
| **Hit Rate** | > 70% | 50-70% | < 50% (increase max_size or TTL) |
| **Eviction Rate** | < 10% | 10-25% | > 25% (increase max_size) |
| **Memory Usage** | < 80% of allocated | 80-90% | > 90% (decrease max_size) |

### Alerting Recommendations

```python
# Example monitoring check
def check_cache_health(node: NodeCompute) -> dict[str, bool]:
    stats = node.computation_cache.get_stats()

    return {
        "hit_rate_ok": stats.get("hit_rate", 0) >= 70,
        "eviction_rate_ok": (
            stats.get("evictions", 0) / max(stats.get("total_requests", 1), 1)
        ) <= 0.1,
        "memory_ok": stats["total_entries"] < (stats["max_size"] * 0.8)
    }

---

## Production Deployment Checklist

- [ ] **Cache Size Configured** - Based on workload analysis and memory budget
- [ ] **TTL Configured** - Matches data staleness requirements
- [ ] **Eviction Policy Selected** - Appropriate for access patterns
- [ ] **Statistics Enabled** - For production monitoring (unless ultra-low latency required)
- [ ] **Monitoring Alerts Set** - Hit rate, eviction rate, memory usage
- [ ] **Load Testing Completed** - Cache behavior validated under production load
- [ ] **Thread Safety Reviewed** - See [docs/THREADING.md](./THREADING.md) for multi-threaded deployments

---

## Advanced Tuning

### Dynamic Configuration

For adaptive systems, cache configuration can be adjusted at runtime:

```python
# Analyze current metrics
stats = node.computation_cache.get_stats()

# Adjust configuration based on hit rate
if stats.get("hit_rate", 0) < 50:
    # Increase cache size
    new_config = ModelComputeCacheConfig(
        max_size=node.computation_cache.max_size * 2,
        ttl_seconds=node.computation_cache.ttl_seconds * 1.5
    )

    # Recreate container with new config
    container = await create_model_onex_container(
        compute_cache_config=new_config
    )

### A/B Testing Cache Configurations

```python
# Test different configurations
configs = [
    ModelComputeCacheConfig(max_size=256, eviction_policy="lru"),
    ModelComputeCacheConfig(max_size=512, eviction_policy="lfu"),
    ModelComputeCacheConfig(max_size=1024, eviction_policy="lru"),
]

# Run performance tests
for config in configs:
    container = await create_model_onex_container(
        compute_cache_config=config
    )
    node = NodeCompute(container)

    # Benchmark and compare metrics
    # ... (implementation specific)

### Multi-Tier Caching

For advanced scenarios, combine NodeCompute cache with external caching:

```python
# L1: NodeCompute in-memory cache (fast, small)
compute_config = ModelComputeCacheConfig(
    max_size=256,
    ttl_seconds=300,
    eviction_policy="lru"
)

# L2: External Redis cache (larger, distributed)
# ... (implementation specific to deployment)

---

## Troubleshooting

### Problem: Low Hit Rate (< 50%)

**Possible Causes:**
- Cache size too small for workload
- TTL too short causing premature expiration
- Highly variable access patterns (cache thrashing)

**Solutions:**
1. Increase `max_size` by 2-4x
2. Increase `ttl_seconds` by 50-100%
3. Switch to `lfu` eviction policy
4. Analyze access patterns for optimization opportunities

### Problem: High Memory Usage

**Possible Causes:**
- `max_size` configured too large
- Large computation results
- Memory leak in custom computations

**Solutions:**
1. Reduce `max_size` to fit memory budget
2. Implement result compression for large values
3. Profile computation functions for memory leaks

### Problem: Frequent Evictions

**Possible Causes:**
- `max_size` too small for working set
- Access pattern doesn't match eviction policy

**Solutions:**
1. Increase `max_size` to reduce eviction pressure
2. Switch eviction policy (try `lfu` for hot data)
3. Reduce TTL to allow natural expiration before eviction

---

## Reference

### Configuration Model

See [`model_compute_cache_config.py`](../../src/omnibase_core/models/configuration/model_compute_cache_config.py) for complete API documentation.

### Thread Safety

See [THREADING.md](./THREADING.md) for multi-threaded deployment guidelines.

### Related Documentation

- [NodeCompute Architecture](../../src/omnibase_core/nodes/node_compute.py)
- [ModelComputeCache Implementation](../../src/omnibase_core/models/infrastructure/model_compute_cache.py)
- [Container Configuration](../../src/omnibase_core/models/container/model_onex_container.py)
