# Common Pitfalls - What to Avoid When Building Nodes

**Status**: 🚧 Coming Soon - Planned Documentation
**Version**: 1.0.0 (planned)
**Last Updated**: 2025-01-20
**Estimated Reading Time**: 15 minutes

## Overview

This guide will catalog common mistakes, anti-patterns, and pitfalls developers encounter when building ONEX nodes, along with explanations and solutions for each issue.

## Planned Content

### 1. General Node Pitfalls

#### Pitfall: Using `pip` Instead of Poetry
**Problem**: Direct pip usage bypasses project dependency management
**Solution**: Always use `poetry run` and `poetry add`
```bash
# ❌ Wrong
pip install package
python script.py

# ✅ Correct
poetry add package
poetry run python script.py
```

#### Pitfall: Missing Type Annotations
**Problem**: Reduced type safety and IDE support
**Solution**: Use complete Pydantic models and type hints

#### Pitfall: Improper Error Handling
**Problem**: Catching generic exceptions without context
**Solution**: Use OnexError with proper exception chaining

#### Pitfall: Blocking I/O in Async Context
**Problem**: Running synchronous blocking operations in async methods
**Solution**: Use appropriate async libraries or run_in_executor

### 2. COMPUTE Node Pitfalls

#### Pitfall: Side Effects in COMPUTE Nodes
**Problem**: COMPUTE nodes should be pure transformations
**Impact**: Unpredictable behavior, difficult testing, caching issues
**Solution**: Move side effects to EFFECT nodes

#### Pitfall: Stateful COMPUTE Nodes
**Problem**: Maintaining state between executions
**Impact**: Race conditions, unpredictable results
**Solution**: Keep COMPUTE nodes stateless and pure

#### Pitfall: Heavy Computation Without Optimization
**Problem**: No consideration for performance
**Impact**: Slow execution, resource exhaustion
**Solution**: Use caching, lazy evaluation, or batch processing

### 3. EFFECT Node Pitfalls

#### Pitfall: Non-Idempotent Operations
**Problem**: Operations that fail on retry
**Impact**: Cannot safely retry failed operations
**Solution**: Design for idempotency with unique identifiers

#### Pitfall: Missing Transaction Management
**Problem**: No rollback on partial failures
**Impact**: Inconsistent state after errors
**Solution**: Use transaction contexts and proper cleanup

#### Pitfall: Hardcoded External Dependencies
**Problem**: Direct instantiation of clients/connections
**Impact**: Difficult testing, tight coupling
**Solution**: Use dependency injection via ModelONEXContainer

#### Pitfall: Ignoring Timeout Handling
**Problem**: No timeouts on external calls
**Impact**: Hanging operations, resource leaks
**Solution**: Configure appropriate timeouts and handle timeout exceptions

### 4. REDUCER Node Pitfalls

#### Pitfall: Direct State Mutation
**Problem**: Modifying state without FSM transitions
**Impact**: Inconsistent state, lost audit trail
**Solution**: Use FSM pattern with explicit state transitions

#### Pitfall: Backwards Compatibility Methods
**Problem**: Keeping deprecated non-FSM methods
**Impact**: Confusion, inconsistent behavior
**Solution**: Remove backwards compatibility, pure FSM only

#### Pitfall: Missing Intent Emission
**Problem**: Not emitting Intents for state changes
**Impact**: No coordination with Orchestrators
**Solution**: Always emit ModelIntent for state transitions

#### Pitfall: Blocking Aggregation Logic
**Problem**: Synchronous aggregation of large datasets
**Impact**: Performance bottlenecks
**Solution**: Use async aggregation patterns

### 5. ORCHESTRATOR Node Pitfalls

#### Pitfall: Missing Lease Management
**Problem**: Not using ModelAction with lease tracking
**Impact**: Resource leaks, dangling actions
**Solution**: Always use lease management for Actions

#### Pitfall: Tight Coupling to Child Nodes
**Problem**: Direct instantiation of orchestrated nodes
**Impact**: Difficult testing, inflexible workflows
**Solution**: Use dependency injection and interfaces

#### Pitfall: No Error Recovery Strategy
**Problem**: Workflows fail completely on single error
**Impact**: Poor resilience, lost work
**Solution**: Implement graceful degradation and retry logic

#### Pitfall: Synchronous Workflow Execution
**Problem**: Sequential execution when parallelism possible
**Impact**: Poor performance
**Solution**: Use asyncio.gather for independent operations

### 6. Testing Pitfalls

#### Pitfall: Testing Implementation Instead of Behavior
**Problem**: Tests coupled to internal implementation
**Impact**: Brittle tests that break on refactoring
**Solution**: Test public interfaces and contracts

