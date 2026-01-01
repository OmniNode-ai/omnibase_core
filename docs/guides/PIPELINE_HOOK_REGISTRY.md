# Pipeline Runner and Hook Registry Guide

## Overview

The Pipeline Runner and Hook Registry infrastructure provides a declarative, extensible system for executing hooks in canonical phase order. This system enables:

- **Phase-based execution**: Hooks execute in a predefined order (preflight, before, execute, after, emit, finalize)
- **Dependency management**: Hooks can declare dependencies on other hooks within the same phase
- **Priority ordering**: When dependencies are equal, hooks are sorted by priority
- **Type validation**: Hooks can be validated against contract types
- **Error handling**: Different phases have different error handling behaviors (fail-fast vs continue-on-error)
- **Thread safety**: Freeze-after-init pattern for concurrent reads

## Quick Start

### Basic Pipeline Execution

```python
from omnibase_core.pipeline import (
    BuilderExecutionPlan,
    ModelPipelineHook,
    ModelPipelineContext,
    RegistryHook,
    RunnerPipeline,
)

# Step 1: Create hooks
def logging_hook(ctx: ModelPipelineContext) -> None:
    """Log pipeline start."""
    ctx.data["started_at"] = "2025-01-01T00:00:00Z"
    print("Pipeline started")

def validation_hook(ctx: ModelPipelineContext) -> None:
    """Validate input data."""
    ctx.data["validated"] = True
    print("Validation passed")

def main_processing(ctx: ModelPipelineContext) -> None:
    """Main processing logic."""
    ctx.data["result"] = {"status": "success"}
    print("Processing complete")

def cleanup_hook(ctx: ModelPipelineContext) -> None:
    """Cleanup resources."""
    print("Cleanup completed")

# Step 2: Register hooks
registry = RegistryHook()

registry.register(ModelPipelineHook(
    hook_id="logging",
    phase="preflight",
    callable_ref="app.hooks.logging",
))

registry.register(ModelPipelineHook(
    hook_id="validation",
    phase="before",
    callable_ref="app.hooks.validation",
))

registry.register(ModelPipelineHook(
    hook_id="processing",
    phase="execute",
    callable_ref="app.hooks.processing",
))

registry.register(ModelPipelineHook(
    hook_id="cleanup",
    phase="finalize",
    callable_ref="app.hooks.cleanup",
))

# Step 3: Freeze registry (required before building plan)
registry.freeze()

# Step 4: Build execution plan
builder = BuilderExecutionPlan(registry=registry)
plan, warnings = builder.build()

# Step 5: Create callable registry
callables = {
    "app.hooks.logging": logging_hook,
    "app.hooks.validation": validation_hook,
    "app.hooks.processing": main_processing,
    "app.hooks.cleanup": cleanup_hook,
}

# Step 6: Execute pipeline
async def run_pipeline():
    runner = RunnerPipeline(plan=plan, callable_registry=callables)
    result = await runner.run()

    if result.success:
        print("Pipeline completed successfully!")
        print(f"Context data: {result.context.data}")
    else:
        print(f"Pipeline failed with {len(result.errors)} errors")
        for error in result.errors:
            print(f"  - {error.phase}/{error.hook_id}: {error.error_message}")

# Run it
import asyncio
asyncio.run(run_pipeline())
```

## Architecture

### Phase Execution Order

The pipeline executes hooks in a canonical phase order:

```text
preflight -> before -> execute -> after -> emit -> finalize
```

| Phase | Purpose | Error Behavior |
|-------|---------|----------------|
| `preflight` | Pre-execution checks (permissions, resources) | Fail-fast |
| `before` | Setup and preparation | Fail-fast |
| `execute` | Main processing logic | Fail-fast |
| `after` | Post-execution processing | Continue |
| `emit` | Event emission and notifications | Continue |
| `finalize` | Cleanup (ALWAYS runs, even on error) | Continue |

**Fail-fast phases**: Abort on first error, re-raise exception.

**Continue phases**: Capture errors, continue executing remaining hooks.

**Finalize guarantee**: The `finalize` phase ALWAYS runs, even if earlier phases raised exceptions.

### Fail-Fast Semantics Deep Dive

The `fail_fast` setting is **explicitly set based on phase semantics** when building execution plans. This is not relying on defaults - the `BuilderExecutionPlan` explicitly assigns `fail_fast` based on the phase:

```python
# From builder_execution_plan.py - explicit phase-based assignment
FAIL_FAST_PHASES: frozenset[PipelinePhase] = frozenset(
    {"preflight", "before", "execute"}
)

# In build() method:
phases[phase] = ModelPhaseExecutionPlan(
    phase=phase,
    hooks=sorted_hooks,
    fail_fast=phase in FAIL_FAST_PHASES,  # Explicit, not default
)
```

**Rationale for each phase**:

