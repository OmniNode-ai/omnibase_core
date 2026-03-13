#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# Usage: spdx-rollout.sh <worktree_path>
# Runs SPDX header rollout for a single repo worktree.
# Prereqs: worktree already created, omnibase_core dev dep added.
set -euo pipefail

WORKTREE="${1:?Usage: spdx-rollout.sh <worktree_path>}"
cd "$WORKTREE"

echo "=== SPDX Rollout: $(basename "$WORKTREE") ==="

# 0. Preflight checks
echo "[0] Preflight checks..."
[[ -f ".pre-commit-config.yaml" ]] || {
  echo "ERROR: .pre-commit-config.yaml not found. Create it and add the validate-spdx-headers hook first."
  exit 1
}
pre-commit --version > /dev/null || {
  echo "ERROR: pre-commit not available. Run: pip install pre-commit && pre-commit install"
  exit 1
}

# 1. Verify onex is available
echo "[1] Checking onex availability..."
uv run onex --version || {
  echo "ERROR: onex not available. Add omnibase_core as a dev dep:"
  echo "  uv add --dev omnibase_core"
  exit 1
}

# 2. Resolve eligible directories (fail fast if none found)
DIRS=()
for d in src tests scripts examples; do [ -d "$d" ] && DIRS+=("$d"); done
if [ ${#DIRS[@]} -eq 0 ]; then
  echo "ERROR: No eligible directories found among src/tests/scripts/examples. Nothing to stamp."
  exit 1
fi
echo "[2] Eligible dirs: ${DIRS[*]}"

# 3. Dry-run audit (|| true: non-zero expected when files need stamping — informational only)
AUDIT_FILE="$(mktemp "/tmp/spdx-audit-$(basename "$WORKTREE").XXXXXX.txt")"
echo "[3] Auditing files that need SPDX headers (output: $AUDIT_FILE)..."
uv run onex spdx fix --dry-run "${DIRS[@]}" 2>&1 | tee "$AUDIT_FILE" || true
echo "Audit complete. Review $AUDIT_FILE before continuing."
echo "Add '# spdx-skip: <reason>' to any generated/vendored files BEFORE continuing."
read -r -p "Press Enter to proceed with stamping (Ctrl-C to abort)..."

# 4. Stamp eligible files
echo "[4] Stamping SPDX headers..."
uv run onex spdx fix "${DIRS[@]}"

# 5. Validate stamp is clean
echo "[5] Validating headers match hook scope..."
uv run onex spdx fix --check "${DIRS[@]}"
echo "Validation passed."

# 6. Install hooks (required for fresh worktrees) then run only the SPDX hook
# (not full suite — separate ticket for pre-existing failures)
echo "[6] Installing pre-commit hooks in this worktree..."
pre-commit install
echo "Running validate-spdx-headers hook..."
pre-commit run validate-spdx-headers --all-files
echo "Hook passed."

echo "=== Rollout complete for $(basename "$WORKTREE"). ==="
echo "Review staged changes, then commit:"
echo "  git add -A && git commit -m 'feat(spdx): add SPDX MIT header enforcement and stamp all eligible files'"
