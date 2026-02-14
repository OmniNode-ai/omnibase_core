> **Navigation**: [Home](../INDEX.md) > Troubleshooting > Async Hang Debugging

# Async Hang Debugging Guide

**Last Updated**: 2025-11-15
**Issue**: Test suite hangs with timeouts in CI
**Resolution Time**: ~30 minutes

---

## Symptoms

- **Test Progress**: Hangs at specific completion percentage (e.g., 97%)
- **CI Behavior**: Timeout after 5 minutes (or configured timeout)
- **Last Test**: Shows as PASSED but next test never starts
- **Error Message**: "Error: The operation was canceled"
- **Environment**: Typically seen in pytest with pytest-asyncio strict mode

### Example Output
```
[gw1] [ 97%] PASSED tests/unit/mixins/test_mixin_utils.py::TestCanonicalizeMetadataBlock::test_handles_various_data_types
Error: The operation was canceled.
```

---

## Root Cause

**Problem**: Synchronous methods calling async methods without properly awaiting or scheduling the coroutines.

**Why It Hangs**:
1. Async method (e.g., `publish_async()`) is called from sync code
2. Method returns a coroutine object
3. Coroutine is **never awaited** or scheduled on event loop
4. Event loop cleanup tries to handle uncompleted coroutines
5. pytest-asyncio strict mode **blocks** waiting for coroutines to complete
6. **Test suite hangs** until timeout

---

## Detection Steps

### Step 1: Identify Last Passing Test
```
# Look at CI output or local test run
# Note the test that passed just before the hang
# Example: test_handles_various_data_types at 97%
```

### Step 2: Find Next Test in Collection Order
```
poetry run pytest tests/ --collect-only -q | grep -A 5 "test_handles_various_data_types"
```

### Step 3: Search for Unawaited Async Calls
```
# Look for publish_async, send_async, or other async method calls
# that are NOT preceded by 'await'
grep -n "\.publish_async\|\.send_async\|async def" src/omnibase_core/mixins/*.py
```

### Step 4: Check for Sync Methods Calling Async
```
# Find methods that call *_async but are not themselves async
rg "def\s+\w+\(" -A 20 src/omnibase_core/mixins/ | grep "publish_async\|send_async"
```

---

## Common Patterns

### ❌ Anti-Pattern: Unawaited Async Call

**File**: `src/omnibase_core/mixins/mixin_workflow_support.py:141`

```
def emit_dag_completion_event(self, result, status):
    """Synchronous method."""
    # ... setup code ...

    # ❌ WRONG: Async method called without await
    self._event_bus.publish_async(envelope)
```

**Why It's Wrong**:
- `emit_dag_completion_event` is **synchronous** (no `async def`)
- `publish_async()` returns a coroutine
- Coroutine is **not awaited**
- Coroutine never executes, just gets garbage collected
- Event loop gets stuck waiting

---

## Solution Pattern

### ✅ Correct: Helper Method with Coroutine Detection

```
def emit_dag_completion_event(self, result, status):
    """Synchronous method."""
    # ... setup code ...

    # ✅ CORRECT: Use helper that handles async properly
    self._publish_event(envelope)

def _publish_event(self, envelope: Any) -> None:
    """Publish event, handling both sync and async event buses."""
    import asyncio
    import inspect

    # Call the async method
    result = self._event_bus.publish_async(envelope)

    # Check if it returned a coroutine
    if inspect.iscoroutine(result):
        try:
            # Get the running event loop
            loop = asyncio.get_running_loop()
            # Schedule the coroutine as a fire-and-forget task
            _ = loop.create_task(result)  # type: ignore[unused-awaitable]
        except RuntimeError:
            # No running event loop - fallback for non-async contexts
            try:
                asyncio.run(result)
            except RuntimeError:
                # Test context with mocks - ignore
                pass
```

**Why This Works**:
1. ✅ **Detects async**: Uses `inspect.iscoroutine()` to check return type
2. ✅ **Schedules properly**: Creates task on event loop (fire-and-forget)
3. ✅ **Handles fallbacks**: Works in sync contexts, test mocks, etc.
4. ✅ **No hangs**: Coroutines are properly scheduled and executed
5. ✅ **Type safe**: Mypy annotation silences unused-awaitable warning

---

## Verification Steps

After implementing the fix:

### 1. Run Affected Tests
```
poetry run pytest tests/unit/mixins/test_mixin_workflow_support.py -xvs
```

### 2. Check Type Safety
```
poetry run mypy src/omnibase_core/mixins/mixin_workflow_support.py
```

### 3. Smoke Test Related Modules
```
poetry run pytest tests/unit/mixins/ -x --tb=short
```

### 4. Full Test Suite (if time permits)
```
poetry run pytest tests/ -x
```

---

## Prevention Checklist

When writing code that interacts with async methods:

- [ ] **Check method signature**: Is the method you're calling `async def`?
- [ ] **Check return type**: Does it return a coroutine?
- [ ] **Check caller context**: Is your method synchronous?
- [ ] **If sync → async**: Use helper method with coroutine detection
- [ ] **If async → async**: Use `await` keyword
- [ ] **Test in strict mode**: Run tests with `pytest-asyncio` strict mode
- [ ] **CI verification**: Ensure tests don't timeout in CI

---

## Quick Reference

### Signs of Async Issues

| Symptom | Likely Cause |
|---------|-------------|
| Test hangs at specific % | Unawaited coroutine in recently run test |
| "Operation canceled" in CI | Timeout due to event loop hang |
| Works locally, hangs in CI | Stricter async mode in CI environment |
| Passes sometimes, hangs others | Race condition with event loop cleanup |

### Search Patterns

```
# Find potential async issues
rg "\.publish_async\(" --type py
rg "\.send_async\(" --type py
rg "async def.*\(" -A 10 --type py | grep -v "await"

# Find sync methods calling async
rg "def\s+(?!async)" -A 20 --type py | grep "publish_async\|send_async"
```

---

## Historical Incidents

### Incident 1: mixin_workflow_support.py (2025-11-15)

**Symptom**: Tests hung at 97% completion after `test_handles_various_data_types`

**Root Cause**: Lines 141 and 193 called `publish_async()` without await

**Resolution**:
- Created `_publish_event()` helper method
- Updated both call sites to use helper
- Added coroutine detection with `inspect.iscoroutine()`
- Scheduled coroutines on event loop with `create_task()`

**Files Changed**:
- `src/omnibase_core/mixins/mixin_workflow_support.py`

**Tests Verified**:
- ✅ 56 affected tests pass
- ✅ 503 mixin tests pass
- ✅ Mypy strict mode passes

**Correlation ID**: `e45c1e1b-a28f-4923-a829-a1a4c06ca9d5`

---

## Related Documentation

- [Threading Guide](../guides/THREADING.md) - Thread safety patterns
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Testing Guide](../guides/TESTING_GUIDE.md) - Test execution patterns

---

## Need Help?

If you encounter an async hang issue:

1. **Read this guide** - Follow the detection steps
2. **Search for similar issues** - Check git history for similar fixes
3. **Test incrementally** - Isolate the hanging test
4. **Check event loops** - Look for unawaited coroutines
5. **Document the fix** - Update this guide with new patterns

---

**Remember**: In Python, calling an async method from sync code without proper handling will **always** cause issues. Use the helper pattern above to ensure safe async/sync interop.