| Phase | `fail_fast` | Rationale |
|-------|-------------|-----------|
| `preflight` | `True` | Validation must pass before proceeding. If permissions or resource checks fail, there's no point continuing. |
| `before` | `True` | Setup must succeed before main execution. A failed setup (e.g., database connection) invalidates subsequent operations. |
| `execute` | `True` | Core logic - first failure should halt further execution to prevent cascading errors or invalid state. |
| `after` | `False` | Cleanup should attempt all hooks even if some fail. One failed cleanup should not prevent others. |
| `emit` | `False` | Event emission should try all hooks (best effort). Failed notification should not block other notifications. |
| `finalize` | `False` | Resource cleanup must try all hooks regardless of prior errors. Critical for preventing resource leaks. |

**When might you want different behavior?**

The phase-based defaults cover most use cases, but you can customize `fail_fast` by building custom `ModelPhaseExecutionPlan` objects:

```python
# Custom fail-fast behavior (advanced use case)
from omnibase_core.pipeline import (
    ModelExecutionPlan,
    ModelPhaseExecutionPlan,
    ModelPipelineHook,
)

# Build custom phase plan with overridden fail_fast
custom_after_phase = ModelPhaseExecutionPlan(
    phase="after",
    hooks=[hook1, hook2],
    fail_fast=True,  # Override: fail-fast even in "after" phase
)

# Use in custom execution plan
custom_plan = ModelExecutionPlan(
    phases={"after": custom_after_phase}
)
```

**Note**: Overriding `fail_fast` is rarely needed. The default phase semantics are carefully chosen to match common pipeline patterns.

### Component Overview

```text
                    +-----------------+
                    |  RegistryHook   |
                    |  (registration) |
                    +--------+--------+
                             |
                             | freeze()
                             v
              +-----------------------------+
              |    BuilderExecutionPlan     |
              |  - Type validation          |
              |  - Dependency validation    |
              |  - Topological sort         |
              +--------------+--------------+
                             |
                             | build()
                             v
                    +------------------+
                    | ModelExecutionPlan |
                    |  (frozen, shareable) |
                    +---------+----------+
                              |
                              v
                    +------------------+
                    |  RunnerPipeline  |
                    |  (execution)     |
                    +------------------+
```

## API Reference

### ModelPipelineHook

Represents a single hook in the pipeline.

```python
from omnibase_core.pipeline import ModelPipelineHook, PipelinePhase
from omnibase_core.enums import EnumHandlerTypeCategory

hook = ModelPipelineHook(
    # Required fields
    hook_id="my-hook",           # Unique identifier (alphanumeric, -, _)
    phase="execute",             # Pipeline phase
    callable_ref="module.func",  # Reference to callable in registry

    # Optional fields
    priority=100,                        # Execution priority (lower = earlier, default: 100)
    dependencies=["other-hook"],         # Hook IDs that must run first (same phase)
    handler_type_category=EnumHandlerTypeCategory.COMPUTE,  # Optional type category
    timeout_seconds=30.0,                # Optional execution timeout
)
```

**Valid phases**: `"preflight"`, `"before"`, `"execute"`, `"after"`, `"emit"`, `"finalize"`

### RegistryHook

Manages hook registration with freeze-after-init thread safety.

```python
from omnibase_core.pipeline import RegistryHook, ModelPipelineHook

# Create registry
registry = RegistryHook()

# Register hooks (only before freeze)
registry.register(hook1)
registry.register(hook2)

# Freeze for concurrent access
registry.freeze()

# Read operations (safe after freeze)
hooks = registry.get_hooks_by_phase("execute")
all_hooks = registry.get_all_hooks()
hook = registry.get_hook_by_id("my-hook")
is_frozen = registry.is_frozen
```

**Methods**:

| Method | Description | Before Freeze | After Freeze |
|--------|-------------|---------------|--------------|
| `register(hook)` | Register a hook | Yes | Raises `HookRegistryFrozenError` |
| `freeze()` | Lock registry (idempotent) | Yes | Yes (no-op) |
| `get_hooks_by_phase(phase)` | Get hooks for phase | Yes | Yes (returns copy) |
| `get_all_hooks()` | Get all hooks | Yes | Yes (returns copy) |
| `get_hook_by_id(id)` | Get hook by ID | Yes | Yes |
| `is_frozen` | Check frozen state | Yes | Yes |

### BuilderExecutionPlan

Builds execution plans from a frozen registry with validation.

```python
from omnibase_core.pipeline import BuilderExecutionPlan, RegistryHook
from omnibase_core.enums import EnumHandlerTypeCategory

# Create builder (enforce_hook_typing=True is the default)
builder = BuilderExecutionPlan(
    registry=registry,                          # Must be frozen
    contract_category=EnumHandlerTypeCategory.COMPUTE,  # Optional type validation
    # enforce_hook_typing=True is the default - raises error on type mismatch
)

# Build plan (validates and sorts hooks)
plan, warnings = builder.build()

# Check warnings (type mismatches when enforce_hook_typing=False is explicitly set)
for warning in warnings:
    print(f"Warning: {warning.code} - {warning.message}")
```

