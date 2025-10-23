#!/bin/bash
# remove_unused_ignores.sh
# Automatically remove unused type: ignore comments from codebase
# Part of Phase 1: Quick Wins for type safety improvements

set -e

PROJECT_ROOT="/Volumes/PRO-G40/Code/omnibase_core"
cd "$PROJECT_ROOT"

echo "════════════════════════════════════════════════════════════════"
echo "  Removing Unused Type Ignore Comments"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Create backup directory
BACKUP_DIR="$PROJECT_ROOT/.backup_$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating backup in: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Get list of files with unused ignores
echo "🔍 Scanning for unused type ignore comments..."
poetry run mypy src/omnibase_core/ --strict 2>&1 | \
  grep 'Unused "type: ignore"' | \
  cut -d: -f1 | \
  sort -u > /tmp/files_to_fix.txt

FILE_COUNT=$(wc -l < /tmp/files_to_fix.txt)
echo "   Found $FILE_COUNT files with unused ignores"
echo ""

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "✅ No unused type ignore comments found!"
    exit 0
fi

# Process each file
echo "🛠️  Processing files..."
FIXED_COUNT=0

while read -r file; do
    if [ -f "$file" ]; then
        # Create backup
        cp "$file" "$BACKUP_DIR/$(basename "$file").bak"

        # Get line numbers for this file
        poetry run mypy src/omnibase_core/ --strict 2>&1 | \
            grep "$file" | \
            grep 'Unused "type: ignore"' | \
            cut -d: -f2 | \
            sort -rn | \
            while read -r line_num; do
                # Remove type ignore from line (process in reverse order to preserve line numbers)
                sed -i.tmp "${line_num}s/  # type: ignore.*$//" "$file"
                rm -f "$file.tmp"
            done

        FIXED_COUNT=$((FIXED_COUNT + 1))
        echo "   ✓ Fixed: $file"
    fi
done < /tmp/files_to_fix.txt

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Removed unused ignores from $FIXED_COUNT files"
echo ""
echo "📋 Running mypy to verify..."
echo "═══════════════════════════════════════════════════════════════"

# Verify changes
if poetry run mypy src/omnibase_core/ --strict 2>&1 | grep -q 'Unused "type: ignore"'; then
    REMAINING=$(poetry run mypy src/omnibase_core/ --strict 2>&1 | grep -c 'Unused "type: ignore"' || true)
    echo "⚠️  Warning: $REMAINING unused ignore comments still remain"
    echo "   Check mypy output for details"
    echo ""
    echo "🔄 Backup available at: $BACKUP_DIR"
else
    echo "✅ All unused type ignore comments successfully removed!"
    echo ""
    echo "🗑️  Backup directory can be deleted: $BACKUP_DIR"
fi

echo ""
echo "Next steps:"
echo "  1. Run tests: poetry run pytest tests/"
echo "  2. Review changes: git diff"
echo "  3. Commit: git add -A && git commit -m 'chore: remove unused type ignore comments'"
echo ""
