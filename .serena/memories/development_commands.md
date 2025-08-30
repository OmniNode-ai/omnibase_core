# Development Commands for ONEX Core

## Environment Setup
```bash
# Setup development environment
make setup-dev
source venv/bin/activate
make install-dev
make pre-commit-install
```

## Code Quality Commands
```bash
# Run all quality checks
make quality

# Individual quality checks
make lint          # Run ruff linting
make type-check    # Run mypy type checking
make format        # Format with black and isort

# Fix code issues automatically
make fix           # Fix linting issues and format code
```

## Testing Commands
```bash
# Run tests
make test          # Run pytest tests
pytest tests/      # Direct pytest execution
```

## Pre-commit Commands
```bash
# Install pre-commit hooks
make pre-commit-install

# Run pre-commit on all files
make pre-commit-run
```

## Build and Package Commands
```bash
# Build package
make build         # Clean and build package

# Clean artifacts
make clean         # Remove build artifacts and cache
```

## Development Workflow
1. **Setup**: `make setup-dev && source venv/bin/activate`
2. **Install**: `make install-dev && make pre-commit-install`
3. **Development**: Write code, run `make quality` and `make test`
4. **Pre-commit**: `make pre-commit-run` before committing
5. **Build**: `make build` for packaging

## Project Structure Commands
- Use `poetry` for dependency management
- Follow `ruff` linting rules (comprehensive ruleset)
- Use `black` and `isort` for formatting
- Run `mypy` for type checking
- Use `pytest` with asyncio mode for testing