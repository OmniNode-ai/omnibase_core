#!/bin/bash
# Apply string version fixer to all model files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔍 Finding all model files..."
FILES=$(find "$PROJECT_ROOT/src/omnibase_core" -name "model_*.py" -o -name "mixin_*.py" -type f | sort)
FILE_COUNT=$(echo "$FILES" | wc -l | tr -d ' ')

echo "📊 Found $FILE_COUNT model files"
echo ""

# Track statistics
FIXED=0
SKIPPED=0
ERRORS=0

# Process each file
for filepath in $FILES; do
    filename=$(basename "$filepath")
    echo -n "Processing: $filename ... "

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
echo "==================================================
echo "📈 Statistics:"
echo "   Total files:   $FILE_COUNT"
echo "   Fixed:         $FIXED"
echo "   No changes:    $SKIPPED"
echo "   Errors:        $ERRORS"
echo "==================================================