#### Pitfall: No Async Test Support
**Problem**: Not using pytest-asyncio for async nodes
**Impact**: Tests don't properly exercise async behavior
**Solution**: Use `@pytest.mark.asyncio` and async fixtures

#### Pitfall: Insufficient Error Case Testing
**Problem**: Only testing happy paths
**Impact**: Unhandled errors in production
**Solution**: Test error cases, edge cases, and boundaries

### 7. Architecture Pitfalls

#### Pitfall: Wrong Node Type Selection
**Problem**: Using EFFECT when COMPUTE appropriate (or vice versa)
**Impact**: Unnecessary complexity, poor performance
**Solution**: Review [Node Types](02_NODE_TYPES.md) decision tree

#### Pitfall: Mixing Node Type Responsibilities
**Problem**: COMPUTE node doing I/O, EFFECT node doing transformations
**Impact**: Unclear separation of concerns
**Solution**: Keep node types pure to their purpose

#### Pitfall: Skipping Contract Validation
**Problem**: Not using Pydantic contract validation
**Impact**: Runtime errors from invalid data
**Solution**: Always validate contracts at boundaries

### 8. Performance Pitfalls

#### Pitfall: N+1 Query Problem
**Problem**: Individual queries in loops
**Impact**: Database performance degradation
**Solution**: Use batch operations and bulk queries

#### Pitfall: No Connection Pooling
**Problem**: Creating new connections per operation
**Impact**: Resource exhaustion, slow performance
**Solution**: Use connection pools via ModelONEXContainer

#### Pitfall: Missing Cache Strategy
**Problem**: Recomputing expensive operations
**Impact**: Wasted resources, slow execution
**Solution**: Implement appropriate caching at COMPUTE or REDUCER level

### 9. Deployment Pitfalls

#### Pitfall: Missing Environment Configuration
**Problem**: Hardcoded values instead of configuration
**Impact**: Cannot adapt to different environments
**Solution**: Use environment variables and configuration management

#### Pitfall: No Health Checks
**Problem**: No way to verify node operational status
**Impact**: Difficult monitoring and debugging
**Solution**: Implement health check endpoints

#### Pitfall: Insufficient Logging
**Problem**: No structured logging with context
**Impact**: Difficult troubleshooting in production
**Solution**: Use structured logging with correlation IDs

## Temporary Resources

While this guide is being developed, refer to existing resources:

### Anti-Pattern Documentation
- [Anti-Patterns](../../patterns/ANTI_PATTERNS.md) - Known anti-patterns to avoid
- [Error Handling Best Practices](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Proper error handling

### Architecture Guidance
- [ONEX Four-Node Architecture](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Understanding node responsibilities
- [Pure FSM Reducer Pattern](../../patterns/PURE_FSM_REDUCER_PATTERN.md) - Correct REDUCER implementation

## Coming Soon

This pitfalls guide will include:

- ✅ **Real-World Examples** - Actual mistakes from production
- ✅ **Before/After Code** - Clear problem and solution examples
- ✅ **Detection Strategies** - How to identify pitfalls in code review
- ✅ **Automated Checks** - Linting rules to catch common issues
- ✅ **Performance Impact Analysis** - Quantifying the cost of pitfalls
- ✅ **Migration Guides** - How to fix existing code

## Quick Pitfall Checklist

Before finalizing your node, check:

- [ ] Using Poetry for all Python operations
- [ ] Complete type annotations with Pydantic
- [ ] Proper OnexError usage with exception chaining
- [ ] Node type matches responsibility (COMPUTE=pure, EFFECT=I/O, etc.)
- [ ] Async operations properly handled (no blocking I/O)
- [ ] Error cases tested and handled
- [ ] Dependencies injected via ModelONEXContainer
- [ ] Transaction management for EFFECT nodes
- [ ] FSM pattern for REDUCER nodes
- [ ] Lease management for ORCHESTRATOR nodes
- [ ] Structured logging with context
- [ ] Configuration externalized (no hardcoded values)

## Related Documentation

- [README](README.md) - Node Building Guide overview
- [Node Types](02_NODE_TYPES.md) - Understanding correct node type selection
- [Patterns Catalog](07-patterns-catalog.md) - Correct patterns to use (coming soon)
- [Testing Guide](08-testing-guide.md) - Testing strategies (coming soon)

---

**TODO**: This document is planned for Phase 2 of documentation development. Check [DOCUMENTATION_ARCHITECTURE.md](../../architecture/DOCUMENTATION_ARCHITECTURE.md) for the development roadmap.

**Last Updated**: 2025-01-20
