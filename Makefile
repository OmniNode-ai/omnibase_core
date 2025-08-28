.PHONY: help install install-dev test lint format type-check clean build pre-commit-install pre-commit-run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -e .

install-dev: ## Install with development dependencies
	pip install -e .[dev]
	pip install pre-commit

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files

test: ## Run tests
	pytest tests/

lint: ## Run linting
	ruff check src/ tests/

format: ## Format code
	black src/ tests/
	isort src/ tests/

type-check: ## Run type checking
	mypy src/

quality: lint type-check ## Run all quality checks

fix: ## Fix code issues
	ruff check --fix src/ tests/
	black src/ tests/
	isort src/ tests/

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build package
	python -m build

setup-dev: ## Setup development environment
	python -m venv venv
	@echo "Run 'source venv/bin/activate' then 'make install-dev && make pre-commit-install'"