> **Navigation**: [Home](../INDEX.md) > Guides > Execution Corpus Guide

# Execution Corpus Guide

**Version**: 0.4.0 | **Status**: Complete

---

## Overview

An **Execution Corpus** is a curated collection of execution manifests used for systematic replay testing. It enables:

- **Regression Testing**: Verify system behavior matches baseline across versions
- **Performance Comparison**: Compare execution times and resource usage
- **Handler Coverage**: Ensure all handlers are exercised by test data
- **A/B Testing**: Compare different implementations on identical inputs

The `ModelExecutionCorpus` class provides the data model for managing these collections, supporting both inline storage (materialized mode) and external storage (reference mode).

**Key Characteristics**:
- Immutable after creation (frozen Pydantic model)
- Thread-safe for concurrent read access
- Supports 20-50+ executions for comprehensive coverage
- Built-in statistics and querying capabilities

---

## When to Use Materialized vs Reference Mode

`ModelExecutionCorpus` supports two storage modes to accommodate different use cases.

### Materialized Mode

In materialized mode, full `ModelExecutionManifest` objects are stored inline in the `executions` tuple.

**Best For**:
- Self-contained test fixtures
- Small corpora (fewer than 50 executions)
- Portable test suites that run without external dependencies
- Unit and integration tests in CI/CD pipelines

**Advantages**:
- No external dependencies required
- Fully portable across environments
- Faster access (no I/O to resolve manifests)
- Easier to version control alongside test code

**Disadvantages**:
- Higher memory usage for large corpora
- Larger file sizes when serialized
- Duplication if same manifests used across multiple corpora

**Example**:
```python
from omnibase_core.models.replay import ModelExecutionCorpus
from omnibase_core.models.manifest import ModelExecutionManifest

# Create a materialized corpus
corpus = ModelExecutionCorpus(
    name="unit-test-fixtures",
    version="1.0.0",
    source="synthetic",
    description="Unit test fixtures for text-transform handler",
)

# Add executions inline (returns new instance - model is frozen)
corpus = corpus.with_execution(manifest1)
corpus = corpus.with_execution(manifest2)

# Or add multiple at once (more efficient for bulk adds)
corpus = corpus.with_executions([manifest3, manifest4, manifest5])

# Access directly
for manifest in corpus.executions:
    print(f"{manifest.manifest_id}: {manifest.node_identity.handler_descriptor_id}")
```

### Reference Mode

In reference mode, only manifest UUIDs are stored in the `execution_ids` tuple. Full manifests must be resolved from an external storage system.

**Best For**:
- Large corpora (hundreds or thousands of executions)
- Production database integration
- Shared storage across teams
- Memory-constrained environments

**Advantages**:
- Memory efficient (only UUIDs stored)
- Smaller serialized file size
- Supports very large corpora
- Manifests can be updated without corpus changes

**Disadvantages**:
- Requires external storage system
- Slower access (I/O required to resolve)
- Not portable without storage access
- More complex setup

**Example**:
```python
from uuid import UUID
from omnibase_core.models.replay import ModelExecutionCorpus

# Create a reference-mode corpus
corpus = ModelExecutionCorpus(
    name="production-regression-suite",
    version="2.1.0",
    source="production",
    description="Q4 2024 production request sample",
    is_reference=True,
)

# Add manifest references
corpus = corpus.with_execution_ref(UUID("123e4567-e89b-12d3-a456-426614174000"))
corpus = corpus.with_execution_ref(UUID("987fcdeb-51a2-3c4d-8e9f-012345678901"))

# Or add multiple at once
corpus = corpus.with_execution_refs([uuid1, uuid2, uuid3])

# Resolve manifests from external storage when needed
for manifest_id in corpus.execution_ids:
    manifest = manifest_repository.get(manifest_id)  # Your storage system
    process(manifest)
```

### Mixed Mode

