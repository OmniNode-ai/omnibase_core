#!/bin/bash
# Run tests in 20 splits with coverage, then combine results
# IMPORTANT: This script adds resource constraints for local execution
# CI runs 20 splits on separate isolated runners (no resource limits needed)
# Local runs 20 splits on one machine (needs concurrency + worker limits)
#
# PORTABILITY:
#   This script auto-detects the source directory from the project structure.
#   Override with ONEX_SRC_DIR environment variable:
#     ONEX_SRC_DIR="src/my_package" ./scripts/run-coverage-parallel.sh
#
# USAGE:
#   ./scripts/run-coverage-parallel.sh           # Auto-detect package
#   ONEX_SRC_DIR="lib/custom" ./scripts/run-coverage-parallel.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get project root (script can run from anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Auto-detect source directory if not set, with validation
if [ -n "${ONEX_SRC_DIR:-}" ]; then
    # ONEX_SRC_DIR was provided externally - validate it exists
    if [ ! -d "$PROJECT_ROOT/$ONEX_SRC_DIR" ]; then
        echo -e "${RED}ERROR: ONEX_SRC_DIR '$ONEX_SRC_DIR' does not exist at '$PROJECT_ROOT/$ONEX_SRC_DIR'${NC}"
        exit 1
    fi
else
    # Standard ONEX layout: src/<package_name>/
    if [ -d "$PROJECT_ROOT/src" ]; then
        # Count packages under src/ (excluding src itself, __pycache__, and hidden dirs)
        PACKAGE_COUNT=$(find "$PROJECT_ROOT/src" -maxdepth 1 -type d ! -name "src" ! -name "__pycache__" ! -name ".*" | wc -l | tr -d ' ')

        if [ "$PACKAGE_COUNT" -gt 1 ]; then
            echo -e "${YELLOW}WARNING: Multiple packages found under src/ ($PACKAGE_COUNT). Using first one. Set ONEX_SRC_DIR explicitly for specific package.${NC}"
        fi

        PACKAGE_DIR=$(find "$PROJECT_ROOT/src" -maxdepth 1 -type d ! -name "src" ! -name "__pycache__" ! -name ".*" | head -1)
        if [ -n "$PACKAGE_DIR" ]; then
            ONEX_SRC_DIR="src/$(basename "$PACKAGE_DIR")"
        else
            echo -e "${RED}ERROR: No package directory found under src/${NC}"
            exit 1
        fi
    else
        echo -e "${RED}ERROR: No src/ directory found${NC}"
        exit 1
    fi
fi

# Resource configuration for local execution
# ============================================
# MAX_CONCURRENT_SPLITS: How many splits run simultaneously (default: 3)
#   - Too high = resource exhaustion, OOM, system freeze
#   - Too low = slower execution, underutilized CPU
#   - Recommended: 2-4 for most machines (8-12 cores)
MAX_CONCURRENT_SPLITS=${MAX_CONCURRENT_SPLITS:-3}

# WORKERS_PER_SPLIT: pytest-xdist workers per split (default: 4)
#   - Total workers = MAX_CONCURRENT_SPLITS × WORKERS_PER_SPLIT
#   - Example: 3 splits × 4 workers = 12 total workers
#   - Recommended: 2-4 workers per split
WORKERS_PER_SPLIT=${WORKERS_PER_SPLIT:-4}

# MAX_FAILURES: Stop testing after N failures (default: 10)
#   - Fail fast on critical issues
#   - Saves resources and time
MAX_FAILURES=${MAX_FAILURES:-10}

echo -e "${BLUE}🧪 Running parallel coverage tests (20 splits)${NC}"
echo -e "${BLUE}📊 Configuration:${NC}"
echo -e "   • Source directory: ${ONEX_SRC_DIR}"
echo -e "   • Concurrent splits: ${MAX_CONCURRENT_SPLITS}"
echo -e "   • Workers per split: ${WORKERS_PER_SPLIT}"
echo -e "   • Total concurrent workers: $((MAX_CONCURRENT_SPLITS * WORKERS_PER_SPLIT))"
echo -e "   • Max failures before abort: ${MAX_FAILURES}"
echo ""