**Validation performed**:

1. **Hook type validation** (if `contract_category` set):
   - Generic hooks (`handler_type_category=None`) pass for any contract
   - Typed hooks must match contract type
   - By default (`enforce_hook_typing=True`), type mismatches raise `HookTypeMismatchError`
   - Set `enforce_hook_typing=False` for warning-only mode (useful for gradual migration)

2. **Dependency validation**:
   - All dependencies must exist within the same phase
   - Raises `UnknownDependencyError` for missing dependencies

3. **Cycle detection**:
   - Dependencies must not form cycles
   - Raises `DependencyCycleError` if cycle detected

4. **Topological sorting**:
   - Hooks sorted by dependencies first
   - Priority as tie-breaker (lower value = earlier)

### ModelExecutionPlan

Frozen execution plan ready for the pipeline runner.

```python
from omnibase_core.pipeline import ModelExecutionPlan, PipelinePhase

# Created by BuilderExecutionPlan.build()
plan, _ = builder.build()

# Access phase hooks
execute_hooks = plan.get_phase_hooks("execute")

# Check fail-fast behavior
is_fail_fast = plan.is_phase_fail_fast("execute")  # True
is_fail_fast = plan.is_phase_fail_fast("after")    # False

# Get metadata
total = plan.total_hooks
category = plan.contract_category

# Create empty plan
empty = ModelExecutionPlan.empty()
```

### RunnerPipeline

Executes the pipeline using an execution plan.

```python
from omnibase_core.pipeline import RunnerPipeline, ModelPipelineContext, ModelPipelineResult

# Create runner
runner = RunnerPipeline(
    plan=plan,                    # From BuilderExecutionPlan.build()
    callable_registry=callables,  # Dict mapping callable_ref to actual callables
)

# Execute (async)
result: ModelPipelineResult = await runner.run()

# Check result
if result.success:
    print("Success!")
    print(f"Final context: {result.context.data}")
else:
    print(f"Failed with {len(result.errors)} errors")
    for error in result.errors:
        print(f"  Phase: {error.phase}")
        print(f"  Hook: {error.hook_id}")
        print(f"  Error: {error.error_type}: {error.error_message}")
```

### ModelPipelineContext

Shared mutable context passed to all hooks.

```python
from omnibase_core.pipeline import ModelPipelineContext

def my_hook(ctx: ModelPipelineContext) -> None:
    # Read data from previous hooks
    previous_result = ctx.data.get("result")

    # Store data for subsequent hooks
    ctx.data["my_output"] = {"status": "done"}
```

### PipelineResult

Result of pipeline execution.

```python
from omnibase_core.pipeline import PipelineResult

result: PipelineResult = await runner.run()

result.success    # bool - True if no errors
result.errors     # list[ModelHookError] - Captured errors from continue phases
result.context    # ModelPipelineContext | None - Final context state
```

### HookCallable Type

Type alias for hook functions.

```python
from omnibase_core.pipeline import HookCallable, ModelPipelineContext

# Sync hook
def sync_hook(ctx: ModelPipelineContext) -> None:
    ctx.data["sync"] = True

# Async hook
async def async_hook(ctx: ModelPipelineContext) -> None:
    await some_async_operation()
    ctx.data["async"] = True
```

### Constants

Pipeline module exports two important constants for phase behavior:

```python
from omnibase_core.pipeline import CANONICAL_PHASE_ORDER, FAIL_FAST_PHASES

# Phase execution order
CANONICAL_PHASE_ORDER
# ["preflight", "before", "execute", "after", "emit", "finalize"]

# Phases with fail-fast behavior (abort on first error)
FAIL_FAST_PHASES
# frozenset({"preflight", "before", "execute"})

# Check if a phase is fail-fast
if "execute" in FAIL_FAST_PHASES:
    print("execute phase will abort on first error")

# Phases NOT in FAIL_FAST_PHASES use continue-on-error behavior
continue_phases = [p for p in CANONICAL_PHASE_ORDER if p not in FAIL_FAST_PHASES]
# ["after", "emit", "finalize"]
```

**Use cases**:
- Check if a custom phase should be fail-fast
- Build custom phase iteration logic
- Validate phase names programmatically

```python
# Both sync and async hooks are valid HookCallable types
callables: dict[str, HookCallable] = {
    "sync.hook": sync_hook,
    "async.hook": async_hook,
}
```

## Common Patterns

### Hook Dependencies

Define execution order within a phase using dependencies:

