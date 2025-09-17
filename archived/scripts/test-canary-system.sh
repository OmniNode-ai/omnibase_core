#!/bin/bash

# Canary System Integration Test Runner
#
# This script runs comprehensive integration tests for the canary system
# and can be executed repeatedly to verify system functionality.

set -e

echo "🧪 Running Canary System Integration Tests"
echo "========================================="

# Set up environment
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)/src"

# Ensure we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Error: Must be run from project root directory"
    exit 1
fi

# Check if pytest is available
if ! command -v poetry &> /dev/null; then
    echo "❌ Error: Poetry not found. Please install poetry first."
    exit 1
fi

# Install dependencies if needed
echo "📦 Ensuring dependencies are installed..."
poetry install --no-dev

# Run the integration tests
echo "🚀 Running canary system integration tests..."
poetry run pytest tests/integration/test_canary_system_integration.py -v --tb=short --color=yes

# Check exit code
if [[ $? -eq 0 ]]; then
    echo ""
    echo "✅ All canary system integration tests passed!"
    echo "🎯 The canary system is working correctly."
else
    echo ""
    echo "❌ Some tests failed. Check the output above for details."
    exit 1
fi
