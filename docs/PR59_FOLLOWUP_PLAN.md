# PR #59 Follow-Up Plan

**Status**: Planning
**Target PR**: #60
**Created**: 2025-10-17

---

## Overview

This document outlines the plan to address all CodeRabbit review comments from PR #59. Tasks are organized by priority with specific implementation details.

---

## 1. Create GitHub Issues for ONEX Compliance (HIGH PRIORITY)

**Why**: Track architectural debt and prevent it from being forgotten.

**Issues to Create**:

### Issue 1: Naming Convention Violations
- **Title**: "Fix Enum* and Service* prefix violations per ONEX naming standards"
- **Labels**: `technical-debt`, `onex-compliance`, `naming`
- **Description**:
  - Several enums and services don't follow ONEX naming conventions
  - Need audit of all `enum_*.py` and service files
  - Update validation scripts to catch these
- **Affected Files**: Run naming validation to identify all violations

### Issue 2: Directory Structure - services → node_services
- **Title**: "Refactor services directory to node_services per ONEX architecture"
- **Labels**: `technical-debt`, `onex-compliance`, `refactoring`
- **Description**:
  - Current: `src/omnibase_core/models/nodes/services/`
  - Target: `src/omnibase_core/models/nodes/node_services/`
  - Update all imports and exports

### Issue 3: Silent Exception Handling
- **Title**: "Eliminate silent exception handling patterns"
- **Labels**: `technical-debt`, `onex-compliance`, `error-handling`
- **Description**:
  - Audit for bare `except:` or `except Exception:` without logging
  - Replace with explicit exception types and proper error propagation
  - Ensure all exceptions logged at appropriate level

### Issue 4: Single Class Per File Violations
- **Title**: "Split files with multiple classes per ONEX standards"
- **Labels**: `technical-debt`, `onex-compliance`, `architecture`
- **Description**:
  - Identify files with multiple public classes
  - Split into separate files with clear naming
  - Update imports

### Issue 5: Standard Exceptions vs ModelOnexError
- **Title**: "Replace standard exceptions with ModelOnexError throughout codebase"
- **Labels**: `technical-debt`, `onex-compliance`, `error-handling`
- **Description**:
  - Audit for `ValueError`, `TypeError`, `RuntimeError` usage
  - Replace with appropriate `ModelOnexError` subclasses
  - Ensure proper error context and chaining

**Implementation**:
```bash
# Create all issues with gh CLI
gh issue create --title "..." --body "..." --label "technical-debt,onex-compliance"
```

---

## 2. Add Cache Size Configuration (HIGH PRIORITY)

**Why**: Production deployments need tunable cache behavior for different workloads.

**Current State**: Hardcoded cache in `NodeCompute`

**Target State**:
- Container-managed cache configuration
- Tunable parameters: max_size, eviction_policy, ttl
- Per-node type configuration support

**Implementation**:

### Step 1: Create Cache Configuration Model
**File**: `src/omnibase_core/models/configuration/model_compute_cache_config.py`

```python
from pydantic import Field
from omnibase_core.models.base import ModelBase

class ModelComputeCacheConfig(ModelBase):
    """Configuration for computation caching in NodeCompute.

    Thread Safety: Cache operations must be synchronized by implementation.
    Memory Usage: ~1KB per cached entry (varies by computation size).
    """
    max_size: int = Field(
        default=128,
        ge=1,
        le=10000,
        description="Maximum number of cached computations. Default conservative for production."
    )
    ttl_seconds: int | None = Field(
        default=3600,  # 1 hour
        ge=1,
        description="Time-to-live for cached entries. None = no expiration."
    )
    eviction_policy: str = Field(
        default="lru",
        pattern="^(lru|lfu|fifo)$",
        description="Cache eviction policy: lru (least recently used), lfu (least frequently used), fifo"
    )
    enable_stats: bool = Field(
        default=True,
        description="Enable cache hit/miss statistics for monitoring"
    )
```

### Step 2: Add to Container Configuration
**File**: `src/omnibase_core/models/container/model_onex_container.py`

```python
# Add to ModelONEXContainer
compute_cache_config: ModelComputeCacheConfig = Field(
    default_factory=ModelComputeCacheConfig,
    description="Cache configuration for NodeCompute instances"
)
```

