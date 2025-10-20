# Development Workflow Guide - omnibase_core

**Status**: 🚧 Coming Soon

## Overview

This guide describes the recommended development workflow for building ONEX nodes and services.

## Development Cycle

### 1. Planning Phase
- Define node requirements
- Choose node type (EFFECT/COMPUTE/REDUCER/ORCHESTRATOR)
- Design contracts and interfaces

### 2. Implementation Phase
- Create node class
- Implement business logic
- Add error handling
- Write documentation

### 3. Testing Phase
- Unit tests
- Integration tests
- Type checking with mypy
- Code quality checks

### 4. Review Phase
- Code review
- Documentation review
- ONEX compliance check
- Performance validation

### 5. Deployment Phase
- Version bump
- Release notes
- Deployment to production

## Tools and Commands

### Code Quality
```bash
# Type checking
poetry run mypy src/

# Formatting
poetry run black src/ tests/
poetry run isort src/ tests/

# Linting
poetry run ruff check src/
```

### Testing
```bash
# Run all tests
poetry run pytest tests/

# Run with coverage
poetry run pytest tests/ --cov=src

# Run specific test
poetry run pytest tests/unit/test_my_node.py -v
```

## Best Practices

1. **Always use Poetry** for package management
2. **Write tests first** (TDD approach)
3. **Document as you code** (not after)
4. **Use ONEX patterns** (don't reinvent)
5. **Validate before committing** (run all checks)

## Common Workflows

**Adding a new dependency**:
```bash
poetry add package-name
```

**Creating a new node**:
```bash
# Use templates from docs/reference/templates/
```

**Running pre-commit hooks**:
```bash
pre-commit run --all-files
```

## Next Steps

- [Testing Guide](testing-guide.md) - Comprehensive testing strategies
- [Debugging Guide](debugging-guide.md) - Debugging techniques
- [Node Building Guide](node-building/README.md) - Node implementation patterns

---

**Related Documentation**:
- [ONEX Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Node Templates](../reference/templates/)