```python
# Hook B depends on Hook A
hook_a = ModelPipelineHook(
    hook_id="setup-database",
    phase="before",
    callable_ref="app.setup_db",
)

hook_b = ModelPipelineHook(
    hook_id="load-config",
    phase="before",
    dependencies=["setup-database"],  # Runs after setup-database
    callable_ref="app.load_config",
)
```

**Note**: Dependencies must be within the same phase. Cross-phase dependencies raise `UnknownDependencyError`.

### Priority Ordering

When hooks have no dependencies, priority determines order (lower = earlier):

```python
# High priority (runs first)
critical_hook = ModelPipelineHook(
    hook_id="critical-check",
    phase="preflight",
    priority=10,
    callable_ref="app.critical",
)

# Default priority
normal_hook = ModelPipelineHook(
    hook_id="normal-check",
    phase="preflight",
    priority=100,  # Default
    callable_ref="app.normal",
)

# Low priority (runs last)
optional_hook = ModelPipelineHook(
    hook_id="optional-check",
    phase="preflight",
    priority=500,
    callable_ref="app.optional",
)
```

### Diamond Dependency Pattern

Complex dependency graphs are supported:

```python
#     A (priority=1)
#    / \
#   B   C (priority=1, 2)
#    \ /
#     D

hook_a = ModelPipelineHook(
    hook_id="A", phase="execute", callable_ref="a", priority=1
)
hook_b = ModelPipelineHook(
    hook_id="B", phase="execute", dependencies=["A"], callable_ref="b", priority=1
)
hook_c = ModelPipelineHook(
    hook_id="C", phase="execute", dependencies=["A"], callable_ref="c", priority=2
)
hook_d = ModelPipelineHook(
    hook_id="D", phase="execute", dependencies=["B", "C"], callable_ref="d", priority=1
)

# Execution order: A -> B -> C -> D
# (B before C due to lower priority)
```

### Type-Safe Hooks

Validate hooks against contract types:

```python
from omnibase_core.enums import EnumHandlerTypeCategory

# Define typed hook
compute_hook = ModelPipelineHook(
    hook_id="compute-transform",
    phase="execute",
    handler_type_category=EnumHandlerTypeCategory.COMPUTE,
    callable_ref="app.compute",
)

# Build with type enforcement (default behavior)
builder = BuilderExecutionPlan(
    registry=registry,
    contract_category=EnumHandlerTypeCategory.COMPUTE,
    # enforce_hook_typing=True is the default - raises HookTypeMismatchError on mismatch
)

# Opt-in to warning-only mode (for gradual migration or backwards compatibility)
builder = BuilderExecutionPlan(
    registry=registry,
    contract_category=EnumHandlerTypeCategory.COMPUTE,
    enforce_hook_typing=False,  # Produces warnings instead of errors
)
plan, warnings = builder.build()
```

**Type validation rules**:
- Generic hooks (`handler_type_category=None`) pass for any contract
- Typed hooks must exactly match the contract type
- No contract type (`contract_category=None`) skips validation
- **Default behavior** (`enforce_hook_typing=True`): Type mismatches raise `HookTypeMismatchError`
- **Warning-only mode** (`enforce_hook_typing=False`): Type mismatches produce warnings but allow execution

### Timeout Enforcement

Set per-hook timeouts:

```python
# Hook with 5-second timeout
slow_hook = ModelPipelineHook(
    hook_id="slow-operation",
    phase="execute",
    callable_ref="app.slow_op",
    timeout_seconds=5.0,
)

# If hook exceeds timeout, HookTimeoutError is raised
# For fail-fast phases: pipeline aborts
# For continue phases: error captured, other hooks continue
```

### Async Hooks

Mix sync and async hooks freely:

```python
import asyncio

def sync_setup(ctx: ModelPipelineContext) -> None:
    ctx.data["config"] = load_config()

async def async_fetch(ctx: ModelPipelineContext) -> None:
    ctx.data["external_data"] = await fetch_from_api()

async def async_process(ctx: ModelPipelineContext) -> None:
    await asyncio.sleep(0.1)
    ctx.data["processed"] = True

callables = {
    "sync.setup": sync_setup,
    "async.fetch": async_fetch,
    "async.process": async_process,
}

# Runner handles both transparently
runner = RunnerPipeline(plan=plan, callable_registry=callables)
result = await runner.run()
```

### Error Handling Patterns

```python
def risky_hook(ctx: ModelPipelineContext) -> None:
    """Hook in fail-fast phase - errors abort pipeline."""
    if not ctx.data.get("valid"):
        raise ValueError("Validation failed")

def optional_hook(ctx: ModelPipelineContext) -> None:
    """Hook in continue phase - errors are captured."""
    try:
        process_optional_data()
    except Exception as e:
        # Log but don't re-raise in continue phase
        ctx.data["optional_error"] = str(e)

async def run_with_error_handling():
    runner = RunnerPipeline(plan=plan, callable_registry=callables)

    try:
        result = await runner.run()
    except ValueError as e:
        # Fail-fast phase error (preflight, before, execute)
        print(f"Pipeline aborted: {e}")
        return

    # Check for errors from continue phases
    if not result.success:
        for error in result.errors:
            print(f"Non-fatal error in {error.phase}: {error.error_message}")
```