### Step 3: Wire Cache Config into NodeCompute
**File**: `src/omnibase_core/nodes/node_compute.py`

```python
def __init__(self, ...):
    # Get cache config from container
    cache_config = self.container.compute_cache_config

    # Initialize cache with config
    self._cache = ComputationCache(
        max_size=cache_config.max_size,
        ttl_seconds=cache_config.ttl_seconds,
        eviction_policy=cache_config.eviction_policy,
        enable_stats=cache_config.enable_stats
    )
```

### Step 4: Update ComputationCache Implementation
**File**: `src/omnibase_core/models/infrastructure/model_compute_cache.py`

- Add parameters to constructor
- Implement TTL expiration
- Add cache statistics tracking
- Document thread safety requirements

### Step 5: Add Production Documentation
**File**: `docs/PRODUCTION_CACHE_TUNING.md`

```markdown
# Cache Tuning for Production

## Memory Implications
- Small workload (< 100 computations/sec): max_size=128, ~128KB
- Medium workload (100-1000/sec): max_size=512, ~512KB
- Large workload (> 1000/sec): max_size=2048, ~2MB

## Eviction Policies
- **lru**: Best for time-locality (recent computations likely to repeat)
- **lfu**: Best for frequency-locality (some computations much more common)
- **fifo**: Simplest, lowest overhead

## Monitoring
Enable `enable_stats=True` and monitor:
- Cache hit ratio (target > 70%)
- Eviction rate
- Memory usage
```

**Tests**:
- Unit test for `ModelComputeCacheConfig` validation
- Integration test for container → NodeCompute wiring
- Performance test showing cache impact

---

## 3. Document Thread Safety (HIGH PRIORITY)

**Why**: Prevent race conditions in production multi-threaded environments.

**Scope**:
- Circuit breakers in `NodeEffect`
- Parallel processing in `NodeCompute`
- Caching layer thread safety

**Implementation**:

### Step 1: Create THREADING.md
**File**: `docs/THREADING.md`

```markdown
# Thread Safety in Omnibase Core

## Overview
This document explains the concurrency model and thread safety guarantees for ONEX nodes.

## NodeCompute Thread Safety

### Parallel Processing
`NodeCompute` uses `ThreadPoolExecutor` for parallel batch processing:
- **Thread-Safe**: Input/output models (immutable after creation)
- **NOT Thread-Safe**: Internal cache state (requires synchronization)
- **Recommendation**: Use separate NodeCompute instances per thread OR implement cache locking

### Computation Cache
Current implementation: **NOT thread-safe by default**
- LRU operations are not atomic
- Concurrent gets/sets can corrupt cache state
- **Mitigation**: Add `threading.Lock` for production use

Example:
```python
from threading import Lock

class ThreadSafeComputationCache:
    def __init__(self):
        self._cache = {}
        self._lock = Lock()

    def get(self, key):
        with self._lock:
            return self._cache.get(key)
```

## NodeEffect Thread Safety

### Circuit Breakers
Circuit breaker state is **NOT thread-safe**:
- `failure_count` increments are not atomic
- `last_failure_time` updates can race
- Multiple threads may incorrectly trip/reset breaker

**Mitigation Options**:

1. **Single-threaded effects**: Design effects to run sequentially
2. **Per-thread breakers**: Use thread-local circuit breakers
3. **Atomic counters**: Use `threading.Lock` or `multiprocessing.Value`

Example:
```python
from threading import Lock

class ThreadSafeCircuitBreaker:
    def __init__(self):
        self._failure_count = 0
        self._lock = Lock()

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
```

## Transaction Thread Safety

`ModelEffectTransaction` is **NOT thread-safe**:
- Rollback operations assume single-threaded execution
- Multiple threads should NOT share transaction objects

**Recommendation**: Create one transaction per operation, never share across threads.

## General Guidelines

1. **Immutable by Default**: All Pydantic models are thread-safe after creation
2. **Mutable State**: Any mutable state (caches, counters) needs explicit synchronization
3. **Container Sharing**: `ModelONEXContainer` can be shared across threads (read-only after init)
4. **Node Instances**: Do NOT share node instances across threads without careful analysis

## Production Checklist

- [ ] Cache access synchronized with locks
- [ ] Circuit breakers use atomic counters
- [ ] Transactions created per-operation
- [ ] Metrics collection thread-safe
- [ ] Event bus publishing synchronized
```