# Detect CPU count and warn if configuration is too aggressive (skip in CI)
# CI environments: GitHub Actions (CI=true), GitLab CI (CI=true), etc.
if [ -z "${CI:-}" ]; then
  CPU_COUNT=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo "unknown")
  TOTAL_WORKERS=$((MAX_CONCURRENT_SPLITS * WORKERS_PER_SPLIT))
  if [[ "$CPU_COUNT" != "unknown" ]] && [[ $TOTAL_WORKERS -gt $((CPU_COUNT * 2)) ]]; then
    echo -e "${YELLOW}⚠️  WARNING: Total workers ($TOTAL_WORKERS) exceeds 2× CPU cores ($CPU_COUNT)${NC}"
    echo -e "${YELLOW}   This may cause resource exhaustion. Consider reducing:${NC}"
    echo -e "${YELLOW}   export MAX_CONCURRENT_SPLITS=2${NC}"
    echo -e "${YELLOW}   export WORKERS_PER_SPLIT=4${NC}"
    echo ""
  fi
fi

# Clean previous coverage data
echo "🧹 Cleaning previous coverage data..."
rm -f .coverage .coverage.*

# Track start time
START_TIME=$(date +%s)

# Run splits with concurrency limit using job control
# ====================================================
# Strategy: Launch splits in batches of MAX_CONCURRENT_SPLITS
# Wait for batch completion before launching next batch
# This prevents resource exhaustion from running all 12 splits simultaneously
echo -e "${YELLOW}🚀 Launching test splits (batches of ${MAX_CONCURRENT_SPLITS})...${NC}"

# Function to run a single split
run_split() {
  local split_num=$1
  echo "[Split $split_num/20] Starting..."
  COVERAGE_FILE=.coverage.$split_num poetry run pytest tests/ \
    --splits 20 \
    --group $split_num \
    --cov="$ONEX_SRC_DIR" \
    --cov-report= \
    -n $WORKERS_PER_SPLIT \
    --maxfail=$MAX_FAILURES \
    --tb=short \
    -q 2>&1 | sed "s/^/[Split $split_num] /"
  local exit_code=$?
  if [ $exit_code -eq 0 ]; then
    echo "[Split $split_num/20] ✓ Complete"
  else
    echo -e "${RED}[Split $split_num/20] ✗ Failed (exit code: $exit_code)${NC}"
  fi
  return $exit_code
}

# Launch splits in controlled batches
# Track PIDs for bash 3.2 compatibility (macOS default)
split_pids=()
failed_splits=0

for i in {1..20}; do
  # Launch split in background
  run_split $i &
  split_pids+=($!)

  # Wait if we've reached max concurrent splits
  if [[ ${#split_pids[@]} -ge $MAX_CONCURRENT_SPLITS ]]; then
    # Wait for first background job in batch
    wait ${split_pids[0]}
    job_exit=$?
    if [[ $job_exit -ne 0 ]]; then
      ((failed_splits++))
    fi
    # Remove completed job from array
    split_pids=("${split_pids[@]:1}")
  fi
done

# Wait for remaining background jobs
echo "⏳ Waiting for remaining splits to complete..."
for pid in "${split_pids[@]}"; do
  wait $pid
  job_exit=$?
  if [[ $job_exit -ne 0 ]]; then
    ((failed_splits++))
  fi
done

# Check for failures
if [[ $failed_splits -gt 0 ]]; then
  echo -e "${RED}❌ $failed_splits split(s) failed${NC}"
  exit 1
fi

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo -e "${GREEN}✅ All splits complete in ${MINUTES}m ${SECONDS}s${NC}"

# Combine coverage data
echo -e "${BLUE}🔗 Combining coverage data from all splits...${NC}"
poetry run coverage combine

# Generate reports
echo -e "${BLUE}📊 Generating coverage reports...${NC}"
echo ""
poetry run coverage report --fail-under=60
echo ""

# Generate HTML report
poetry run coverage html

echo ""
echo -e "${GREEN}✅ Coverage report complete!${NC}"
echo -e "${BLUE}📂 HTML report: htmlcov/index.html${NC}"
echo -e "${BLUE}🌐 Open with: open htmlcov/index.html${NC}"
echo ""
echo -e "${YELLOW}⏱️  Total time: ${MINUTES}m ${SECONDS}s${NC}"
