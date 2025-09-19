#!/usr/bin/env bash
set -euo pipefail

# ONEX Baseline Producer Script
# Generates sharded baseline inputs for initial repository analysis

# Configuration
EXCLUDES_REGEX='(^|/)(archive|archived|deprecated|dist|build|node_modules|venv|\.venv|\.mypy_cache|\.pytest_cache)(/|$)'
INCLUDE_EXT='py|pyi|yaml|yml|toml|json|ini|cfg|sh|bash|ps1|psm1|go|rs|ts|tsx|js|jsx|proto|sql|md'
BYTES_PER_SHARD=$((200*1024))  # 200KB per shard
EMPTY_TREE=4b825dc642cb6eb9a060e54bf8d69288fbee4904

# Detect repository name
REPO_NAME="$(basename "$(git rev-parse --show-toplevel)")"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR=".onex_baseline/$REPO_NAME/$TIMESTAMP"

echo "Starting baseline analysis for: $REPO_NAME"
echo "Output directory: $OUT_DIR"

# Create output directories
mkdir -p "$OUT_DIR/shards"

# Get current HEAD
HEAD_SHA="$(git rev-parse HEAD)"

# Generate file list (excluding archives and including specified extensions)
echo "Generating file list..."
git ls-files -z \
  | tr -d '\r' \
  | xargs -0 -I{} bash -c '[[ "{}" =~ '"$EXCLUDES_REGEX"' ]] || echo "{}"' \
  | grep -E "\.(${INCLUDE_EXT})$" \
  > "$OUT_DIR/files.list" || true

FILE_COUNT=$(wc -l < "$OUT_DIR/files.list")
echo "Found $FILE_COUNT files to analyze"

# Generate git names (all files as added)
awk '{print "A\t"$0}' "$OUT_DIR/files.list" > "$OUT_DIR/baseline.names"

# Generate unified diff against empty tree
echo "Generating unified diff..."
git diff -U0 --no-color "$EMPTY_TREE"...HEAD -- $(cat "$OUT_DIR/files.list") > "$OUT_DIR/baseline.diff" || true

# Generate diff stats
git diff --stat "$EMPTY_TREE"...HEAD -- $(cat "$OUT_DIR/files.list") > "$OUT_DIR/baseline.stats" || true

# Check if diff was generated
if [[ ! -s "$OUT_DIR/baseline.diff" ]]; then
    echo "Warning: No diff generated. Check if files exist."
    exit 0
fi

# Split diff into shards
echo "Sharding diff file..."
csplit -s -f "$OUT_DIR/tmpdiff_" -b "%03d" "$OUT_DIR/baseline.diff" '/^diff --git /' '{*}' 2>/dev/null || true

# Combine temporary files into size-limited shards
shard_idx=0
shard_bytes=0
> "$OUT_DIR/manifest.tsv"

for part in "$OUT_DIR"/tmpdiff_*; do
    [[ -f "$part" ]] || continue

    bytes=$(wc -c < "$part")

    # Start new shard if current would exceed limit
    if (( shard_bytes + bytes > BYTES_PER_SHARD || shard_bytes == 0 )); then
        (( shard_idx++ ))
        shard_file="$OUT_DIR/shards/diff_shard_${shard_idx}.diff"
        > "$shard_file"
        shard_bytes=0
        echo -e "$shard_idx\t$shard_file\t0" >> "$OUT_DIR/manifest.tsv"
    fi

    cat "$part" >> "$shard_file"
    shard_bytes=$((shard_bytes + bytes))

    # Update manifest with actual size
    sed -i "s|$shard_idx\t$shard_file\t.*|$shard_idx\t$shard_file\t$shard_bytes|" "$OUT_DIR/manifest.tsv"
done

# Clean up temporary files
rm -f "$OUT_DIR"/tmpdiff_*

# Generate metadata file
cat > "$OUT_DIR/metadata.json" <<EOF
{
  "repo": "$REPO_NAME",
  "timestamp": "$TIMESTAMP",
  "empty_tree": "$EMPTY_TREE",
  "head_sha": "$HEAD_SHA",
  "range": "$EMPTY_TREE...$HEAD_SHA",
  "file_count": $FILE_COUNT,
  "shard_count": $shard_idx,
  "bytes_per_shard": $BYTES_PER_SHARD
}
EOF

echo "Baseline analysis complete:"
echo "  - Files analyzed: $FILE_COUNT"
echo "  - Shards created: $shard_idx"
echo "  - Output directory: $OUT_DIR"
echo ""
echo "Run the ONEX reviewer with:"
echo "  ./onex/scripts/onex_reviewer.py baseline \"$OUT_DIR\""