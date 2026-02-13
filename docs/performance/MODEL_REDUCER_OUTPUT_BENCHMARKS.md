> **Navigation**: [Home](../INDEX.md) > Performance > ModelReducerOutput Benchmarks

# ModelReducerOutput Performance Benchmarks

**Location**: `tests/performance/test_model_reducer_output_benchmarks.py`

**Status**: ✅ All 36 benchmarks passing (as of 2025-12-16)

**Related**: PR #205 review feedback

---

## Overview

Comprehensive performance benchmarks for `ModelReducerOutput[T]` operations across varying data sizes, from small (10 items) to extra-large (10,000 items) payloads.

## Running Benchmarks

```bash
# Run all performance benchmarks
poetry run pytest -m performance tests/performance/test_model_reducer_output_benchmarks.py -v

# Run specific benchmark
poetry run pytest tests/performance/test_model_reducer_output_benchmarks.py::TestModelReducerOutputPerformance::test_model_creation_performance -v

# Run with detailed output
poetry run pytest -m performance tests/performance/test_model_reducer_output_benchmarks.py -v -s
```

---

## Benchmark Categories

### 1. Model Creation Performance

**Tests**: `test_model_creation_performance[small|medium|large|xlarge]`

**What it measures**: Time to instantiate `ModelReducerOutput[dict]` with complex nested data structures.

**Performance Baselines**:
| Data Size | Max Time | Notes |
|-----------|----------|-------|
| 10 items | < 1ms | Small payloads |
| 100 items | < 2ms | Medium payloads |
| 1,000 items | < 10ms | Large payloads |
| 10,000 items | < 50ms | Extra-large payloads |

**Why it matters**: Model creation happens on every reducer operation. Fast creation ensures low overhead for FSM state transitions.

---

### 2. Serialization Performance

**Tests**:
- `test_serialization_performance[*]` - Dict serialization (`model_dump()`)
- `test_json_serialization_performance[*]` - JSON serialization (`model_dump_json()`)

**What it measures**: Time to convert `ModelReducerOutput` to dict or JSON string.

**Performance Baselines**:
| Data Size | Max Time (dict) | Max Time (JSON) | Notes |
|-----------|-----------------|-----------------|-------|
| 10 items | < 5ms | < 5ms | Event bus messaging |
| 100 items | < 10ms | < 10ms | Typical payload size |
| 1,000 items | < 50ms | < 50ms | Large aggregations |
| 10,000 items | < 200ms | < 200ms | Bulk operations |

**Why it matters**: Serialization is critical for event bus operations (Kafka/Redpanda). JSON serialization is used for inter-service communication.

---

### 3. Deserialization Performance

**Tests**:
- `test_deserialization_performance[*]` - Dict deserialization (`model_validate()`)
- `test_json_deserialization_performance[*]` - JSON deserialization (`model_validate_json()`)

**What it measures**: Time to reconstruct `ModelReducerOutput` from dict or JSON string.

**Performance Baselines**:
| Data Size | Max Time (dict) | Max Time (JSON) | Notes |
|-----------|-----------------|-----------------|-------|
| 10 items | < 5ms | < 5ms | Event consumption |
| 100 items | < 10ms | < 10ms | Typical consumption |
| 1,000 items | < 50ms | < 50ms | Large message handling |
| 10,000 items | < 200ms | < 200ms | Bulk message processing |

**Why it matters**: Deserialization happens when consuming events from the event bus. Fast deserialization reduces message processing latency.

---

### 4. Validation Performance

**Tests**:
- `test_validation_performance_field_level` - Per-field validation overhead
- `test_validation_performance_sentinel_values` - Sentinel value validation (-1 pattern)

**What it measures**: Time spent in Pydantic field validators.

**Performance Baselines**:
| Validation Type | Max Time | Notes |
|-----------------|----------|-------|
| Per-field validation | < 0.1ms | processing_time_ms, items_processed |
| Sentinel vs normal | < 0.2ms additional | -1.0 and -1 sentinel handling |

**Why it matters**: Field validation runs on every model creation. Low overhead ensures validation doesn't become a bottleneck.

**Key Insight**: Sentinel value validation (-1 pattern) adds negligible overhead compared to normal value validation.

---

### 5. Intent Handling Performance

**Test**: `test_intent_handling_performance[no_intents|10|100|1000]`

**What it measures**: Performance impact of Intent emission (pure FSM pattern).

**Performance Baselines**:
| Intent Count | Max Time | Notes |
|--------------|----------|-------|
| 0 intents | < 1ms | No side effects |
| 10 intents | < 2ms | Typical use case |
| 100 intents | < 10ms | Complex reductions |
| 1,000 intents | < 50ms | Bulk intent emission |

**Why it matters**: Intents are core to the ModelIntent pattern (FSM → Effect). Performance scales linearly with intent count.

---

### 6. Metadata Handling Performance

**Test**: `test_metadata_handling_performance[no_tags|10|100]`

**What it measures**: Performance of `ModelReducerMetadata` with varying tag counts.

**Performance Baselines**:
| Tag Count | Max Time | Notes |
|-----------|----------|-------|
| 0 tags | < 1ms | Minimal metadata |
| 10 tags | < 2ms | Typical tagging |
| 100 tags | < 10ms | Heavy tagging |

**Why it matters**: Metadata is used for correlation, tracing, and grouping. Performance should scale gracefully with tag count.

---

### 7. Memory Usage

**Test**: `test_memory_usage[small|medium|large|xlarge]`

**What it measures**: RSS (Resident Set Size) memory increase when creating 10 model instances.

