# CLAUDE.md - Omnibase Core Project Instructions

## Python Development - ALWAYS USE POETRY

**CRITICAL**: This project uses Poetry for all Python package management and task execution.

### Required Patterns:

✅ **CORRECT - Always use Poetry:**
```bash
poetry run pytest tests/unit/
poetry run mypy src/omnibase_core/
poetry run python -m module.name
poetry install
poetry add package-name
poetry run black src/
poetry run isort src/
```

❌ **WRONG - Never use pip or python directly:**
```bash
python -m pip install -e .          # NEVER
pip install package                 # NEVER
python -m pytest tests/             # NEVER
python script.py                    # NEVER
```

### Why Poetry?

1. **Dependency Isolation**: Poetry manages virtualenvs automatically
2. **Lock File**: Ensures reproducible builds across environments
3. **Project Consistency**: All developers and CI use same environment
4. **ONEX Standards**: Poetry is the mandated tool for all ONEX projects

### Agent Instructions

When spawning polymorphic agents:
- **ALWAYS** instruct them to use `poetry run` for Python commands
- **NEVER** allow direct pip or python execution
- Include explicit examples showing Poetry usage

### Testing Commands

```bash
# Run all tests
poetry run pytest tests/

# Run specific test file
poetry run pytest tests/unit/exceptions/test_onex_error.py -v

# Run with coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing

# Run specific test class
poetry run pytest tests/unit/exceptions/test_onex_error.py::TestOnexErrorEdgeCases -xvs
```

### Code Quality Commands

```bash
# Type checking
poetry run mypy src/omnibase_core/

# Formatting
poetry run black src/ tests/

# Import sorting
poetry run isort src/ tests/

# All pre-commit hooks
pre-commit run --all-files
```

---

**Remember**: If you're running Python code in this project, it goes through Poetry. No exceptions.
