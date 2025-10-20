#!/bin/bash
# Full suite with parallelization (2-3min)
# Runs all tests in parallel using all CPU cores
set -e

echo "🎯 Running full test suite..."
poetry run pytest tests/ \
  -n auto \
  --tb=short \
  "$@"