A corpus can contain both materialized executions and references, useful for migration scenarios or hybrid architectures.

```python
# Start with some materialized executions
corpus = ModelExecutionCorpus(
    name="hybrid-corpus",
    version="1.0.0",
    source="mixed",
)

# Add materialized executions
corpus = corpus.with_execution(critical_manifest)

# Also add references to additional manifests in storage
corpus = corpus.with_execution_ref(archived_manifest_id)

# Total count includes both
print(f"Total: {corpus.execution_count}")  # Includes executions + execution_ids
```

---

## Best Practices for Corpus Curation

### Recommended Corpus Size

**Optimal Range**: 20-50 executions per corpus

| Size | Use Case | Considerations |
|------|----------|----------------|
| < 20 | Quick smoke tests | May miss edge cases |
| 20-50 | Standard regression suite | Optimal balance of coverage and speed |
| 50-100 | Comprehensive coverage | Longer execution time |
| > 100 | Full production sampling | Use reference mode |

**Why 20-50 is Optimal**:
- Provides statistically meaningful coverage
- Manageable execution time for CI/CD
- Easy to review and maintain
- Sufficient variety to catch regressions

**Validation**:
```python
# Check corpus is ready for replay
corpus.validate_for_replay()  # Raises ModelOnexError if empty

# Check execution count
if corpus.execution_count < 20:
    print("Warning: Corpus may have insufficient coverage")
elif corpus.execution_count > 100:
    print("Consider splitting into multiple focused corpora")
```

### Handler Coverage

Ensure your corpus exercises all handlers in your system.

```python
# Get unique handlers in corpus
handlers = corpus.get_unique_handlers()
print(f"Handlers covered: {handlers}")

# Compare against expected handlers
expected_handlers = {"text-transform", "json-parse", "data-validate", "api-call"}
covered = set(handlers)
missing = expected_handlers - covered

if missing:
    print(f"WARNING: Missing coverage for handlers: {missing}")

# Query executions by specific handler
transform_runs = corpus.get_executions_by_handler("text-transform")
print(f"text-transform executions: {len(transform_runs)}")

# Ensure balanced distribution
stats = corpus.get_statistics()
for handler, count in stats.handler_distribution.items():
    percentage = count / stats.total_executions * 100
    print(f"  {handler}: {count} ({percentage:.1f}%)")
```

### Quality Criteria

A well-curated corpus should include both successful and failed executions with realistic distributions.

**Include Both Success and Failure Cases**:
```python
# Check success/failure distribution
stats = corpus.get_statistics()
print(f"Success rate: {stats.success_rate:.1%}")
print(f"Successful: {stats.success_count}")
print(f"Failed: {stats.failure_count}")

# Get specific categories
successful = corpus.get_successful_executions()
failed = corpus.get_failed_executions()

# Target realistic ratios based on production data
# Example: If production has 95% success rate, corpus should be similar
if stats.success_rate > 0.99:
    print("Warning: Consider adding some failure cases")
elif stats.success_rate < 0.80:
    print("Warning: Unusually high failure rate")
```

**Capture Edge Cases**:
- Empty inputs
- Maximum-size inputs
- Unicode and special characters
- Timeout scenarios
- Error conditions

**Document Capture Context**:
```python
from datetime import datetime, UTC
from omnibase_core.models.replay import ModelCorpusCaptureWindow

corpus = ModelExecutionCorpus(
    name="production-sample-2024q4",
    version="1.0.0",
    source="production",
    description="Sampled from production traffic during Q4 2024 release",
    tags=("regression", "release-2.5", "q4-2024"),
    capture_window=ModelCorpusCaptureWindow(
        start_time=datetime(2024, 10, 1, 0, 0, 0, tzinfo=UTC),
        end_time=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    ),
)
```

---

## Integration with Replay Infrastructure

### Creating a Corpus

