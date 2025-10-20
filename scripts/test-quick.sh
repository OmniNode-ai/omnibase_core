#!/bin/bash
# Quick feedback - only affected tests (5-30s)
# Uses pytest-testmon to run only tests affected by code changes
set -e

echo "🚀 Running affected tests with pytest-testmon..."
poetry run pytest \
  --testmon \
  --testmon-noselect \
  -n auto \
  --maxfail=5 \
  -x \
  --tb=short \
  "$@"