### Middleware Composition

Use `ComposerMiddleware` for onion-style wrapping:

```python
from omnibase_core.pipeline import ComposerMiddleware, Middleware
from collections.abc import Callable, Awaitable

async def logging_middleware(next_fn: Callable[[], Awaitable[object]]) -> object:
    """Log execution timing."""
    import time
    start = time.time()
    result = await next_fn()
    print(f"Execution took {time.time() - start:.2f}s")
    return result

async def error_middleware(next_fn: Callable[[], Awaitable[object]]) -> object:
    """Handle errors."""
    try:
        return await next_fn()
    except Exception as e:
        print(f"Error caught: {e}")
        raise

async def core_function() -> dict:
    """Core processing logic."""
    return {"status": "done"}

# Compose middleware
composer = ComposerMiddleware()
composer.use(logging_middleware)  # Outermost
composer.use(error_middleware)     # Inner

wrapped = composer.compose(core_function)
result = await wrapped()
# Execution: logging -> error -> core -> error -> logging
```

## Thread Safety

### Design Pattern: Freeze-After-Init

The hook registry uses a freeze-after-init pattern for thread safety:

1. **Registration Phase** (single-threaded, mutable):
   - Register all hooks
   - Modify registry state

2. **After `freeze()`** (concurrent, immutable):
   - No modifications allowed
   - Safe for concurrent reads
   - Returns copies of internal state

```python
# Single-threaded setup
registry = RegistryHook()
registry.register(hook1)
registry.register(hook2)
registry.freeze()  # Lock for concurrent access

# Now safe for concurrent reads
import threading

def worker():
    # Safe - returns copy
    hooks = registry.get_hooks_by_phase("execute")
    # Process hooks...

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

### Runner Thread Safety

**The `RunnerPipeline` is NOT thread-safe during execution.**

Create a new runner instance per execution/thread:

```python
import threading

# CORRECT: New runner per thread
def run_pipeline_in_thread(plan, callables):
    async def execute():
        runner = RunnerPipeline(plan=plan, callable_registry=callables)
        return await runner.run()

    import asyncio
    return asyncio.run(execute())

# The execution plan is frozen and can be shared
threads = [
    threading.Thread(target=run_pipeline_in_thread, args=(plan, callables))
    for _ in range(5)
]
```

### Thread Safety Summary

| Component | Thread-Safe? | Notes |
|-----------|-------------|-------|
| `RegistryHook` (before freeze) | No | Single-threaded registration |
| `RegistryHook` (after freeze) | Yes | Returns copies |
| `ModelExecutionPlan` | Yes | Frozen, immutable |
| `ModelPipelineHook` | Yes | Frozen, immutable |
| `RunnerPipeline` | No | Create per execution |
| `ModelPipelineContext` | No | Mutable, single execution |
| `BuilderExecutionPlan` | Yes | Stateless operation |

For detailed threading guidance, see [Threading Guide](THREADING.md).

## Exception Reference

| Exception | Cause | Phase |
|-----------|-------|-------|
| `HookRegistryFrozenError` | Registering after `freeze()` | Registration |
| `DuplicateHookError` | Registering hook with existing ID | Registration |
| `UnknownDependencyError` | Dependency references unknown hook | Build |
| `DependencyCycleError` | Dependencies form a cycle | Build |
| `HookTypeMismatchError` | Hook type doesn't match contract (default behavior; use `enforce_hook_typing=False` for warnings only) | Build |
| `CallableNotFoundError` | `callable_ref` not in registry | Execution |
| `HookTimeoutError` | Hook exceeded `timeout_seconds` | Execution |

## Testing Patterns

### Unit Testing Hooks

Test hooks in isolation without running the full pipeline:

```python
import pytest
from omnibase_core.pipeline import ModelPipelineContext

def test_validation_hook_sets_flag():
    """Test that validation hook sets validated flag."""
    ctx = ModelPipelineContext()

    # Call hook directly
    validation_hook(ctx)

    assert ctx.data.get("validated") is True


def test_validation_hook_rejects_invalid_data():
    """Test that validation hook raises for invalid input."""
    ctx = ModelPipelineContext()
    ctx.data["input"] = {"invalid": True}

    with pytest.raises(ValueError, match="Invalid input"):
        validation_hook(ctx)
```

### Integration Testing Pipeline Execution

Test the full pipeline with all hooks:

```python
import pytest
from omnibase_core.pipeline import (
    BuilderExecutionPlan,
    ModelPipelineHook,
    ModelPipelineContext,
    RegistryHook,
    RunnerPipeline,
)


