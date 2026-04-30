#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# grant-skip-approval.sh — OMN-10417
#
# Manual approval flow for [skip-receipt-gate: <id>] tokens.
#
# USAGE
#   bash scripts/grant-skip-approval.sh \
#     --id        appr-20260430-001 \
#     --granted-by jonahgabriel \
#     --repo      omnibase_core \
#     --pr-number 1234 \
#     --occ-path  /path/to/onex_change_control
#
# WHAT THIS DOES
#   1. Validates that the approver is NOT the PR author (call this script from
#      a shell authenticated as the approver, not the PR author).
#   2. Appends a new entry to onex_change_control/allowlists/skip_token_approvals.yaml
#      with a 7-day expiry.
#   3. Prints the token to add to the PR body.
#   4. Reminds you to open a PR to OCC with CODEOWNERS review from @OmniNode-ai/platform-leads.
#
# RULES
#   - The approver MUST be a member of @OmniNode-ai/platform-leads.
#   - The approver MUST NOT be the PR author (self-approval is rejected by receipt_gate.py).
#   - scope_pr_numbers is REQUIRED — every approval is scoped to specific PRs.
#   - Approvals expire after 7 days by default (pass --days N to override).
#   - You MUST open a PR to OCC and get CODEOWNERS review before the approval is live.
#
# EXAMPLE WORKFLOW
#   # 1. Platform lead runs this script for a worker's PR:
#   bash scripts/grant-skip-approval.sh \
#     --id appr-20260430-001 \
#     --granted-by platform-lead-login \
#     --repo omnibase_core \
#     --pr-number 1234 \
#     --occ-path $OMNI_HOME/omni_home/onex_change_control
#
#   # 2. Platform lead opens a PR to OCC with the modified allowlists/skip_token_approvals.yaml.
#   # 3. CODEOWNERS review from @OmniNode-ai/platform-leads.
#   # 4. Once the OCC PR merges, the worker adds to their PR body:
#   #      [skip-receipt-gate: appr-20260430-001]
#   # 5. Receipt gate validates the token against the live allowlist.

set -euo pipefail

ID=""
GRANTED_BY=""
REPO=""
PR_NUMBER=""
OCC_PATH=""
DAYS=7

while [[ $# -gt 0 ]]; do
  case "$1" in
    --id)           ID="$2"; shift 2 ;;
    --granted-by)   GRANTED_BY="$2"; shift 2 ;;
    --repo)         REPO="$2"; shift 2 ;;
    --pr-number)    PR_NUMBER="$2"; shift 2 ;;
    --occ-path)     OCC_PATH="$2"; shift 2 ;;
    --days)         DAYS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$ID" || -z "$GRANTED_BY" || -z "$REPO" || -z "$PR_NUMBER" || -z "$OCC_PATH" ]]; then
  echo "ERROR: --id, --granted-by, --repo, --pr-number, and --occ-path are all required." >&2
  exit 1
fi

ALLOWLIST="$OCC_PATH/allowlists/skip_token_approvals.yaml"
if [[ ! -f "$ALLOWLIST" ]]; then
  echo "ERROR: allowlist not found at $ALLOWLIST" >&2
  exit 1
fi

NOW_UTC=$(python3 -c "from datetime import UTC, datetime; print(datetime.now(tz=UTC).isoformat())")
EXPIRES_UTC=$(python3 -c "from datetime import UTC, datetime, timedelta; print((datetime.now(tz=UTC) + timedelta(days=${DAYS})).isoformat())")

# Append the new entry via Python to keep YAML valid.
python3 - << PYEOF
import yaml
from pathlib import Path

path = Path("$ALLOWLIST")
data = yaml.safe_load(path.read_text()) or {}
approvals = data.get("approvals") or []

new_entry = {
    "id": "$ID",
    "granted_by": "$GRANTED_BY",
    "granted_at": "$NOW_UTC",
    "expires_at": "$EXPIRES_UTC",
    "scope_repos": ["$REPO"],
    "scope_pr_numbers": [int("$PR_NUMBER")],
}

# Reject duplicate ids.
if any(a.get("id") == "$ID" for a in approvals):
    raise SystemExit(f"ERROR: id '$ID' already exists in allowlist.")

approvals.append(new_entry)
data["approvals"] = approvals
path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))
print(f"Added entry {new_entry['id']!r} to {path}")
PYEOF

echo ""
echo "========================================"
echo "  NEXT STEPS"
echo "========================================"
echo ""
echo "1. Open a PR to onex_change_control with the modified allowlist:"
echo "   git -C $OCC_PATH add allowlists/skip_token_approvals.yaml"
echo "   git -C $OCC_PATH commit -m 'feat(OMN-10417): grant skip-receipt-gate approval $ID'"
echo "   gh pr create --repo OmniNode-ai/onex_change_control --title 'feat(OMN-10417): grant skip-receipt-gate approval $ID'"
echo ""
echo "2. Get CODEOWNERS review from @OmniNode-ai/platform-leads."
echo ""
echo "3. Once merged, add to the PR body:"
echo "   [skip-receipt-gate: $ID]"
echo ""
echo "4. Approval expires: $EXPIRES_UTC"
echo "========================================"