### Step 2: Add Thread Safety to Docstrings

**NodeCompute** (`src/omnibase_core/nodes/node_compute.py`):
```python
class NodeCompute:
    """Pure computation node with caching and parallel processing.

    Thread Safety:
        - Instance NOT thread-safe due to mutable cache state
        - Use separate instances per thread OR implement cache locking
        - Parallel processing via ThreadPoolExecutor is internally managed
        - See docs/THREADING.md for production guidelines
    """
```

**NodeEffect** (`src/omnibase_core/nodes/node_effect.py`):
```python
class NodeEffect:
    """Side-effect node with transactions and circuit breakers.

    Thread Safety:
        - Circuit breaker state NOT thread-safe (failure counts, timers)
        - Transactions NOT shareable across threads
        - Create separate instances per thread for concurrent effects
        - See docs/THREADING.md for production guidelines
    """
```

**ComputationCache**:
```python
class ComputationCache:
    """LRU cache for computation results.

    Thread Safety:
        - NOT thread-safe by default
        - Production use requires external synchronization (e.g., threading.Lock)
        - See docs/THREADING.md for thread-safe implementation example
    """
```

### Step 3: Add Warning to README
**File**: `README.md`

Add section:
```markdown
## Concurrency and Thread Safety

⚠️ **Important**: Most ONEX node components are NOT thread-safe by default.

For production multi-threaded environments, see [docs/THREADING.md](docs/THREADING.md) for:
- Thread safety guarantees
- Synchronization patterns
- Production checklist
```

**Tests**:
- Add thread safety test that deliberately races cache operations
- Document expected failures without locking
- Add example of correct locking pattern

---

## 4. Return Rollback Failures (MEDIUM PRIORITY)

**Why**: Silent rollback failures mask data inconsistency and are debugging nightmares.

**Current State**: Likely swallows exceptions

**Target State**: Explicit failure handling with logging

**Implementation**:

### Step 1: Update Transaction Model
**File**: `src/omnibase_core/nodes/model_effect_transaction.py`

```python
from typing import List
from omnibase_core.models.base import ModelBase
from omnibase_core.exceptions import ModelOnexError

class ModelEffectTransaction(ModelBase):
    """Transaction context for effect operations with rollback tracking.

    Rollback Semantics:
        - Rollback failures are logged and returned, never silently swallowed
        - Partial rollback failures are captured with details of which operations failed
        - Original exception is preserved via exception chaining
    """

    operations: List[str] = []
    committed: bool = False
    rollback_failures: List[str] = []  # Track which rollbacks failed

    def rollback(self) -> tuple[bool, List[ModelOnexError]]:
        """Rollback all operations in reverse order.

        Returns:
            Tuple of (all_succeeded, failure_list)
            - all_succeeded: True if all rollbacks succeeded
            - failure_list: List of errors for failed rollbacks (empty if all succeeded)

        Logging:
            - Each rollback failure logged at ERROR level with full context
            - Successful rollbacks logged at DEBUG level
        """
        failures = []

        for operation in reversed(self.operations):
            try:
                self._rollback_operation(operation)
                logger.debug(f"Rolled back operation: {operation}")
            except Exception as e:
                error = ModelOnexError(
                    message=f"Rollback failed for operation: {operation}",
                    error_code="ROLLBACK_FAILURE",
                    cause=e,
                    context={"operation": operation, "transaction_id": self.id}
                )
                failures.append(error)
                logger.error(
                    f"Rollback failed for operation {operation}: {error}",
                    exc_info=True
                )

        self.rollback_failures = [f.message for f in failures]
        return (len(failures) == 0, failures)
```

### Step 2: Update NodeEffect to Handle Rollback Failures
**File**: `src/omnibase_core/nodes/node_effect.py`

