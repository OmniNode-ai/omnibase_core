# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# Makefile for omnibase_core
#
# Targets match CI exactly (see .github/workflows/test.yml).
# All Python commands use `uv run` — never direct python/pip.

.DEFAULT_GOAL := help
.PHONY: help install format lint lint-fix typecheck test test-cov ci-fast

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

## install: Install all dependencies (uv sync --all-extras)
install:
	uv sync --all-extras

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

## format: Auto-fix formatting with ruff (modifies files)
format:
	uv run ruff format src/ tests/

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

## lint: Check formatting and linting without modifying files (CI: lint + mypy)
lint:
	uv run ruff format --check src/ tests/
	uv run ruff check src/ tests/
	uv run mypy src/omnibase_core

## lint-fix: Auto-fix ruff lint violations (modifies files)
lint-fix:
	uv run ruff check --fix src/ tests/

# ---------------------------------------------------------------------------
# Type Checking
# ---------------------------------------------------------------------------

## typecheck: Run mypy + pyright strict type checks (matches CI)
typecheck:
	uv run mypy src/omnibase_core
	uv run pyright src/omnibase_core

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

## test: Run full test suite
test:
	uv run pytest tests/

## test-cov: Run full test suite with coverage report
test-cov:
	uv run pytest tests/ --cov

# ---------------------------------------------------------------------------
# CI Fast (Phase 1 quality checks — matches CI quality-gate)
# ---------------------------------------------------------------------------

## ci-fast: Run all Phase 1 CI quality checks locally (matches quality-gate)
ci-fast:
	uv run ruff format --check src/ tests/
	uv run ruff check src/ tests/
	uv run mypy src/omnibase_core
	uv run pyright src/omnibase_core
	uv run python scripts/validation/validate-all-exports.py
	uv run python scripts/validation/validate-doc-links.py --fix-case
	uv run python -m omnibase_core.validation.checker_enum_governance src/omnibase_core/
	uv run mypy --strict \
		scripts/validation/validate-no-direct-io.py \
		scripts/validation/validate-all-exports.py \
		scripts/validation/validate-no-infra-imports.py \
		scripts/check_transport_imports.py
	uv run python scripts/check_transport_imports.py --changed-files --verbose
	./scripts/validate-no-transport-imports.sh
	uv run python scripts/check_node_purity.py --verbose || true  # non-blocking (CI continue-on-error)
	git ls-files -z | xargs -0 detect-secrets-hook \
		--baseline .secrets.baseline \
		--exclude-files 'uv\.lock' \
		--exclude-files '\.venv/' \
		--exclude-files 'tests/fixtures/' \
		--exclude-files '\.git/' \
		--exclude-files '\.secrets\.baseline' \
		--exclude-files '\.github/workflows/.*\.yml'  # requires: pip install detect-secrets

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

## help: Show this help message
help:
	@echo "omnibase_core — available targets:"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## /  /'
	@echo ""
	@echo "Run 'make <target>' to execute a target."
