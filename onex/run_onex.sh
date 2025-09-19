#!/usr/bin/env bash
set -euo pipefail

# ONEX Orchestrator Script
# Main entry point for running ONEX reviews

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
CONFIG_DIR="$SCRIPT_DIR/configs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_usage {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  baseline    - Run baseline analysis on current repository"
    echo "  nightly     - Run nightly incremental review"
    echo "  status      - Show ONEX status and last run info"
    echo "  clean       - Clean temporary files and caches"
    echo ""
    echo "Options:"
    echo "  --policy <file>  - Use custom policy file (default: onex/configs/policy.yaml)"
    echo "  --output <dir>   - Custom output directory"
    echo "  --verbose        - Enable verbose output"
    echo ""
    echo "Examples:"
    echo "  $0 baseline"
    echo "  $0 nightly --verbose"
    echo "  $0 status"
}

function run_baseline {
    echo -e "${BLUE}=== Running ONEX Baseline Analysis ===${NC}"
    echo ""

    # Run baseline producer
    echo -e "${YELLOW}Step 1: Generating baseline data...${NC}"
    "$SCRIPTS_DIR/baseline_producer.sh"

    # Find latest baseline directory
    BASELINE_DIR=$(find .onex_baseline -type d -name "[0-9]*" | sort -r | head -n1)

    if [[ -z "$BASELINE_DIR" ]]; then
        echo -e "${RED}Error: No baseline data found${NC}"
        exit 1
    fi

    echo ""
    echo -e "${YELLOW}Step 2: Running ONEX reviewer...${NC}"
    python3 "$SCRIPTS_DIR/onex_reviewer.py" baseline "$BASELINE_DIR" "$CONFIG_DIR/policy.yaml"

    echo ""
    echo -e "${GREEN}✓ Baseline analysis complete${NC}"
    echo -e "Results: ${BASELINE_DIR}/outputs/"
}

function run_nightly {
    echo -e "${BLUE}=== Running ONEX Nightly Review ===${NC}"
    echo ""

    # Run nightly producer
    echo -e "${YELLOW}Step 1: Generating nightly data...${NC}"
    "$SCRIPTS_DIR/nightly_producer.sh"

    # Find latest nightly directory
    NIGHTLY_DIR=$(find .onex_nightly/runs -type d -name "[0-9]*" 2>/dev/null | sort -r | head -n1)

    if [[ -z "$NIGHTLY_DIR" ]]; then
        echo -e "${YELLOW}No changes detected or first run${NC}"
        echo "Run 'baseline' command first to initialize"
        exit 0
    fi

    echo ""
    echo -e "${YELLOW}Step 2: Running ONEX reviewer...${NC}"
    python3 "$SCRIPTS_DIR/onex_reviewer.py" nightly "$NIGHTLY_DIR" "$CONFIG_DIR/policy.yaml"

    echo ""
    echo -e "${GREEN}✓ Nightly review complete${NC}"
    echo -e "Results: ${NIGHTLY_DIR}/outputs/"
}

function show_status {
    echo -e "${BLUE}=== ONEX Status ===${NC}"
    echo ""

    # Check baseline status
    if [[ -d ".onex_baseline" ]]; then
        BASELINE_COUNT=$(find .onex_baseline -type d -name "[0-9]*" | wc -l)
        LATEST_BASELINE=$(find .onex_baseline -type d -name "[0-9]*" | sort -r | head -n1)
        echo -e "${GREEN}Baseline:${NC}"
        echo "  Runs: $BASELINE_COUNT"
        if [[ -n "$LATEST_BASELINE" ]]; then
            echo "  Latest: $(basename $(dirname "$LATEST_BASELINE"))/$(basename "$LATEST_BASELINE")"
        fi
    else
        echo -e "${YELLOW}Baseline: Not initialized${NC}"
    fi

    echo ""

    # Check nightly status
    if [[ -f ".onex_nightly/last_successful_sha" ]]; then
        LAST_SHA=$(cat .onex_nightly/last_successful_sha)
        CURRENT_SHA=$(git rev-parse HEAD)
        echo -e "${GREEN}Nightly:${NC}"
        echo "  Last SHA: ${LAST_SHA:0:8}"
        echo "  Current SHA: ${CURRENT_SHA:0:8}"

        if [[ "$LAST_SHA" == "$CURRENT_SHA" ]]; then
            echo "  Status: Up to date"
        else
            echo "  Status: Changes pending review"
        fi

        if [[ -d ".onex_nightly/runs" ]]; then
            RUN_COUNT=$(find .onex_nightly/runs -type d -name "[0-9]*" | wc -l)
            echo "  Runs: $RUN_COUNT"
        fi
    else
        echo -e "${YELLOW}Nightly: Not initialized${NC}"
    fi

    echo ""

    # Check policy
    if [[ -f "$CONFIG_DIR/policy.yaml" ]]; then
        echo -e "${GREEN}Policy:${NC} $CONFIG_DIR/policy.yaml"
        RULE_COUNT=$(grep -c "ONEX\." "$SCRIPTS_DIR/onex_reviewer.py" || true)
        echo "  Active rules: ~$((RULE_COUNT / 2))"
    else
        echo -e "${RED}Policy: Not found${NC}"
    fi
}

function clean_cache {
    echo -e "${BLUE}=== Cleaning ONEX Cache ===${NC}"
    echo ""

    # Confirm before cleaning
    read -p "Remove all ONEX data? This cannot be undone. (y/N): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .onex_baseline .onex_nightly
        echo -e "${GREEN}✓ Cache cleaned${NC}"
    else
        echo "Cancelled"
    fi
}

# Main script logic
if [[ $# -lt 1 ]]; then
    print_usage
    exit 1
fi

COMMAND=$1
shift

# Parse options
POLICY_FILE="$CONFIG_DIR/policy.yaml"
OUTPUT_DIR=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --policy)
            POLICY_FILE="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    baseline)
        run_baseline
        ;;
    nightly)
        run_nightly
        ;;
    status)
        show_status
        ;;
    clean)
        clean_cache
        ;;
    *)
        echo "Unknown command: $COMMAND"
        print_usage
        exit 1
        ;;
esac