**From Scratch**:
```python
from omnibase_core.models.replay import ModelExecutionCorpus
from omnibase_core.models.manifest import ModelExecutionManifest

# Create empty corpus
corpus = ModelExecutionCorpus(
    name="my-test-suite",
    version="1.0.0",
    source="synthetic",
    description="Test fixtures for CI",
)

# Build manifest (example - actual fields depend on your setup)
manifest = ModelExecutionManifest(
    node_identity=node_identity,
    contract_identity=contract_identity,
    input_snapshot=input_data,
    output_snapshot=output_data,
    timing=timing_info,
)

# Add to corpus
corpus = corpus.with_execution(manifest)
```

**From Production Logs**:
```python
# Sample from production execution log
production_manifests = execution_log.sample(n=50, strategy="stratified")

corpus = ModelExecutionCorpus(
    name="production-sample",
    version="1.0.0",
    source="production",
).with_executions(production_manifests)
```

### Converting Between Modes

**Materialized to Reference** (to save memory):
```python
# Extract IDs from materialized corpus
manifest_ids = [m.manifest_id for m in corpus.executions]

# Store manifests in external system
for manifest in corpus.executions:
    manifest_repository.store(manifest)

# Create reference-mode corpus
reference_corpus = ModelExecutionCorpus(
    name=corpus.name,
    version=corpus.version,
    source=corpus.source,
    description=corpus.description,
    tags=corpus.tags,
    capture_window=corpus.capture_window,
    execution_ids=tuple(manifest_ids),
    is_reference=True,
)
```

**Reference to Materialized** (to make portable):
```python
# Resolve manifests from storage
manifests = [
    manifest_repository.get(manifest_id)
    for manifest_id in corpus.execution_ids
]

# Create materialized corpus
materialized_corpus = ModelExecutionCorpus(
    name=corpus.name,
    version=corpus.version,
    source=corpus.source,
    description=corpus.description,
    tags=corpus.tags,
    capture_window=corpus.capture_window,
    executions=tuple(manifests),
    is_reference=False,
)
```

### Merging Corpora

Combine multiple corpora for comprehensive testing:
```python
# Merge two corpora
combined_executions = (*corpus_a.executions, *corpus_b.executions)
combined_refs = (*corpus_a.execution_ids, *corpus_b.execution_ids)

merged_corpus = ModelExecutionCorpus(
    name="combined-regression-suite",
    version="1.0.0",
    source="mixed",
    description=f"Merged from {corpus_a.name} and {corpus_b.name}",
    executions=combined_executions,
    execution_ids=combined_refs,
)

print(f"Merged corpus: {merged_corpus.execution_count} total executions")
```

### Running Replay Tests

Integrate corpus with replay testing framework:
```python
async def run_corpus_replay(
    corpus: ModelExecutionCorpus,
    executor: HandlerExecutor,
) -> ReplayResults:
    """Execute all corpus manifests and compare outputs."""

    # Validate corpus before replay
    corpus.validate_for_replay()

    results = []
    for manifest in corpus.executions:
        # Re-execute with same inputs
        actual_output = await executor.execute(
            handler_id=manifest.node_identity.handler_descriptor_id,
            input_data=manifest.input_snapshot,
            replay_context=manifest.replay_context,
        )

        # Compare with expected output
        expected_output = manifest.output_snapshot
        is_match = compare_outputs(actual_output, expected_output)

        results.append(ReplayResult(
            manifest_id=manifest.manifest_id,
            matched=is_match,
            expected=expected_output,
            actual=actual_output,
        ))

    return ReplayResults(results=results)
```

---

## Statistics and Analysis

### Getting Corpus Statistics

```python
stats = corpus.get_statistics()

print(f"Total executions: {stats.total_executions}")
print(f"Success count: {stats.success_count}")
print(f"Failure count: {stats.failure_count}")
print(f"Success rate: {stats.success_rate:.1%}")
print(f"Average duration: {stats.avg_duration_ms:.2f}ms")

print("\nHandler distribution:")
for handler, count in sorted(stats.handler_distribution.items()):
    print(f"  {handler}: {count}")
```

