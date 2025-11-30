#!/usr/bin/env bash
#
# validate-no-model-primitive-unions.sh
# Pre-commit hook to prevent Union types mixing models and primitives
#
# ONEX Phase 0 Pattern: Strongly-typed models only, no primitive fallbacks
# Pydantic Union types like `list[Model] | list[str]` cause validation
# confusion in parallel execution (pytest-xdist race conditions)
#
# Example violations:
#   ❌ dependencies: list[ModelDep] | list[str]  # Union confusion
#   ✅ dependencies: list[ModelDep]              # Strongly typed
#
# Exit codes:
#   0 - No violations found
#   1 - Violations found
#
# PORTABILITY:
#   This script auto-detects the source directory from the project structure.
#   It works with any ONEX repository that follows the standard layout:
#     project_root/
#       src/
#         <package_name>/
#           ...
#
#   Override the source directory with ONEX_SRC_DIR environment variable:
#     ONEX_SRC_DIR="src/my_package" ./scripts/validate-no-model-primitive-unions.sh
#
# USAGE:
#   ./scripts/validate-no-model-primitive-unions.sh           # Auto-detect
#   ONEX_SRC_DIR="src/custom" ./scripts/validate-no-model-primitive-unions.sh
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get project root (script can run from anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Auto-detect source directory if not set
if [ -z "${ONEX_SRC_DIR:-}" ]; then
    # Standard ONEX layout: src/<package_name>/
    if [ -d "$PROJECT_ROOT/src" ]; then
        # Find the first directory under src/ (excluding __pycache__, hidden dirs)
        PACKAGE_DIR=$(find "$PROJECT_ROOT/src" -maxdepth 1 -type d ! -name "src" ! -name "__pycache__" -not -path "*/.*" | sort | head -1)
        if [ -n "$PACKAGE_DIR" ]; then
            # Make path relative to project root
            SRC_DIR="src/$(basename "$PACKAGE_DIR")"
        else
            echo -e "${RED}ERROR: No package directory found under src/${NC}"
            echo "Expected layout: src/<package_name>/"
            exit 1
        fi
    else
        echo -e "${RED}ERROR: No src/ directory found in project root${NC}"
        echo "Expected layout: $PROJECT_ROOT/src/<package_name>/"
        exit 1
    fi
else
    SRC_DIR="$ONEX_SRC_DIR"
fi

# Make SRC_DIR an absolute path for grep
# Handle both relative and absolute ONEX_SRC_DIR paths
if [[ "$SRC_DIR" = /* ]]; then
    # Absolute path - use as-is
    SRC_DIR_ABS="$SRC_DIR"
else
    # Relative path - prepend PROJECT_ROOT
    SRC_DIR_ABS="$PROJECT_ROOT/$SRC_DIR"
fi

# Verify source directory exists
if [ ! -d "$SRC_DIR_ABS" ]; then
    echo -e "${RED}ERROR: Source directory not found: $SRC_DIR_ABS${NC}"
    exit 1
fi

VIOLATIONS_FOUND=0

echo -e "${BLUE}🔍 Validating: No Model-Primitive Union types...${NC}"
echo "   Source: $SRC_DIR"
echo ""

# Pattern 1: list[Model] | list[primitive]
# Matches: list[ModelFoo] | list[str], list[Something] | list[int], etc.
echo "  Checking for list[Model] | list[primitive] patterns..."
if grep -rn --include="*.py" \
    -E ': list\[[A-Z][a-zA-Z0-9_]*\]\s*\|\s*list\[(str|int|float|bool|dict|Any)\]' \
    "$SRC_DIR_ABS" 2>/dev/null; then
    echo -e "${RED}❌ Found list[Model] | list[primitive] Union types${NC}"
    VIOLATIONS_FOUND=1
fi

# Pattern 2: dict[..] | list[dict[..]]
# Matches: dict[str, Any] | list[dict[str, Any]]
echo "  Checking for dict[..] | list[dict[..]] patterns..."
if grep -rn --include="*.py" \
    -E ': dict\[.+\]\s*\|\s*list\[dict\[' \
    "$SRC_DIR_ABS" 2>/dev/null | grep -v "# ONEX_APPROVED"; then
    echo -e "${YELLOW}⚠️  Found dict[..] | list[dict[..]] patterns (may need review)${NC}"
    # Don't mark as violation yet - these might be legacy
fi

# Pattern 3: Multiple list[] Union types
# Matches: list[str] | list[int] | list[Any]
echo "  Checking for multiple list[] Union types..."
if grep -rn --include="*.py" \
    -E ': list\[.+\]\s*\|\s*list\[.+\]\s*\|\s*list\[' \
    "$SRC_DIR_ABS" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Found multiple list[] Union types (may need review)${NC}"
fi

if [ $VIOLATIONS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ No Model-Primitive Union violations found${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}ONEX Phase 0 Violation: Model-Primitive Union Types Found${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Union types mixing models and primitives cause Pydantic validation"
    echo "confusion in parallel execution (pytest-xdist race conditions)."
    echo ""
    echo "Fix: Remove primitive fallbacks, use strongly-typed models only:"
    echo ""
    echo -e "  ${RED}❌ BAD:${NC}  dependencies: list[ModelDep] | list[str] | None"
    echo -e "  ${GREEN}✅ GOOD:${NC} dependencies: list[ModelDep] | None"
    echo ""
    echo "See: PR#59 follow-up for details on this pattern"
    echo ""
    exit 1
fi