```python
def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
    transaction = None
    try:
        if self.enable_transactions:
            transaction = self._create_transaction()

        # ... execute effect ...

        if transaction:
            transaction.commit()

    except Exception as e:
        if transaction and not transaction.committed:
            success, rollback_errors = transaction.rollback()

            if not success:
                # Rollback failed - this is CRITICAL
                logger.error(
                    f"Transaction rollback failed with {len(rollback_errors)} errors",
                    extra={
                        "transaction_id": transaction.id,
                        "rollback_errors": [str(e) for e in rollback_errors]
                    }
                )

                # Optionally: invoke callback for critical failures
                if self.on_rollback_failure:
                    self.on_rollback_failure(transaction, rollback_errors)

                # Chain the rollback errors to the original exception
                raise ModelOnexError(
                    message="Effect failed AND rollback failed (data may be inconsistent)",
                    error_code="EFFECT_ROLLBACK_FAILURE",
                    cause=e,
                    context={
                        "original_error": str(e),
                        "rollback_errors": [str(err) for err in rollback_errors],
                        "transaction_id": transaction.id
                    }
                ) from e

        raise
```

### Step 3: Add Rollback Failure Callback Support
```python
class NodeEffect:
    def __init__(
        self,
        ...,
        on_rollback_failure: Callable[[ModelEffectTransaction, List[ModelOnexError]], None] | None = None
    ):
        """
        Args:
            on_rollback_failure: Optional callback invoked on rollback failures.
                                 Useful for alerting, metrics, or custom recovery logic.
        """
        self.on_rollback_failure = on_rollback_failure
```

### Step 4: Add Metrics
```python
# In _update_specialized_metrics
if transaction and transaction.rollback_failures:
    self.metrics.increment("transaction.rollback_failures_total")
    self.metrics.histogram(
        "transaction.failed_operation_count",
        len(transaction.rollback_failures)
    )
```

**Tests**:
- Unit test: rollback failures are captured and returned
- Unit test: rollback failures are logged at ERROR level
- Integration test: callback is invoked on rollback failure
- Integration test: metrics track rollback failures

---

## 5. TestFixtureBase and Pydantic Bypass Docs (MEDIUM PRIORITY)

**Why**: Prevent Pydantic bypass pattern from leaking into production code.

**Scope**: Test fixtures only (never used in production)

**Implementation**:

### Step 1: Create TestFixtureBase
**File**: `tests/fixtures/fixture_base.py`

```python
"""Base class for test fixtures using Pydantic bypass patterns.

⚠️ WARNING: This module uses Pydantic validation bypass for test performance.
NEVER import or use these patterns in production code.
"""

from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class TestFixtureBase:
    """Base class for test fixtures with safe Pydantic bypass patterns.

    Why Bypass Validation in Tests:
        - Validation is expensive (10-100x slower than direct construction)
        - Tests create thousands of model instances
        - Test data is known-valid by construction
        - Production code always validates at boundaries

    Safety Guarantees:
        - Only used in tests/ directory (enforced by pre-commit hook)
        - Models are still type-checked by mypy
        - Integration tests validate real data flows

    Usage:
        class MyFixture(TestFixtureBase):
            @staticmethod
            def create_effect_input(**overrides):
                return TestFixtureBase.construct(
                    ModelEffectInput,
                    operation="test_op",
                    parameters={},
                    **overrides
                )
    """

    @staticmethod
    def construct(model_class: Type[T], **field_values) -> T:
        """Construct model bypassing Pydantic validation.

        ⚠️ ONLY USE IN TESTS

        Args:
            model_class: The Pydantic model class to construct
            **field_values: Field values to set (no validation)

        Returns:
            Model instance with validation bypassed

        Example:
            # Fast test fixture creation
            input_data = TestFixtureBase.construct(
                ModelEffectInput,
                operation="test",
                parameters={"key": "value"}
            )
        """
        return model_class.model_construct(**field_values)

    @staticmethod
    def construct_many(model_class: Type[T], count: int, **base_fields) -> list[T]:
        """Construct many model instances efficiently.

        Args:
            model_class: The Pydantic model class
            count: Number of instances to create
            **base_fields: Base field values for all instances

        Returns:
            List of model instances
        """
        return [
            model_class.model_construct(**base_fields, id=i)
            for i in range(count)
        ]
```

### Step 2: Migrate Existing Fixtures
**Files**: All files in `tests/fixtures/`

Example migration:
```python
# Before
def effect_input_fixture(**overrides):
    return ModelEffectInput.model_construct(
        operation="test",
        **overrides
    )

# After
class EffectFixtures(TestFixtureBase):
    @staticmethod
    def effect_input(**overrides):
        return TestFixtureBase.construct(
            ModelEffectInput,
            operation="test",
            parameters={},
            **overrides
        )
```