@pytest.fixture
def test_registry():
    """Create a test registry with mock hooks."""
    registry = RegistryHook()
    registry.register(ModelPipelineHook(
        hook_id="test-setup",
        phase="before",
        callable_ref="test.setup",
    ))
    registry.register(ModelPipelineHook(
        hook_id="test-execute",
        phase="execute",
        callable_ref="test.execute",
    ))
    registry.freeze()
    return registry


@pytest.fixture
def test_callables():
    """Create test callable registry."""
    def setup_hook(ctx: ModelPipelineContext) -> None:
        ctx.data["setup_complete"] = True

    def execute_hook(ctx: ModelPipelineContext) -> None:
        assert ctx.data.get("setup_complete"), "Setup must run first"
        ctx.data["result"] = "success"

    return {
        "test.setup": setup_hook,
        "test.execute": execute_hook,
    }


@pytest.mark.asyncio
async def test_pipeline_executes_in_order(test_registry, test_callables):
    """Test that hooks execute in correct phase order."""
    builder = BuilderExecutionPlan(registry=test_registry)
    plan, _ = builder.build()

    runner = RunnerPipeline(plan=plan, callable_registry=test_callables)
    result = await runner.run()

    assert result.success
    assert result.context.data["setup_complete"] is True
    assert result.context.data["result"] == "success"


@pytest.mark.asyncio
async def test_pipeline_captures_errors_in_after_phase():
    """Test that errors in 'after' phase are captured, not raised."""
    registry = RegistryHook()
    registry.register(ModelPipelineHook(
        hook_id="after-hook",
        phase="after",
        callable_ref="after.hook",
    ))
    registry.freeze()

    def failing_hook(ctx: ModelPipelineContext) -> None:
        raise RuntimeError("After hook failed")

    builder = BuilderExecutionPlan(registry=registry)
    plan, _ = builder.build()

    runner = RunnerPipeline(
        plan=plan,
        callable_registry={"after.hook": failing_hook}
    )
    result = await runner.run()

    # Error captured, not raised (because 'after' is continue-on-error)
    assert not result.success
    assert len(result.errors) == 1
    assert result.errors[0].hook_id == "after-hook"
    assert "After hook failed" in result.errors[0].error_message


@pytest.mark.asyncio
async def test_pipeline_raises_errors_in_execute_phase():
    """Test that errors in 'execute' phase are raised (fail-fast)."""
    registry = RegistryHook()
    registry.register(ModelPipelineHook(
        hook_id="execute-hook",
        phase="execute",
        callable_ref="execute.hook",
    ))
    registry.freeze()

    def failing_hook(ctx: ModelPipelineContext) -> None:
        raise ValueError("Execute hook failed")

    builder = BuilderExecutionPlan(registry=registry)
    plan, _ = builder.build()

    runner = RunnerPipeline(
        plan=plan,
        callable_registry={"execute.hook": failing_hook}
    )

    # Error raised, not captured (because 'execute' is fail-fast)
    with pytest.raises(ValueError, match="Execute hook failed"):
        await runner.run()
```

### Testing Async Hooks

```python
import asyncio
import pytest
from omnibase_core.pipeline import ModelPipelineContext


@pytest.mark.asyncio
async def test_async_hook_completes():
    """Test async hook execution."""
    ctx = ModelPipelineContext()

    async def async_fetch_hook(ctx: ModelPipelineContext) -> None:
        await asyncio.sleep(0.01)  # Simulate async operation
        ctx.data["fetched"] = True

    await async_fetch_hook(ctx)

    assert ctx.data["fetched"] is True


@pytest.mark.asyncio
async def test_hook_timeout():
    """Test that slow hooks respect timeout."""
    from omnibase_core.pipeline import (
        BuilderExecutionPlan,
        HookTimeoutError,
        ModelPipelineHook,
        RegistryHook,
        RunnerPipeline,
    )

    registry = RegistryHook()
    registry.register(ModelPipelineHook(
        hook_id="slow-hook",
        phase="execute",
        callable_ref="slow.hook",
        timeout_seconds=0.1,  # 100ms timeout
    ))
    registry.freeze()

    async def slow_hook(ctx: ModelPipelineContext) -> None:
        await asyncio.sleep(10)  # Way longer than timeout

    builder = BuilderExecutionPlan(registry=registry)
    plan, _ = builder.build()

    runner = RunnerPipeline(
        plan=plan,
        callable_registry={"slow.hook": slow_hook}
    )

    with pytest.raises(HookTimeoutError):
        await runner.run()
```

### Testing Dependencies and Priority

```python
import pytest
from omnibase_core.pipeline import (
    BuilderExecutionPlan,
    DependencyCycleError,
    ModelPipelineHook,
    RegistryHook,
    UnknownDependencyError,
)


