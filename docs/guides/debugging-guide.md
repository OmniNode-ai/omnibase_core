# Debugging Guide - omnibase_core

**Status**: 🚧 Coming Soon

## Overview

Techniques and tools for debugging ONEX nodes and identifying issues quickly.

## Debugging Strategies

### 1. Systematic Debugging
- Reproduce the issue
- Isolate the problem
- Identify root cause
- Fix and verify

### 2. Common Issues

**Node Not Loading**:
- Check container registration
- Verify protocol implementation
- Validate dependencies

**Type Errors**:
- Run `poetry run mypy src/`
- Check contract compliance
- Verify model field types

**Runtime Errors**:
- Check OnexError messages
- Review error chains
- Validate input data

**Performance Issues**:
- Profile with cProfile
- Check cache hit rates
- Review database queries

## Debugging Tools

### Python Debugger (pdb)
```python
import pdb; pdb.set_trace()
```

### Logging
```python
self.logger.debug(f"Processing: {data}")
self.logger.error(f"Failed: {error}", exc_info=True)
```

### Type Checking
```bash
poetry run mypy src/ --show-error-codes
```

### Testing
```bash
# Run single test with verbose output
poetry run pytest tests/test_my_node.py::test_specific -vv
```

## Common Error Patterns

### OnexError with Wrong Error Code
**Problem**: Using generic error codes
**Solution**: Use specific error codes from your error enum

### Missing Type Annotations
**Problem**: mypy complains about types
**Solution**: Add explicit type hints

### Container Resolution Failures
**Problem**: Service not found in container
**Solution**: Verify protocol registration and service implementation

### State Mutation in REDUCER
**Problem**: REDUCER mutates state instead of returning new state
**Solution**: Use pure FSM pattern with immutable state

## Debugging Workflows

### Debug EFFECT Node
1. Mock external dependencies
2. Test transaction behavior
3. Verify error handling
4. Check idempotency

### Debug COMPUTE Node
1. Test with simple inputs
2. Check cache behavior
3. Verify pure computation
4. Profile performance

### Debug REDUCER Node
1. Log state transitions
2. Verify Intent emission
3. Check FSM properties
4. Test all state paths

### Debug ORCHESTRATOR Node
1. Log workflow steps
2. Test error recovery
3. Verify coordination
4. Check dependency order

## Performance Debugging

### Profiling
```python
import cProfile
cProfile.run('my_function()')
```

### Memory Profiling
```python
from memory_profiler import profile

@profile
def my_function():
    pass
```

### Async Debugging
```bash
# Enable asyncio debug mode
PYTHONASYNCIODEBUG=1 poetry run python my_script.py
```

## Next Steps

- [Testing Guide](testing-guide.md) - Comprehensive testing
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error patterns
- [Development Workflow](development-workflow.md) - Complete workflow

---

**Related Documentation**:
- [Threading Guide](../reference/THREADING.md)
- [Performance Benchmarks](../reference/PERFORMANCE_BENCHMARKS.md)
