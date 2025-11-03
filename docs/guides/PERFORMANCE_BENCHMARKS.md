# ONEX Performance Testing Suite

Comprehensive performance benchmarks for ONEX contract models and validation operations ensuring production-ready performance characteristics.

## Overview

This suite addresses PR feedback requirements for performance benchmarks at scale, validating that ONEX validation operations maintain acceptable performance even with complex dependency graphs and high-volume scenarios.

## Performance Targets

### Contract Validation Performance
- **Single dependency validation**: <1ms per dependency
- **Circular dependency detection**: <0.1s for 100 dependencies
- **Regex pattern matching**: <50μs per operation
- **Security validation**: <0.1ms per check
- **Large dependency graphs**: >200 deps/sec throughput

### Memory Efficiency
- **Memory per dependency**: <3000 bytes (complex objects with UUIDs, conditions, versions)
- **Large graphs (5000 deps)**: <15MB total memory
- **Memory growth**: Linear with dependency count

### Concurrent Performance
- **Multi-threaded validation**: >1000 ops/sec throughput
- **Thread safety**: No race conditions or deadlocks
- **Error isolation**: Individual thread failures don't affect others

## Test Categories

### 1. ModelWorkflowDependency Performance
**File**: `tests/performance/core/contracts/test_model_workflow_dependency_performance.py`

**Tests**:
- `test_single_dependency_validation_performance` - Basic validation speed
- `test_circular_dependency_detection_performance` - Circular dependency prevention
- `test_regex_pattern_performance` - Module path validation regex
- `test_large_dependency_graph_performance` - 1000+ dependency handling
- `test_timeout_validation_performance` - Timeout constraint validation
- `test_memory_usage_large_graph` - Memory efficiency at scale
- `test_concurrent_validation_simulation` - Multi-threaded performance

### 2. ModelDependency Performance
**File**: `tests/performance/core/contracts/test_model_dependency_performance.py`

**Tests**:
- `test_regex_compilation_performance` - Pre-compiled regex patterns
- `test_security_validation_performance` - Security check efficiency
- `test_dependency_creation_performance` - Object creation speed
- `test_onex_pattern_validation_performance` - ONEX naming patterns
- `test_large_dependency_set_performance` - Large dataset handling
- `test_memory_efficiency` - Memory usage optimization
- `test_stress_validation_performance` - High-load stress testing

## Running Performance Tests

### Full Performance Suite
```bash
# Run all performance tests
poetry run python -m pytest tests/performance/ -v

# Run with performance output
poetry run python -m pytest tests/performance/ -v -s
```python

### Specific Test Categories
```bash
# Run only ModelWorkflowDependency tests
poetry run python -m pytest tests/performance/core/contracts/test_model_workflow_dependency_performance.py -v -s

# Run only ModelDependency tests
poetry run python -m pytest tests/performance/core/contracts/test_model_dependency_performance.py -v -s
```python

### Individual Performance Tests
```bash
# Test single dependency validation speed
poetry run python -m pytest tests/performance/core/contracts/test_model_workflow_dependency_performance.py::TestModelWorkflowDependencyPerformance::test_single_dependency_validation_performance -v -s

# Test regex performance
poetry run python -m pytest tests/performance/core/contracts/test_model_dependency_performance.py::TestModelDependencyPerformance::test_regex_compilation_performance -v -s
```python

### Slow Tests (Memory and Stress Tests)
```bash
# Run slow tests (may take several seconds each)
poetry run python -m pytest tests/performance/ -m slow -v -s

# Skip slow tests for faster runs
poetry run python -m pytest tests/performance/ -m "not slow" -v -s
```yaml

## Performance Metrics Output

Performance tests output detailed metrics:

```text
✅ Single dependency validation: 0.016ms average
✅ Non-circular validation (100 deps): 0.76ms
✅ Circular detection (50 attempts): 2.38ms
✅ Module regex performance: 0.39μs per match
✅ Snake case conversion: 0.93μs per conversion
✅ Security validation: 0.045ms per check
✅ Large graph creation: 1.23s for 5000 dependencies
✅ Creation throughput: 4065 dependencies/sec
✅ Memory per dependency: 1247.3 bytes
✅ Concurrent validation: 2847.3 deps/sec throughput
```python

## Test Configuration

### Pytest Configuration
Performance tests use custom configuration in `pytest-performance.ini`:

```ini
[tool:pytest]
testpaths = tests/performance
timeout = 30  # Max 30 seconds per test
markers =
    slow: marks tests as slow (may take several seconds)
    memory: marks tests that measure memory usage
    concurrent: marks tests that use threading/multiprocessing
    benchmark: marks performance benchmark tests
```python

### Test Markers
- `@pytest.mark.slow` - Tests taking >2 seconds
- `@pytest.mark.memory` - Memory usage measurement tests
- `@pytest.mark.concurrent` - Multi-threading tests
- `@pytest.mark.benchmark` - Performance benchmark tests

## Performance Validation

### Validation Targets Met
All performance tests validate against specific targets:

1. **Latency Requirements**:
   - Single operations: <1ms
   - Batch operations: <2s for typical loads
   - Regex operations: <50μs

2. **Throughput Requirements**:
   - Dependency creation: >200/sec
   - Validation operations: >1000/sec
   - Concurrent processing: >2000/sec

3. **Memory Requirements**:
   - Per-dependency overhead: <2KB
   - Large graph memory: Linear growth
   - No memory leaks in repeated operations

4. **Scalability Requirements**:
   - Linear performance degradation with size
   - Concurrent safety with no deadlocks
   - Graceful handling of resource constraints

## Integration with PR Feedback

This performance testing suite directly addresses PR #19 feedback:

1. **"Consider adding performance benchmarks for validation operations at scale"**
   - ✅ Comprehensive benchmarks for 1000+ dependencies
   - ✅ Memory usage tracking at scale
   - ✅ Concurrent validation testing

2. **"Add performance benchmarks for the validation routines"**
   - ✅ Individual validation routine benchmarks
   - ✅ Regex pattern performance testing
   - ✅ Security validation efficiency testing

3. **"Test the regex patterns performance optimization"**
   - ✅ Pre-compiled regex pattern benchmarks
   - ✅ Module path validation performance
   - ✅ Camel-to-snake conversion efficiency

## Continuous Integration

### Performance Regression Detection
Performance tests can be integrated into CI to detect regressions:

```bash
# Run performance tests in CI
poetry run python -m pytest tests/performance/ --tb=short --disable-warnings

# Performance regression detection (future enhancement)
poetry run python -m pytest tests/performance/ --benchmark-json=performance-results.json
```yaml

### Performance Monitoring
- Tests output standardized metrics for monitoring
- Results can be tracked over time to detect performance regressions
- Memory usage patterns are validated to prevent memory leaks

## Architecture Compliance

### ONEX Standards Compliance
All performance tests validate ONEX architectural principles:

- **ZERO TOLERANCE**: No Any types or string fallbacks in performance-critical paths
- **Strong Typing**: All validation maintains type safety without performance penalty
- **Circular Dependency Prevention**: Fast detection prevents infinite loops
- **Security-First**: Security validation doesn't compromise performance

### Production Readiness
Performance benchmarks ensure production-ready characteristics:

- **High Throughput**: Handle production-scale dependency graphs
- **Low Latency**: Response times suitable for real-time applications
- **Memory Efficiency**: Sustainable memory usage patterns
- **Concurrent Safety**: Thread-safe operations under load

---

**Performance Suite Version**: 1.0
**Created**: 2025-01-15
**PR Reference**: #19 Contract Dependency Model Refactor
**ONEX Compliance**: Verified
