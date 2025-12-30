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
    PipelineContext,
    RegistryHook,
    RunnerPipeline,
)

# Step 1: Create hooks
def logging_hook(ctx: PipelineContext) -> None:
    """Log pipeline start."""
    ctx.data["started_at"] = "2025-01-01T00:00:00Z"
    print("Pipeline started")

def validation_hook(ctx: PipelineContext) -> None:
    """Validate input data."""
    ctx.data["validated"] = True
    print("Validation passed")

def main_processing(ctx: PipelineContext) -> None:
    """Main processing logic."""
    ctx.data["result"] = {"status": "success"}
    print("Processing complete")

def cleanup_hook(ctx: PipelineContext) -> None:
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

```
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

### Component Overview

```
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

# Create builder
builder = BuilderExecutionPlan(
    registry=registry,                          # Must be frozen
    contract_category=EnumHandlerTypeCategory.COMPUTE,  # Optional type validation
    enforce_hook_typing=True,                   # Raise error on type mismatch
)

# Build plan (validates and sorts hooks)
plan, warnings = builder.build()

# Check warnings (type mismatches when enforce_hook_typing=False)
for warning in warnings:
    print(f"Warning: {warning.code} - {warning.message}")
```

**Validation performed**:

1. **Hook type validation** (if `contract_category` set):
   - Generic hooks (`handler_type_category=None`) pass for any contract
   - Typed hooks must match contract type
   - Mismatch behavior controlled by `enforce_hook_typing`

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
from omnibase_core.pipeline import RunnerPipeline, PipelineContext, PipelineResult

# Create runner
runner = RunnerPipeline(
    plan=plan,                    # From BuilderExecutionPlan.build()
    callable_registry=callables,  # Dict mapping callable_ref to actual callables
)

# Execute (async)
result: PipelineResult = await runner.run()

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

### PipelineContext

Shared mutable context passed to all hooks.

```python
from omnibase_core.pipeline import PipelineContext

def my_hook(ctx: PipelineContext) -> None:
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
result.context    # PipelineContext | None - Final context state
```

### HookCallable Type

Type alias for hook functions.

```python
from omnibase_core.pipeline import HookCallable, PipelineContext

# Sync hook
def sync_hook(ctx: PipelineContext) -> None:
    ctx.data["sync"] = True

# Async hook
async def async_hook(ctx: PipelineContext) -> None:
    await some_async_operation()
    ctx.data["async"] = True

# Both are valid HookCallable types
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

# Build with type enforcement
builder = BuilderExecutionPlan(
    registry=registry,
    contract_category=EnumHandlerTypeCategory.COMPUTE,
    enforce_hook_typing=True,  # Raises HookTypeMismatchError on mismatch
)

# Or with warnings only
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

def sync_setup(ctx: PipelineContext) -> None:
    ctx.data["config"] = load_config()

async def async_fetch(ctx: PipelineContext) -> None:
    ctx.data["external_data"] = await fetch_from_api()

async def async_process(ctx: PipelineContext) -> None:
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
def risky_hook(ctx: PipelineContext) -> None:
    """Hook in fail-fast phase - errors abort pipeline."""
    if not ctx.data.get("valid"):
        raise ValueError("Validation failed")

def optional_hook(ctx: PipelineContext) -> None:
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
| `PipelineContext` | No | Mutable, single execution |
| `BuilderExecutionPlan` | Yes | Stateless operation |

For detailed threading guidance, see [Threading Guide](THREADING.md).

## Exception Reference

| Exception | Cause | Phase |
|-----------|-------|-------|
| `HookRegistryFrozenError` | Registering after `freeze()` | Registration |
| `DuplicateHookError` | Registering hook with existing ID | Registration |
| `UnknownDependencyError` | Dependency references unknown hook | Build |
| `DependencyCycleError` | Dependencies form a cycle | Build |
| `HookTypeMismatchError` | Hook type doesn't match contract (when enforced) | Build |
| `CallableNotFoundError` | `callable_ref` not in registry | Execution |
| `HookTimeoutError` | Hook exceeded `timeout_seconds` | Execution |

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

# Legacy aliases (still work)
from omnibase_core.pipeline import (
    HookRegistry,        # Alias for RegistryHook
    RuntimePlanBuilder,  # Alias for BuilderExecutionPlan
    PipelineRunner,      # Alias for RunnerPipeline
    MiddlewareComposer,  # Alias for ComposerMiddleware
)
```

## Related Documentation

- [Threading Guide](THREADING.md) - Detailed thread safety guidance
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node type overview
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns

---

**Last Updated**: 2025-12-30
**Version**: 1.0.0
**Related PR**: #291 (OMN-1114)
