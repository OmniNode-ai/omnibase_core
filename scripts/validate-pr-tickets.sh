#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# validate-pr-tickets.sh — CI gate for OMN-8916
#
# Parses a PR for OMN-XXXX ticket IDs, fetches each from Linear via GH CLI
# GraphQL, validates against ModelTicketContract, exits non-zero on any failure.
#
# Usage:
#   PR_NUMBER=123 REPO=OmniNode-ai/omnibase_core bash scripts/validate-pr-tickets.sh
#   Or:  bash scripts/validate-pr-tickets.sh [pr_number]

set -euo pipefail

PR_NUMBER="${1:-${PR_NUMBER:-}}"
REPO="${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")}"
LINEAR_API_KEY="${LINEAR_API_KEY:-}"
SKIP_LABEL="skip-contract-gate"

if [[ -z "$PR_NUMBER" ]]; then
  echo "[validate-pr-tickets] ERROR: PR_NUMBER not set" >&2
  exit 1
fi

# Fetch PR metadata
PR_JSON=$(gh pr view "$PR_NUMBER" --repo "$REPO" \
  --json title,body,headRefName,labels 2>/dev/null) || {
  echo "[validate-pr-tickets] ERROR: Could not fetch PR #$PR_NUMBER from $REPO" >&2
  exit 1
}

# Check for skip label
LABELS=$(echo "$PR_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join(l['name'] for l in d.get('labels',[])))")
if echo "$LABELS" | grep -qw "$SKIP_LABEL"; then
  echo "[validate-pr-tickets] Skipping: label '$SKIP_LABEL' present"
  exit 0
fi

# Extract OMN-\d+ ticket IDs from branch, title, body
ALL_TEXT=$(echo "$PR_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('headRefName','') + ' ' + d.get('title','') + ' ' + d.get('body',''))
")

TICKET_IDS=$(echo "$ALL_TEXT" | grep -oE 'OMN-[0-9]+' | sort -u || true)

if [[ -z "$TICKET_IDS" ]]; then
  echo "[validate-pr-tickets] No OMN-XXXX tickets found — skipping gate"
  exit 0
fi

echo "[validate-pr-tickets] Found tickets: $(echo "$TICKET_IDS" | tr '\n' ' ')"

# Validate each ticket
FAILED=0
for TICKET_ID in $TICKET_IDS; do
  echo "[validate-pr-tickets] Validating $TICKET_ID ..."

  # Fetch from Linear via GraphQL
  if [[ -z "$LINEAR_API_KEY" ]]; then
    echo "[validate-pr-tickets] WARNING: LINEAR_API_KEY not set, skipping Linear fetch for $TICKET_ID" >&2
    continue
  fi

  TICKET_JSON=$(curl -s -X POST "https://api.linear.app/graphql" \
    -H "Authorization: $LINEAR_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"{ issue(id: \\\"$TICKET_ID\\\") { identifier title description } }\"}" \
    2>/dev/null) || {
    echo "[validate-pr-tickets] ERROR: Linear API call failed for $TICKET_ID" >&2
    FAILED=1
    continue
  }

  # Run Python validator inline
  RESULT=$(python3 - <<PYEOF
import sys, json
try:
    from omnibase_core.contracts.validators.validate_ticket_contract import validate_ticket_contract

    raw = json.loads('''${TICKET_JSON}''')
    issue = raw.get("data", {}).get("issue") or {}
    desc = issue.get("description", "")

    import re, yaml as _yaml

    # Extract YAML contract block from description
    contract_match = re.search(r'```yaml\n(.*?)```', desc, re.DOTALL)
    if not contract_match:
        print(json.dumps({"valid": False, "errors": ["No YAML contract block found in ticket description"]}))
        sys.exit(0)

    contract_dict = _yaml.safe_load(contract_match.group(1))
    contract_dict.setdefault("ticket_id", issue.get("identifier", ""))
    contract_dict.setdefault("title", issue.get("title", ""))

    result = validate_ticket_contract(contract_dict)
    print(json.dumps({"valid": result.valid, "errors": result.errors}))
except Exception as e:
    print(json.dumps({"valid": False, "errors": [str(e)]}))
PYEOF
)

  VALID=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['valid'])")
  ERRORS=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(d['errors']))")

  if [[ "$VALID" != "True" ]]; then
    echo "[validate-pr-tickets] FAIL $TICKET_ID:"
    echo "$ERRORS" | sed 's/^/  /'
    FAILED=1
  else
    echo "[validate-pr-tickets] PASS $TICKET_ID"
  fi
done

if [[ "$FAILED" -ne 0 ]]; then
  echo ""
  echo "[validate-pr-tickets] CONTRACT GATE FAILED — one or more tickets have incomplete contracts."
  echo "Fix dod_evidence, golden_path, or deploy_step in the Linear ticket description."
  exit 1
fi

echo "[validate-pr-tickets] All tickets passed contract validation."
exit 0
