#!/bin/bash
# Verification script for async cleanup fix

echo "=== Async Cleanup Fix Verification ==="
echo ""
echo "Running full service test suite..."
echo ""

# Run tests and capture results
poetry run pytest tests/unit/models/nodes/services/ -v 2>&1 > /tmp/test_results.txt

# Extract key metrics
TOTAL_TESTS=$(grep -c "PASSED\|FAILED" /tmp/test_results.txt)
PASSED_TESTS=$(grep -c "PASSED" /tmp/test_results.txt)
FAILED_TESTS=$(grep -c "FAILED" /tmp/test_results.txt)
TASK_WARNINGS=$(grep -c "Task was destroyed" /tmp/test_results.txt)

echo "📊 Test Results:"
echo "   Total Tests: $TOTAL_TESTS"
echo "   ✅ Passed: $PASSED_TESTS"
echo "   ❌ Failed: $FAILED_TESTS"
echo ""
echo "⚠️  Task Cleanup Warnings: $TASK_WARNINGS"
echo ""

if [ $TASK_WARNINGS -lt 10 ]; then
    echo "✅ SUCCESS: Task warnings reduced to acceptable level ($TASK_WARNINGS < 10)"
else
    echo "⚠️  WARNING: More task warnings than expected ($TASK_WARNINGS >= 10)"
fi

echo ""
echo "=== Running Specific Lifecycle Tests ==="
poetry run pytest tests/unit/models/nodes/services/test_model_service_effect_lifecycle.py -v --tb=no | tail -3
