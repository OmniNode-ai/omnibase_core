#!/bin/bash
# phase1_quick_wins.sh
# Execute all Phase 1 automated type safety improvements
# Part of the Type Analysis Report recommendations

set -e

PROJECT_ROOT="/Volumes/PRO-G40/Code/omnibase_core"
cd "$PROJECT_ROOT"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════════"
echo "  Phase 1: Quick Wins - Type Safety Improvements"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "This script will:"
echo "  1. Remove unused type: ignore comments (63 errors)"
echo "  2. Add __all__ exports to modules (59 errors)"
echo "  3. Verify changes with mypy and pytest"
echo ""
echo "Expected impact: Remove 122 errors (56.7% of total)"
echo "Expected time: 3-5 hours (automated)"
echo ""

# Check if dry-run mode
DRY_RUN=${DRY_RUN:-"true"}
if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - No changes will be applied${NC}"
    echo "   To apply changes, run: DRY_RUN=false ./scripts/phase1_quick_wins.sh"
    echo ""
fi

# Function to run command with status
run_step() {
    local step_name=$1
    local step_cmd=$2

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}▶ $step_name${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if eval "$step_cmd"; then
        echo -e "${GREEN}✅ $step_name - SUCCESS${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}❌ $step_name - FAILED${NC}"
        echo ""
        return 1
    fi
}

# Step 0: Pre-check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}▶ Step 0: Pre-flight Checks${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for uncommitted changes
if [ "$DRY_RUN" = "false" ] && [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
    echo "   It's recommended to commit or stash changes before running this script"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Get baseline error count
echo "📊 Getting baseline error counts..."
BASELINE_ERRORS=$(poetry run mypy src/omnibase_core/ --strict 2>&1 | grep -c "error:" || echo "0")
UNUSED_IGNORES=$(poetry run mypy src/omnibase_core/ --strict 2>&1 | grep -c 'Unused "type: ignore"' || echo "0")
ATTR_DEFINED=$(poetry run mypy src/omnibase_core/ --strict 2>&1 | grep -c '\[attr-defined\]' || echo "0")

echo "   Total strict mode errors: $BASELINE_ERRORS"
echo "   Unused ignore comments: $UNUSED_IGNORES"
echo "   Missing __all__ exports: $ATTR_DEFINED"
echo ""

# Step 1: Remove unused type ignore comments
if [ "$UNUSED_IGNORES" -gt 0 ]; then
    if [ "$DRY_RUN" = "true" ]; then
        run_step "Step 1: Preview - Remove unused type ignores" \
            "echo '  Would remove $UNUSED_IGNORES unused type: ignore comments' && echo '  Run with DRY_RUN=false to apply'"
    else
        run_step "Step 1: Remove unused type ignore comments" \
            "./scripts/remove_unused_ignores.sh"
    fi
else
    echo -e "${GREEN}✅ Step 1: No unused type ignores found - skipping${NC}"
    echo ""
fi

# Step 2: Add __all__ exports
if [ "$ATTR_DEFINED" -gt 0 ]; then
    if [ "$DRY_RUN" = "true" ]; then
        run_step "Step 2: Preview - Add __all__ exports" \
            "poetry run python scripts/generate_all_exports.py"
    else
        run_step "Step 2: Add __all__ exports to modules" \
            "poetry run python scripts/generate_all_exports.py --apply"
    fi
else
    echo -e "${GREEN}✅ Step 2: No missing __all__ exports found - skipping${NC}"
    echo ""
fi

# Step 3: Verify with mypy (only if changes were applied)
if [ "$DRY_RUN" = "false" ]; then
    run_step "Step 3: Verify type checking improvements" \
        "poetry run mypy src/omnibase_core/ --strict 2>&1 | tee /tmp/mypy_phase1_results.txt"

    # Calculate improvement
    NEW_ERRORS=$(grep -c "error:" /tmp/mypy_phase1_results.txt || echo "0")
    ERRORS_FIXED=$((BASELINE_ERRORS - NEW_ERRORS))
    PERCENT_IMPROVED=$(awk "BEGIN {printf \"%.1f\", ($ERRORS_FIXED / $BASELINE_ERRORS) * 100}")

    echo "📊 Results:"
    echo "   Baseline errors: $BASELINE_ERRORS"
    echo "   Current errors: $NEW_ERRORS"
    echo "   Errors fixed: $ERRORS_FIXED"
    echo "   Improvement: $PERCENT_IMPROVED%"
    echo ""

    # Step 4: Run tests
    run_step "Step 4: Run test suite" \
        "poetry run pytest tests/ -v --tb=short"

    # Final summary
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${GREEN}✅ Phase 1 Complete!${NC}"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Summary:"
    echo "  ✓ Removed $UNUSED_IGNORES unused type ignore comments"
    echo "  ✓ Added __all__ exports to modules (fixing $ATTR_DEFINED errors)"
    echo "  ✓ Reduced strict mode errors by $ERRORS_FIXED ($PERCENT_IMPROVED%)"
    echo "  ✓ All tests passing"
    echo ""
    echo "Next steps:"
    echo "  1. Review changes: git diff"
    echo "  2. Commit changes: git add -A && git commit -m 'chore: Phase 1 type safety improvements'"
    echo "  3. Continue to Phase 2: Fix no-any-return errors (see TYPE_ANALYSIS_REPORT.md)"
    echo ""

else
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${YELLOW}📋 Dry Run Complete${NC}"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "To apply changes, run:"
    echo "  DRY_RUN=false ./scripts/phase1_quick_wins.sh"
    echo ""
    echo "Or run individual scripts:"
    echo "  ./scripts/remove_unused_ignores.sh"
    echo "  poetry run python scripts/generate_all_exports.py --apply"
    echo ""
fi