### Step 3: Add Pre-Commit Hook
**File**: `.pre-commit-config.yaml`

```yaml
- repo: local
  hooks:
    - id: no-pydantic-bypass-in-prod
      name: Prevent Pydantic bypass in production code
      entry: python scripts/validation/validate_no_pydantic_bypass.py
      language: system
      files: '^src/.*\.py$'  # Only check production code
      exclude: '^tests/.*$'   # Exclude tests
```

**File**: `scripts/validation/validate_no_pydantic_bypass.py`

```python
#!/usr/bin/env python3
"""Validate that Pydantic bypass patterns are not used in production code."""

import sys
import re
from pathlib import Path

BYPASS_PATTERNS = [
    r'\.model_construct\(',
    r'\.__dict__\[',  # Direct dict manipulation
    r'object\.__setattr__\(',  # Bypass frozen models
]

def check_file(filepath: Path) -> list[str]:
    """Check file for Pydantic bypass patterns."""
    violations = []
    content = filepath.read_text()

    for line_num, line in enumerate(content.splitlines(), 1):
        for pattern in BYPASS_PATTERNS:
            if re.search(pattern, line):
                violations.append(
                    f"{filepath}:{line_num}: Found Pydantic bypass pattern: {pattern}"
                )

    return violations

def main():
    files = [Path(f) for f in sys.argv[1:]]
    all_violations = []

    for filepath in files:
        violations = check_file(filepath)
        all_violations.extend(violations)

    if all_violations:
        print("❌ Pydantic bypass patterns found in production code:")
        for violation in all_violations:
            print(f"  {violation}")
        print("\n⚠️  These patterns should only be used in tests/fixtures/")
        sys.exit(1)

    print("✅ No Pydantic bypass patterns in production code")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Step 4: Add Documentation
**File**: `tests/fixtures/README.md`

```markdown
# Test Fixtures

## Pydantic Bypass Pattern

Test fixtures use `model_construct()` to bypass Pydantic validation for performance.

### Why?
- Validation is 10-100x slower than direct construction
- Tests create thousands of model instances
- Test data is known-valid by construction

### Safety
- ✅ Only used in `tests/` directory
- ✅ Enforced by pre-commit hook
- ✅ Models still type-checked by mypy
- ✅ Integration tests validate real flows

### Usage
```python
from tests.fixtures.fixture_base import TestFixtureBase

class MyFixtures(TestFixtureBase):
    @staticmethod
    def create_input(**overrides):
        return TestFixtureBase.construct(
            ModelEffectInput,
            operation="test",
            **overrides
        )
```

### ⚠️ NEVER Use in Production
This pattern bypasses Pydantic's validation, type coercion, and defaults.
Production code MUST use normal model construction.
```

**Tests**:
- Test that pre-commit hook catches bypass patterns in `src/`
- Test that pre-commit hook allows bypass patterns in `tests/`
- Performance test showing fixture speedup

---

## Implementation Order

1. **GitHub Issues** (15 min) - Do first to track everything else
2. **Cache Configuration** (2-3 hours) - Highest production impact
3. **Thread Safety Docs** (1-2 hours) - Critical for production deployment
4. **Rollback Failures** (2-3 hours) - Important for data consistency
5. **TestFixtureBase** (1 hour) - Good hygiene, lowest risk

**Total Estimated Time**: 6-9 hours

---

## Testing Strategy

### Unit Tests
- Cache config validation and wiring
- Rollback failure capture and logging
- TestFixtureBase construct methods

### Integration Tests
- Cache behavior with different configs
- Thread safety scenarios (deliberate races)
- Rollback failure callbacks

### Documentation Tests
- All code examples in docs are valid
- Pre-commit hooks work correctly

---

## Success Criteria

- [ ] All 5 GitHub issues created and linked
- [ ] Cache configuration wired into container and documented
- [ ] THREADING.md created with docstring updates
- [ ] Rollback failures returned and logged
- [ ] TestFixtureBase created with pre-commit enforcement
- [ ] All tests passing
- [ ] Pre-commit hooks passing
- [ ] Documentation reviewed

---

## Notes

- All changes should be atomic and testable
- Each task can be developed in parallel if needed
- Consider breaking into multiple PRs if scope is too large
- Get feedback on THREADING.md before implementing patterns
