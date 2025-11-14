#!/usr/bin/env bash
#
# validate-clean-root.sh
# Validates that project root is clean (no temporary/build artifacts)
#
# This script can be:
#   1. Run directly for validation
#   2. Copied to .git/hooks/pre-push for automatic enforcement
#
# Exit codes:
#   0 - Project root is clean
#   1 - Violations found (artifacts in root)
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

# Configuration: Files/directories that should NOT exist in project root
FORBIDDEN_PATTERNS=(
    # Coverage files
    ".coverage"
    ".coverage.*"
    "htmlcov"
    "coverage.xml"
    ".coverage.json"

    # Audit and reports
    "audit_*.json"
    "security_audit_*.json"
    "*.audit.json"
    "*_audit_report.json"

    # Python cache
    "__pycache__"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    ".Python"

    # Pytest cache
    ".pytest_cache"

    # Mypy cache
    ".mypy_cache"

    # Ruff cache
    ".ruff_cache"

    # Temporary files
    "*.tmp"
    "*.temp"
    "*.swp"
    "*.swo"
    "*~"

    # Log files
    "*.log"
    "npm-debug.log*"
    "yarn-debug.log*"
    "yarn-error.log*"

    # Build artifacts
    "build"
    "dist"
    "*.egg-info"

    # IDE artifacts
    ".vscode/settings.json.bak"
    ".idea/workspace.xml"

    # OS files
    ".DS_Store"
    "Thumbs.db"
)

# Whitelist: Allowed patterns that match forbidden patterns
WHITELIST=(
    ".vscode"  # VS Code directory is allowed
    ".idea"    # IntelliJ directory is allowed
    ".github"  # GitHub workflows are allowed
)

echo -e "${BLUE}🔍 Validating project root cleanliness...${NC}"
echo "   Project: $PROJECT_ROOT"
echo ""

VIOLATIONS_FOUND=0
VIOLATIONS_LIST=()

# Check each forbidden pattern
for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    # Use find to check for pattern in root directory only (maxdepth 1)
    while IFS= read -r -d '' file; do
        # Get relative path from project root
        relative_path="${file#$PROJECT_ROOT/}"

        # Check if it's in whitelist
        is_whitelisted=0
        for whitelist_item in "${WHITELIST[@]}"; do
            if [[ "$relative_path" == "$whitelist_item"* ]]; then
                is_whitelisted=1
                break
            fi
        done

        if [ $is_whitelisted -eq 0 ]; then
            VIOLATIONS_LIST+=("$relative_path")
            VIOLATIONS_FOUND=1
        fi
    done < <(find "$PROJECT_ROOT" -maxdepth 1 -name "$pattern" -print0 2>/dev/null)
done

# Report results
if [ $VIOLATIONS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ Project root is clean - no temporary/build artifacts found${NC}"
    exit 0
else
    echo -e "${RED}❌ Project root validation FAILED${NC}"
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}Found ${#VIOLATIONS_LIST[@]} temporary/build artifact(s) in project root:${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    for violation in "${VIOLATIONS_LIST[@]}"; do
        echo -e "  ${RED}▸${NC} $violation"
    done

    echo ""
    echo -e "${YELLOW}Why this matters:${NC}"
    echo "  • Temporary files pollute the repository"
    echo "  • Build artifacts should not be committed"
    echo "  • Coverage reports belong in CI, not source control"
    echo "  • Clean root improves developer experience"
    echo ""
    echo -e "${YELLOW}How to fix:${NC}"
    echo "  1. Review the listed files above"
    echo "  2. Delete temporary/build artifacts:"
    echo -e "     ${BLUE}rm -rf htmlcov .coverage* *.log audit_*.json${NC}"
    echo "  3. Add to .gitignore if needed"
    echo "  4. Try pushing again"
    echo ""
    echo -e "${YELLOW}To bypass this check (NOT recommended):${NC}"
    echo -e "  ${BLUE}git push --no-verify${NC}"
    echo ""

    exit 1
fi
