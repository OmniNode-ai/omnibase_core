#!/bin/bash
# Batch fix all string version violations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔍 Finding files with violations..."
FILES=$(pre-commit run validate-string-versions --all-files 2>&1 | grep -A2 "^📁" | grep "^📁" | awk '{print $2}' | sort -u)
FILE_COUNT=$(echo "$FILES" | wc -l | tr -d ' ')

echo "📊 Found $FILE_COUNT files to fix"
echo ""

# Track statistics
FIXED=0
SKIPPED=0
ERRORS=0

# Process each file
for file in $FILES; do
    filepath="$PROJECT_ROOT/$file"

    if [ ! -f "$filepath" ]; then
        echo "⚠️  File not found: $filepath"
        ((ERRORS++))
        continue
    fi

    echo -n "Processing: $file ... "

    # Run fixer
    if poetry run python "$SCRIPT_DIR/fix_string_versions_regex.py" "$filepath" --backup >/dev/null 2>&1; then
        if [ -f "${filepath}.bak" ]; then
            echo "✅ Fixed"
            ((FIXED++))
        else
            echo "⏭️  No changes"
            ((SKIPPED++))
        fi
    else
        echo "❌ Error"
        ((ERRORS++))
    fi
done

echo ""
echo "=" "==================================================
echo "📈 Statistics:"
echo "   Total files:   $FILE_COUNT"
echo "   Fixed:         $FIXED"
echo "   No changes:    $SKIPPED"
echo "   Errors:        $ERRORS"
echo "==================================================
echo ""

# Verify results
echo "🔍 Verifying fixes..."
REMAINING=$(pre-commit run validate-string-versions --all-files 2>&1 | grep "Found" | head -1 | grep -o '[0-9]\+' | head -1)

if [ -z "$REMAINING" ] || [ "$REMAINING" -eq 0 ]; then
    echo "✅ All violations fixed!"
else
    echo "⚠️  $REMAINING violations remaining"
    echo ""
    echo "Remaining violations:"
    pre-commit run validate-string-versions --all-files 2>&1 | grep -A2 "^📁" | head -20
fi