def test_unknown_dependency_raises():
    """Test that unknown dependencies raise an error."""
    registry = RegistryHook()
    registry.register(ModelPipelineHook(
        hook_id="child",
        phase="execute",
        dependencies=["nonexistent"],  # This doesn't exist
        callable_ref="child.hook",
    ))
    registry.freeze()

    builder = BuilderExecutionPlan(registry=registry)

    with pytest.raises(UnknownDependencyError) as exc_info:
        builder.build()

    assert "nonexistent" in str(exc_info.value)


def test_dependency_cycle_raises():
    """Test that circular dependencies raise an error."""
    registry = RegistryHook()
    registry.register(ModelPipelineHook(
        hook_id="A",
        phase="execute",
        dependencies=["B"],
        callable_ref="a.hook",
    ))
    registry.register(ModelPipelineHook(
        hook_id="B",
        phase="execute",
        dependencies=["A"],  # Circular!
        callable_ref="b.hook",
    ))
    registry.freeze()

    builder = BuilderExecutionPlan(registry=registry)

    with pytest.raises(DependencyCycleError):
        builder.build()


def test_priority_ordering():
    """Test that hooks are ordered by priority when no dependencies."""
    registry = RegistryHook()
    registry.register(ModelPipelineHook(
        hook_id="low-priority",
        phase="execute",
        priority=500,
        callable_ref="low.hook",
    ))
    registry.register(ModelPipelineHook(
        hook_id="high-priority",
        phase="execute",
        priority=10,
        callable_ref="high.hook",
    ))
    registry.freeze()

    builder = BuilderExecutionPlan(registry=registry)
    plan, _ = builder.build()

    hooks = plan.get_phase_hooks("execute")
    assert hooks[0].hook_id == "high-priority"  # Lower priority value = earlier
    assert hooks[1].hook_id == "low-priority"
```

### Mocking External Dependencies

```python
import pytest
from unittest.mock import AsyncMock, patch
from omnibase_core.pipeline import ModelPipelineContext