### Getting Time Range

```python
time_range = corpus.get_time_range()

if time_range:
    print(f"Earliest execution: {time_range.min_time}")
    print(f"Latest execution: {time_range.max_time}")
    print(f"Time span: {time_range.duration}")
else:
    print("Corpus is empty")
```

### Querying Executions

```python
# By handler
transforms = corpus.get_executions_by_handler("text-transform")

# By success/failure
successful = corpus.get_successful_executions()
failed = corpus.get_failed_executions()

# Get unique handlers
handlers = corpus.get_unique_handlers()
```

---

## API Reference

### ModelExecutionCorpus

| Attribute | Type | Description |
|-----------|------|-------------|
| `corpus_id` | `UUID` | Unique identifier |
| `name` | `str` | Human-readable name |
| `version` | `str` | Semantic version |
| `source` | `str` | Source environment |
| `description` | `str | None` | Optional description |
| `tags` | `tuple[str, ...]` | Categorization tags |
| `capture_window` | `ModelCorpusCaptureWindow | None` | Capture time range |
| `executions` | `tuple[ModelExecutionManifest, ...]` | Materialized manifests |
| `execution_ids` | `tuple[UUID, ...]` | Reference manifest IDs |
| `is_reference` | `bool` | Whether in reference mode |
| `created_at` | `datetime` | Creation timestamp |

| Property | Type | Description |
|----------|------|-------------|
| `is_materialized` | `bool` | True if not in reference mode |
| `is_valid_for_replay` | `bool` | True if has any executions |
| `execution_count` | `int` | Total count (materialized + refs) |

| Method | Returns | Description |
|--------|---------|-------------|
| `get_statistics()` | `ModelCorpusStatistics` | Compute corpus statistics |
| `get_time_range()` | `ModelCorpusTimeRange | None` | Get execution time range |
| `with_execution(manifest)` | `ModelExecutionCorpus` | Add single manifest |
| `with_executions(manifests)` | `ModelExecutionCorpus` | Add multiple manifests |
| `with_execution_ref(id)` | `ModelExecutionCorpus` | Add single reference |
| `with_execution_refs(ids)` | `ModelExecutionCorpus` | Add multiple references |
| `validate_for_replay()` | `None` | Validate corpus (raises on error) |
| `get_executions_by_handler(name)` | `tuple[...]` | Query by handler ID |
| `get_successful_executions()` | `tuple[...]` | Get successful runs |
| `get_failed_executions()` | `tuple[...]` | Get failed runs |
| `get_unique_handlers()` | `tuple[str, ...]` | Get unique handler IDs |

### ModelCorpusStatistics

| Attribute | Type | Description |
|-----------|------|-------------|
| `total_executions` | `int` | Total execution count |
| `success_count` | `int` | Successful executions |
| `failure_count` | `int` | Failed executions |
| `handler_distribution` | `dict[str, int]` | Count by handler |
| `success_rate` | `float` | Success fraction (0.0-1.0) |
| `avg_duration_ms` | `float | None` | Average duration |

### ModelCorpusCaptureWindow

| Attribute | Type | Description |
|-----------|------|-------------|
| `start_time` | `datetime` | Window start |
| `end_time` | `datetime` | Window end |

| Property | Type | Description |
|----------|------|-------------|
| `duration` | `timedelta` | Window length |

---

## See Also

- **Source Code**: `omnibase_core.models.replay.model_execution_corpus`
- **Manifest Model**: `omnibase_core.models.manifest.model_execution_manifest`
- **Replay Context**: `omnibase_core.models.replay.model_replay_context`
- **Related Issue**: OMN-1202

---

**Last Updated**: 2025-01-04
**Documentation Version**: 1.0.0
**Framework Version**: omnibase_core 0.4.0+
