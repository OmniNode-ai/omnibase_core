#!/bin/bash
# Unit tests only (15-30s)
# Runs all unit tests in parallel
set -e

echo "🧪 Running unit tests..."
poetry run pytest tests/unit/ \
  -n auto \
  --maxfail=10 \
  -x \
  --tb=short \
  "$@"