@pytest.mark.asyncio
async def test_hook_with_mocked_external_service():
    """Test hook that calls external service with mock."""
    async def api_hook(ctx: ModelPipelineContext) -> None:
        # In real code, this would call an external API
        from some_module import external_api
        result = await external_api.fetch_data(ctx.data["user_id"])
        ctx.data["api_result"] = result

    ctx = ModelPipelineContext()
    ctx.data["user_id"] = "user123"

    with patch("some_module.external_api.fetch_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"status": "ok", "data": [1, 2, 3]}

        await api_hook(ctx)

        mock_fetch.assert_called_once_with("user123")
        assert ctx.data["api_result"]["status"] == "ok"
```

## Troubleshooting

### "Cannot modify frozen hook registry"

**Cause**: Attempting to register hooks after calling `freeze()`.

**Solution**: Register all hooks before freezing:

```python
registry = RegistryHook()
registry.register(hook1)  # Before freeze
registry.freeze()
registry.register(hook2)  # Error! Already frozen
```

### "Hook with ID 'xxx' already registered"

**Cause**: Duplicate hook IDs.

**Solution**: Use unique hook IDs:

```python
# Each hook needs a unique ID
registry.register(ModelPipelineHook(hook_id="unique-id-1", ...))
registry.register(ModelPipelineHook(hook_id="unique-id-2", ...))
```

### "Hook 'xxx' references unknown dependency 'yyy'"

**Cause**: Dependency refers to non-existent hook or hook in different phase.

**Solution**:
- Ensure all dependencies are registered
- Ensure dependencies are in the same phase

```python
# Dependencies must be in same phase
hook_a = ModelPipelineHook(hook_id="setup", phase="before", ...)
hook_b = ModelPipelineHook(
    hook_id="main",
    phase="before",  # Same phase as dependency
    dependencies=["setup"],
    ...
)
```

### "Dependency cycle detected"

**Cause**: Hooks form a circular dependency.

**Solution**: Remove the cycle by restructuring dependencies:

```python
# WRONG: A -> B -> A (cycle)
hook_a = ModelPipelineHook(hook_id="A", dependencies=["B"], ...)
hook_b = ModelPipelineHook(hook_id="B", dependencies=["A"], ...)

# CORRECT: A -> B (no cycle)
hook_a = ModelPipelineHook(hook_id="A", dependencies=[], ...)
hook_b = ModelPipelineHook(hook_id="B", dependencies=["A"], ...)
```

### "Callable not found in registry: xxx"

**Cause**: `callable_ref` doesn't have a matching entry in the callable registry.

**Solution**: Ensure all `callable_ref` values have corresponding entries:

```python
hook = ModelPipelineHook(callable_ref="app.my_func", ...)

callables = {
    "app.my_func": my_function,  # Must match callable_ref
}
```

### Finalize not running

**Cause**: Likely a bug - finalize ALWAYS runs.

**Solution**: Verify your hooks are in the `finalize` phase:

```python
# Finalize hooks must have phase="finalize"
cleanup = ModelPipelineHook(
    hook_id="cleanup",
    phase="finalize",  # Not "after" or "emit"
    callable_ref="app.cleanup",
)
```

## Migration Notes

### Hook Typing Enforcement (OMN-1157) - Breaking Change

**Version**: v0.6.0+

**What Changed**: The `enforce_hook_typing` parameter in `BuilderExecutionPlan` now defaults to `True` (was `False`).

| Aspect | Before (v0.5.x) | After (v0.6.0+) |
|--------|-----------------|-----------------|
| **Default behavior** | Type mismatches produce warnings | Type mismatches raise `HookTypeMismatchError` |
| **Parameter default** | `enforce_hook_typing=False` | `enforce_hook_typing=True` |
| **Impact** | Silent failures possible | Fail-fast on type errors |

#### Impact on Existing Code

If your code:
1. **Uses typed hooks** (`handler_type_category` set on hooks)
2. **Has a `contract_category`** set on the builder
3. **Has type mismatches** between hook types and contract category

**Then**: Your code will now raise `HookTypeMismatchError` at build time instead of producing a warning.

#### How to Identify Affected Code

```bash
# Find code that uses BuilderExecutionPlan with contract_category
grep -rn "BuilderExecutionPlan" --include="*.py" | grep "contract_category"

# Find hooks with handler_type_category set
grep -rn "handler_type_category=" --include="*.py"
```

#### Migration Steps

**Option 1: Fix Type Mismatches (Recommended)**

Ensure your hook types match the contract category:

```python
from omnibase_core.pipeline import BuilderExecutionPlan, ModelPipelineHook
from omnibase_core.enums import EnumHandlerTypeCategory

# Hook type MUST match contract_category
hook = ModelPipelineHook(
    hook_id="my-hook",
    phase="execute",
    callable_ref="my.hook",
    handler_type_category=EnumHandlerTypeCategory.COMPUTE,  # Must match builder
)

registry.register(hook)
registry.freeze()

builder = BuilderExecutionPlan(
    registry=registry,
    contract_category=EnumHandlerTypeCategory.COMPUTE,  # Matches hook type
    # enforce_hook_typing=True is now the default
)
plan, warnings = builder.build()  # No error - types match
```

**Option 2: Use Generic Hooks**

Generic hooks (no `handler_type_category`) pass validation for any contract:

```python
# Generic hook - passes for any contract_category
hook = ModelPipelineHook(
    hook_id="generic-hook",
    phase="execute",
    callable_ref="my.hook",
    # handler_type_category not set - this is a generic hook
)
```

**Option 3: Opt-Out (Not Recommended for Production)**

For gradual migration, explicitly set `enforce_hook_typing=False`:

```python
# Opt-out: warning-only mode (not recommended for production)
builder = BuilderExecutionPlan(
    registry=registry,
    contract_category=EnumHandlerTypeCategory.COMPUTE,
    enforce_hook_typing=False,  # Explicit opt-out to legacy behavior
)
plan, warnings = builder.build()

# Check warnings for type mismatches
for warning in warnings:
    if warning.code == "HOOK_TYPE_MISMATCH":
        print(f"Warning: {warning.message}")
```

**Warning**: Opting out masks potential configuration errors. Use only during migration.

#### Why This Change?

1. **Fail-fast behavior**: Catches configuration errors at build time, not runtime
2. **Type safety**: Ensures hooks are compatible with their intended contract
3. **Production reliability**: Prevents silent failures from misconfigured pipelines
4. **ONEX principles**: Aligns with strict type enforcement across the framework

#### Quick Migration Checklist

- [ ] Search codebase for `BuilderExecutionPlan` usage with `contract_category`
- [ ] Review hooks for `handler_type_category` settings
- [ ] Fix type mismatches OR use generic hooks (no `handler_type_category`)
- [ ] Remove explicit `enforce_hook_typing=False` after migration is complete
- [ ] Run tests to verify no `HookTypeMismatchError` is raised unexpectedly

**See also**: [CHANGELOG.md](../../CHANGELOG.md) for full release notes and additional migration examples.

### Backwards Compatibility Aliases

The module provides backwards compatibility aliases:

```python
# New names (preferred)
from omnibase_core.pipeline import (
    RegistryHook,
    BuilderExecutionPlan,
    RunnerPipeline,
    ComposerMiddleware,
)

```

## Related Documentation

- [Threading Guide](THREADING.md) - Detailed thread safety guidance
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node type overview
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns

---

**Last Updated**: 2026-01-01
**Version**: 1.1.0
**Related PR**: #291 (OMN-1114), OMN-1157 (enforce_hook_typing default change)
