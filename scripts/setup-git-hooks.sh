#!/usr/bin/env bash
#
# setup-git-hooks.sh
# Install git hooks for omnibase_core
#
# This script copies git hooks from scripts/ to .git/hooks/
#
# Usage:
#   ./scripts/setup-git-hooks.sh
#

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo -e "${BLUE}🔧 Setting up git hooks for omnibase_core...${NC}"
echo ""

# Ensure .git/hooks exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ Error: .git/hooks directory not found"
    echo "   Are you in a git repository?"
    exit 1
fi

# Check if pre-push hook already exists
if [ -f "$HOOKS_DIR/pre-push" ]; then
    echo -e "${YELLOW}⚠️  Pre-push hook already exists${NC}"
    read -p "   Overwrite existing hook? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "   Skipping pre-push hook installation"
        exit 0
    fi
    # Backup existing hook
    cp "$HOOKS_DIR/pre-push" "$HOOKS_DIR/pre-push.backup.$(date +%Y%m%d_%H%M%S)"
    echo "   Backed up existing hook to pre-push.backup.*"
fi

# Create the pre-push hook
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/usr/bin/env bash
#
# Pre-Push Hook for omnibase_core
#
# This hook runs before every push to validate:
#   1. Project root is clean (no temporary/build artifacts)
#
# To bypass (NOT recommended): git push --no-verify
#

set -e

# Find the validation script
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
VALIDATION_SCRIPT="$PROJECT_ROOT/scripts/validate-clean-root.sh"

# Check if the validation script exists
if [ ! -f "$VALIDATION_SCRIPT" ]; then
    echo "⚠️  Validation script not found: $VALIDATION_SCRIPT"
    echo "ℹ️  Skipping root cleanliness check"
    exit 0
fi

# Run the validation
echo "🔒 Pre-push validation..."
echo ""

if ! "$VALIDATION_SCRIPT"; then
    echo ""
    echo "❌ Pre-push validation failed - push aborted"
    exit 1
fi

echo ""
echo "✅ Pre-push validation passed"
exit 0
EOF

# Make hook executable
chmod +x "$HOOKS_DIR/pre-push"

echo -e "${GREEN}✅ Git hooks installed successfully${NC}"
echo ""
echo "Installed hooks:"
echo -e "  ${GREEN}▸${NC} pre-push (validates clean project root)"
echo ""
echo "The pre-push hook will now run automatically before every push."
echo "To bypass: git push --no-verify (not recommended)"
echo ""

# Test the hook
echo -e "${BLUE}🧪 Testing pre-push hook...${NC}"
echo ""
if "$HOOKS_DIR/pre-push"; then
    echo ""
    echo -e "${GREEN}✅ Hook test passed - you're ready to push!${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️  Hook test found issues (see above)${NC}"
    echo "   Clean up the artifacts before pushing:"
    echo -e "   ${BLUE}rm -rf htmlcov .coverage* .pytest_cache .mypy_cache .ruff_cache dist .DS_Store${NC}"
fi
