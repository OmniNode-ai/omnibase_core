# Contributing to omnibase_core

Thank you for your interest in contributing to omnibase_core! This document provides guidelines for contributing to the ONEX core framework.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Code of Conduct](#code-of-conduct)

## Getting Started

### Prerequisites

- Python 3.12+
- Poetry (for package management)
- Git
- Basic understanding of ONEX architecture

### First Steps

1. **Read the documentation**:
   - [ONEX Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
   - [Node Building Guide](docs/guides/node-building/README.md)
   - [Development Workflow](docs/guides/development-workflow.md)

2. **Explore the codebase**:
   - Review existing node implementations in `src/omnibase_core/`
   - Study the base classes in `src/omnibase_core/core/`
   - Check out example implementations in `examples/`

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/omnibase_core.git
cd omnibase_core
```

### 2. Install Dependencies

```bash
# Install with Poetry
poetry install

# Activate virtual environment
poetry shell
```

### 3. Set Up Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install
```

### 4. Verify Setup

```bash
# Run tests
poetry run pytest tests/

# Run type checking
poetry run mypy src/

# Run linting
poetry run ruff check src/
```

## Contributing Guidelines

### Types of Contributions

We welcome:

- **Bug fixes** - Fix issues in existing code
- **New features** - Add new ONEX patterns or capabilities
- **Documentation** - Improve docs, examples, tutorials
- **Tests** - Add test coverage
- **Performance improvements** - Optimize existing code

### Before You Start

1. **Check existing issues** - Look for related issues or discussions
2. **Open an issue first** - For significant changes, discuss before implementing
3. **Get feedback early** - Share your approach before investing too much time

## Code Standards

### ONEX Naming Conventions

**Files**:
- Nodes: `node_<name>_<type>.py`
- Models: `model_<name>.py`
- Enums: `enum_<name>.py`
- Utils: `util_<name>.py`

**Classes**:
- Nodes: `Node<Name><Type>` (e.g., `NodeComputeService`)
- Models: `Model<Name>` (e.g., `ModelEventEnvelope`)
- Enums: `Enum<Name>` (e.g., `EnumNodeType`)

**Methods**:
- Use `snake_case` for all methods and functions
- Use descriptive names that explain intent

### Code Quality Standards

1. **Type Annotations**: All functions must have type hints
   ```python
   def process_data(input_data: dict, config: ModelConfig) -> dict:
       pass
   ```

2. **Pydantic Models**: Use Pydantic for all data models
   ```python
   class ModelMyData(BaseModel):
       field: str
       value: int = Field(ge=0)
   ```

3. **Error Handling**: Use OnexError with proper error codes
   ```python
   raise OnexError(
       message="Operation failed",
       error_code=EnumErrorCode.OPERATION_FAILED
   )
   ```

4. **Documentation**: All public APIs must have docstrings
   ```python
   def my_function(data: dict) -> dict:
       """
       Process input data and return result.

       Args:
           data: Input data dictionary

       Returns:
           Processed result dictionary
       """
       pass
   ```

## Testing Requirements

### Test Coverage

- **Minimum**: 80% code coverage
- **Target**: 90% code coverage
- **Critical paths**: 100% coverage

### Writing Tests

```python
import pytest

@pytest.mark.asyncio
async def test_my_node():
    # Arrange
    container = create_test_container()
    node = MyNode(container)

    # Act
    result = await node.process({"value": 42})

    # Assert
    assert result["output"] == 84
```

### Running Tests

```bash
# Run all tests
poetry run pytest tests/

# Run with coverage
poetry run pytest tests/ --cov=src --cov-report=html

# Run specific test
poetry run pytest tests/unit/test_my_node.py -v
```

## Documentation

### Documentation Standards

1. **Docstrings**: All public APIs
2. **Type hints**: All function signatures
3. **Examples**: Include usage examples
4. **Updates**: Update docs with code changes

### Adding Documentation

- Place tutorials in `docs/guides/`
- Place API docs in `docs/reference/api/`
- Place architecture docs in `docs/architecture/`
- Follow existing documentation structure

## Pull Request Process

### 1. Create a Branch

```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Or fix branch
git checkout -b fix/bug-description
```

### 2. Make Changes

- Follow code standards
- Add tests
- Update documentation
- Keep commits focused and atomic

### 3. Test Everything

```bash
# Run all quality checks
poetry run pytest tests/
poetry run mypy src/
poetry run ruff check src/
poetry run black src/ --check
poetry run isort src/ --check
```

### 4. Commit Changes

```bash
# Use semantic commit messages
git commit -m "feat: add new COMPUTE node pattern"
git commit -m "fix: resolve cache invalidation bug"
git commit -m "docs: update REDUCER tutorial"
```

**Commit Types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Build process or auxiliary tool changes

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-new-feature

# Create pull request on GitHub
```

### 6. PR Requirements

Your PR must:

- ✅ Pass all CI checks
- ✅ Include tests for new code
- ✅ Update relevant documentation
- ✅ Follow code standards
- ✅ Have a clear description

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed code
- [ ] Documented changes
- [ ] No breaking changes (or documented)
```

## Code of Conduct

### Our Standards

- **Be respectful** - Treat everyone with respect
- **Be collaborative** - Work together effectively
- **Be professional** - Maintain professionalism
- **Be inclusive** - Welcome diverse perspectives

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or inflammatory comments
- Personal attacks
- Unprofessional conduct

## Getting Help

### Resources

- [Documentation](docs/INDEX.md)
- [Node Building Guide](docs/guides/node-building/README.md)
- [GitHub Issues](https://github.com/OWNER/omnibase_core/issues)

### Questions

- **General questions**: Open a GitHub discussion
- **Bug reports**: Open a GitHub issue
- **Feature requests**: Open a GitHub issue with "enhancement" label

## License

By contributing to omnibase_core, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing to omnibase_core!** 🎉

Your contributions help make ONEX better for everyone.
