#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# OMN-14682: Local pre-push Evidence-Source SHAPE check.
#
# Gives authors fail-fast feedback on a malformed / mis-placed Evidence-Source
# block BEFORE the CI receipt-gate runs, instead of discovering it after push or
# via manual PR-body normalization. This is the LOCAL companion to the hardened
# CI receipt-gate (omnibase_core.validation.validator_receipt_gate); the gate
# remains the authoritative, receipt-verifying enforcement layer.
#
# Body source (first non-empty wins):
#   1. $PR_BODY environment variable (used by tests / scripted pushes)
#   2. `gh pr view --json body` for the current branch's open PR
#
# When there is no PR yet (first push), no gh CLI, or gh is unauthenticated,
# there is nothing to validate locally — the hook prints a notice and exits 0.
# The CI receipt-gate still enforces the same shape on the real PR body, so this
# graceful no-op cannot let a bad shape merge.
#
# Usage:
#   Invoked by pre-commit at the pre-push stage (pass_filenames: false).
#   --self-test   Run synthetic self-tests and exit.

set -uo pipefail

TICKET_REF="OMN-14682"

run_shape_check() {
  # $1: PR body text. Returns the CLI's exit code.
  # `env -u PYTHONPATH` clears any ambient PYTHONPATH that would shadow the
  # worktree's omnibase_core with a canonical clone on sys.path
  # (reference_pythonpath_shadows_worktree_source; matches the substrate-gate
  # hooks in .pre-commit-config.yaml).
  local body="$1"
  printf '%s' "$body" | env -u PYTHONPATH uv run python -m omnibase_core.validation.validator_evidence_shape_cli --pr-body-file -
}

self_test() {
  local fails=0

  local bad_body
  bad_body='Closes OMN-1

```
Evidence-Source: OCC#1234
```
'
  if run_shape_check "$bad_body" >/dev/null 2>&1; then
    echo "[${TICKET_REF}] SELF-TEST FAIL: fenced-only stamp should have been rejected" >&2
    fails=1
  fi

  local good_body
  good_body='Closes OMN-1

Evidence-Source: OCC#1234
Evidence-Ticket: OMN-1
'
  if ! run_shape_check "$good_body" >/dev/null 2>&1; then
    echo "[${TICKET_REF}] SELF-TEST FAIL: canonical stamp + ticket should pass" >&2
    fails=1
  fi

  local none_body
  none_body='Closes OMN-1

No evidence stamp here.
'
  if ! run_shape_check "$none_body" >/dev/null 2>&1; then
    echo "[${TICKET_REF}] SELF-TEST FAIL: no-stamp body should pass (shape-clean)" >&2
    fails=1
  fi

  if [ "$fails" -eq 0 ]; then
    echo "[${TICKET_REF}] SELF-TEST PASS"
  fi
  return "$fails"
}

if [ "${1:-}" = "--self-test" ]; then
  self_test
  exit $?
fi

# Resolve the PR body.
PR_BODY_TEXT="${PR_BODY:-}"

if [ -z "$PR_BODY_TEXT" ]; then
  if command -v gh >/dev/null 2>&1; then
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [ -n "$branch" ] && [ "$branch" != "HEAD" ]; then
      # gh resolves the open PR for the current branch; empty when none/unauth.
      PR_BODY_TEXT="$(gh pr view "$branch" --json body --jq '.body' 2>/dev/null || true)"
    fi
  fi
fi

if [ -z "$PR_BODY_TEXT" ]; then
  echo "[${TICKET_REF}] evidence-shape: no PR body available yet (no open PR / gh); skipping local check. CI receipt-gate still enforces on push."
  exit 0
fi

if run_shape_check "$PR_BODY_TEXT"; then
  exit 0
fi

echo "[${TICKET_REF}] evidence-shape check FAILED — fix the Evidence-Source block above before pushing (or the CI receipt-gate will block the PR)." >&2
exit 1
