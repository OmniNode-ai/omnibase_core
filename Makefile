# SPDX-FileCopyrightText: 2025-2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# Makefile for omnibase_core
#
# Targets match CI exactly (see .github/workflows/test.yml) with intentional
# differences documented below:
# 1. `uv run python` is used here for consistency; CI invokes `python3` directly
#    (e.g. validate-doc-links.py). This is a potential correctness risk: `python3`
#    and `uv run python` may resolve to different interpreter versions or site-packages
#    depending on the host environment — not merely a style difference.
#    TODO(OMN-2335): align CI to use uv run python for consistency
# 2. transport import check always runs full scan here; CI uses --changed-files on
#    feature branches (conservative local default catches more violations pre-push).
# 3. `enum-governance` runs as a separate parallel CI job in test.yml but is included
#    sequentially here in ci-fast (via `uv run python -m omnibase_core.validation.checker_enum_governance`).
# All Python commands use `uv run` — never direct python/pip.
# `detect-secrets` is installed via `make install` as a one-time setup step.

.DEFAULT_GOAL := help
.PHONY: help install format lint lint-fix typecheck test test-cov ci-fast

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

## install: Install all dependencies and dev tools (uv sync --all-extras)
install:
	uv sync --all-extras
	uv tool install detect-secrets==1.5.0 --quiet --force
	chmod +x scripts/validate-no-transport-imports.sh

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

## format: Auto-fix formatting with ruff (modifies files)
format:
	uv run ruff format src/ tests/

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

## lint: Check formatting and linting without modifying files (runs mypy only, not pyright; use ci-fast for full type gate with pyright coverage)
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
	@command -v detect-secrets-hook >/dev/null 2>&1 || (echo "ERROR: detect-secrets not installed. Run 'make install' first." && exit 1)
	@detect-secrets-hook --version 2>&1 | grep -q "1\.5\.0" || (echo "WARNING: detect-secrets version mismatch — expected 1.5.0. Run 'make install' to reinstall." && exit 1)
	uv run ruff format --check src/ tests/
	uv run ruff check src/ tests/
	uv run mypy src/omnibase_core
	uv run pyright src/omnibase_core
	uv run python scripts/validation/validate-all-exports.py
	uv run python scripts/validation/validate-doc-links.py --fix-case  # intentionally mutates: auto-repairs casing in docs/; CI runs equivalent step with python3
	@if ! git diff --quiet docs/ 2>/dev/null; then \
		echo "validate-doc-links: WARNING — --fix-case mutated files in docs/. Review uncommitted changes with 'git diff docs/'."; \
	fi
	uv run python -m omnibase_core.validation.checker_enum_governance src/omnibase_core/
	uv run mypy --strict \
		scripts/validation/validate-no-direct-io.py \
		scripts/validation/validate-all-exports.py \
		scripts/validation/validate-no-infra-imports.py \
		scripts/check_transport_imports.py
	uv run python scripts/check_transport_imports.py --verbose  # full scan: CI runs full scan on main/develop; --changed-files would miss violations on unchanged files
	@test -x scripts/validate-no-transport-imports.sh || (echo "ERROR: scripts/validate-no-transport-imports.sh is not executable. Fix: chmod +x scripts/validate-no-transport-imports.sh (or run 'make install' for full setup)." && exit 1)
	./scripts/validate-no-transport-imports.sh
	@uv run python scripts/check_node_purity.py --verbose; \
		_purity_exit=$$?; \
		if [ $$_purity_exit -ne 0 ]; then \
			echo "node-purity-check: FAILED (non-blocking, see CI for details)"; \
		else \
			echo "node-purity-check: PASSED"; \
		fi; \
		exit 0  # always succeed — non-blocking: matches CI continue-on-error
	@# set +e: capture detect-secrets exit code without failing the recipe; scoped to this @-block
	@set +e; \
	git ls-files -z | xargs -0 uv run detect-secrets-hook \
		--baseline .secrets.baseline \
		--exclude-files 'uv\.lock' \
		--exclude-files '\.venv/' \
		--exclude-files 'tests/fixtures/' \
		--exclude-files '\.git/' \
		--exclude-files '\.secrets\.baseline' \
		--exclude-files '\.github/workflows/.*\.yml'; \
	_secrets_exit=$$?; \
	set -e; \
	if [ $$_secrets_exit -ne 0 ]; then \
		echo "detect-secrets: FAILED (exit code: $$_secrets_exit) — possible secrets detected or scan error. Review .secrets.baseline and remediate before merging."; \
		exit $$_secrets_exit; \
	fi

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