**Performance Baselines**:
| Data Size | Max Memory (10 instances) | Notes |
|-----------|---------------------------|-------|
| 10 items | < 1MB | Small payloads |
| 100 items | < 5MB | Medium payloads |
| 1,000 items | < 20MB | Large payloads |
| 10,000 items | < 100MB | Extra-large payloads |

**Why it matters**: Memory efficiency is critical for long-running services processing thousands of events per second.

**Note**: Memory measurements are approximate and may vary based on Python runtime, GC behavior, and system state.

---

### 8. Round-Trip Performance

**Test**: `test_round_trip_performance`

**What it measures**: End-to-end event bus workflow:
1. Create ModelReducerOutput
2. Serialize to JSON
3. Deserialize from JSON
4. Access all fields

**Performance Baseline**: < 20ms for 100 items

**Why it matters**: This simulates the complete event bus lifecycle (publish → consume → process). Fast round-trips enable high-throughput event processing.

---

### 9. Immutability Overhead

**Test**: `test_frozen_immutability_overhead`

**What it measures**: Field access overhead from `frozen=True` (immutability).

**Performance Baseline**: < 0.01ms for 11 field accesses

**Why it matters**: Immutability (`frozen=True`) provides thread safety. This test ensures immutability adds negligible overhead to field access.

---

### 10. Pydantic vs Dict Comparison

**Test**: `test_comparison_dict_vs_pydantic`

**What it measures**: Performance trade-off between raw dicts and Pydantic models.

**Performance Baseline**: Pydantic creation < 1ms (absolute time)

**Key Insights**:
- Pydantic is expected to be 10-100x slower than raw dicts due to validation and type checking
- **Absolute time matters more than relative percentage**: < 1ms is acceptable overhead
- Type safety and validation are worth the performance trade-off
- For high-performance scenarios, consider caching or pre-validation

**Example Output**:
```
Pydantic vs Dict Performance Comparison (100 items):
  Pydantic model: 0.026ms
  Raw dict: 0.001ms
  Overhead: 0.025ms (2580.8%)
```

**Interpretation**: While Pydantic is 25x slower, the absolute overhead (0.025ms) is negligible for typical use cases.

---

## Performance Optimization Guidelines

### When to Optimize

Optimize when:
1. **Benchmarks exceed thresholds** - Any test fails with exceeded time limits
2. **Production profiling shows bottlenecks** - APM data shows reducer latency
3. **Scaling issues emerge** - Performance degrades with larger payloads

### Optimization Strategies

#### 1. Reduce Data Size
- Paginate large result sets instead of returning all data
- Use projection to exclude unnecessary fields
- Compress data before serialization (for event bus)

#### 2. Cache Validated Models
```python
# Cache validated models to avoid repeated validation
@lru_cache(maxsize=1000)
def get_validated_output(data_hash: str) -> ModelReducerOutput:
    return ModelReducerOutput[dict].model_validate(data)
```

#### 3. Batch Operations
```python
# Batch multiple operations instead of individual creates
outputs = [
    ModelReducerOutput[dict](...)
    for result in batch_results
]
```

#### 4. Use streaming_mode Appropriately
```python
# For large datasets, use WINDOWED or CONTINUOUS mode
output = ModelReducerOutput[dict](
    result=windowed_data,
    streaming_mode=EnumStreamingMode.WINDOWED,
    batches_processed=10,
    ...
)
```

#### 5. Minimize Intent Count
- Batch intents where possible
- Use single intent with batched payload instead of multiple intents

#### 6. Optimize Metadata Tags
- Keep tag counts < 10 for typical operations
- Use correlation IDs instead of descriptive tags for performance-critical paths

---

## CI/CD Integration

### Pre-commit Hook
Performance benchmarks are NOT run in pre-commit (too slow).

### CI Pipeline
Performance benchmarks run in CI with `@pytest.mark.performance`:

```yaml
# .github/workflows/test.yml
- name: Run performance benchmarks
  run: poetry run pytest -m performance --tb=short
```

### Regression Detection
If benchmarks start failing:
1. Check if payload size expectations changed
2. Profile specific operations with `pytest --durations=10`
3. Compare against historical CI runs
4. Investigate Pydantic version changes (validation overhead)

---

## Interpreting Results

### Good Performance
- All benchmarks pass within thresholds
- Linear scaling with data size (2x data ≈ 2x time)
- Memory usage proportional to data size

### Performance Degradation Indicators
- Non-linear scaling (10x data = 50x time)
- Memory leaks (memory doesn't decrease after GC)
- Validation overhead > 1ms per field

### When to Investigate
1. **Single test fails**: Likely a threshold issue, review if threshold is realistic
2. **Multiple tests fail**: Likely a performance regression, investigate code changes
3. **Intermittent failures**: System load or GC interference, run locally to confirm

---

## Related Documentation

- [REDUCER Node Tutorial](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md)
- [Thread Safety Guidelines](../guides/THREADING.md)
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)

---

## Benchmark Maintenance

### Adding New Benchmarks
1. Follow existing pattern with `time_operation()` helper
2. Use `@pytest.mark.parametrize` for data size variations
3. Document baseline in docstring
4. Add to this document's benchmark categories

### Updating Thresholds
When updating performance thresholds:
1. Document reason for change (hardware upgrade, Pydantic version, etc.)
2. Update docstring in test
3. Update this document
4. Add entry to changelog

### Historical Tracking
Track performance trends using CI benchmark runs:
```bash
# Extract timing data from CI logs
grep "passed in" .github/workflows/test.yml | tail -20
```

---

**Last Updated**: 2025-12-16
**Test File**: `tests/performance/test_model_reducer_output_benchmarks.py`
**Total Benchmarks**: 36
**Status**: ✅ All passing
