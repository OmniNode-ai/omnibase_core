#!/usr/bin/env bash
set -euo pipefail

# ONEX Nightly Producer Script
# Generates incremental review inputs for changes since last successful run

# Configuration
EXCLUDES_REGEX='(^|/)(archive|archived|deprecated|dist|build|node_modules|venv|\.venv|\.mypy_cache|\.pytest_cache)(/|$)'
INCLUDE_EXT='py|pyi|yaml|yml|toml|json|ini|cfg|sh|bash|ps1|psm1|go|rs|ts|tsx|js|jsx|proto|sql|md'

# State management
STATE_DIR=".onex_nightly"
PREV_FILE="$STATE_DIR/last_successful_sha"

# Detect repository name
REPO_NAME="$(basename "$(git rev-parse --show-toplevel)")"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$STATE_DIR/runs/$TIMESTAMP"

echo "Starting nightly review for: $REPO_NAME"
echo "Timestamp: $TIMESTAMP"

# Create directories
mkdir -p "$STATE_DIR/runs"
mkdir -p "$OUT_DIR"

# Fetch latest changes
echo "Fetching latest from origin..."
git fetch origin

# Initialize or read previous SHA
if [[ ! -f "$PREV_FILE" ]]; then
    echo "No previous run found. Initializing with current origin/main"
    PREV="$(git rev-parse origin/main)"
    echo "$PREV" > "$PREV_FILE"
    echo "Initialized with SHA: $PREV"
    echo "Run baseline_producer.sh first for initial analysis"
    exit 0
fi

PREV="$(cat "$PREV_FILE")"
HEAD_SHA="$(git rev-parse origin/main)"

echo "Previous SHA: $PREV"
echo "Current SHA: $HEAD_SHA"

# Check if there are changes
if [[ "$PREV" == "$HEAD_SHA" ]]; then
    echo "No changes detected since last run"
    exit 0
fi

# Generate file list for changed files
echo "Analyzing changes..."
git diff --name-status "$PREV...$HEAD_SHA" | while IFS=$'\t' read -r status file; do
    # Skip if file matches exclude pattern
    if [[ "$file" =~ $EXCLUDES_REGEX ]]; then
        continue
    fi
    # Include if file matches extension pattern
    if [[ "$file" =~ \.(${INCLUDE_EXT})$ ]]; then
        echo -e "$status\t$file"
    fi
done > "$OUT_DIR/nightly.names"

# Get list of files for diff generation
git diff --name-only "$PREV...$HEAD_SHA" | while read -r file; do
    # Skip if file matches exclude pattern
    if [[ "$file" =~ $EXCLUDES_REGEX ]]; then
        continue
    fi
    # Include if file matches extension pattern
    if [[ "$file" =~ \.(${INCLUDE_EXT})$ ]]; then
        echo "$file"
    fi
done > "$OUT_DIR/files.list"

FILE_COUNT=$(wc -l < "$OUT_DIR/files.list" 2>/dev/null || echo "0")
echo "Files changed: $FILE_COUNT"

if [[ "$FILE_COUNT" == "0" ]]; then
    echo "No relevant files changed (after filtering)"
    # Update marker anyway to track progress
    echo "$HEAD_SHA" > "$PREV_FILE.tmp"
    mv "$PREV_FILE.tmp" "$PREV_FILE"
    exit 0
fi

# Generate diff stats
echo "Generating diff statistics..."
git diff --stat "$PREV...$HEAD_SHA" -- $(cat "$OUT_DIR/files.list") > "$OUT_DIR/nightly.stats" || true

# Generate unified diff
echo "Generating unified diff..."
git diff -U1 --no-color "$PREV...$HEAD_SHA" -- $(cat "$OUT_DIR/files.list") > "$OUT_DIR/nightly.diff" || true

# Check diff size
DIFF_SIZE=$(wc -c < "$OUT_DIR/nightly.diff")
DIFF_SIZE_MB=$((DIFF_SIZE / 1024 / 1024))
echo "Diff size: ${DIFF_SIZE} bytes (${DIFF_SIZE_MB} MB)"

# Generate metadata
cat > "$OUT_DIR/metadata.json" <<EOF
{
  "repo": "$REPO_NAME",
  "timestamp": "$TIMESTAMP",
  "prev_sha": "$PREV",
  "head_sha": "$HEAD_SHA",
  "range": "$PREV...$HEAD_SHA",
  "file_count": $FILE_COUNT,
  "diff_size_bytes": $DIFF_SIZE,
  "truncated": false
}
EOF

# Check if diff needs truncation (e.g., > 500KB)
MAX_DIFF_BYTES=$((500 * 1024))
if (( DIFF_SIZE > MAX_DIFF_BYTES )); then
    echo "Warning: Diff exceeds size limit. Truncating..."
    head -c $MAX_DIFF_BYTES "$OUT_DIR/nightly.diff" > "$OUT_DIR/nightly.diff.truncated"
    mv "$OUT_DIR/nightly.diff.truncated" "$OUT_DIR/nightly.diff"

    # Update metadata
    sed -i 's/"truncated": false/"truncated": true/' "$OUT_DIR/metadata.json"
fi

# Generate commit list
echo "Generating commit list..."
git log --oneline "$PREV...$HEAD_SHA" > "$OUT_DIR/commits.log"
COMMIT_COUNT=$(wc -l < "$OUT_DIR/commits.log")

echo ""
echo "Nightly review preparation complete:"
echo "  - Commits analyzed: $COMMIT_COUNT"
echo "  - Files changed: $FILE_COUNT"
echo "  - Diff size: ${DIFF_SIZE} bytes"
echo "  - Output directory: $OUT_DIR"
echo ""
echo "Run the ONEX reviewer with:"
echo "  ./onex/scripts/onex_reviewer.py nightly \"$OUT_DIR\""
echo ""
echo "Note: SHA marker will be updated only after successful review"

# Create a temporary marker file (will be moved after successful review)
echo "$HEAD_SHA" > "$OUT_DIR/next_sha"