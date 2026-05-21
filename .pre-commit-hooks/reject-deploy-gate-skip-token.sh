#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# OMN-10414 (extends OMN-10347 / OMN-9730 DGM-Phase4): Mechanical block on ALL
# [skip-*] bypass tokens, including [skip-receipt-gate:] and [skip-deploy-gate:].
# Rejects any staged file or commit message containing [skip-<anything>:].
#
# BLOCKING — this hook rejects all [skip-*] tokens. This is the LOCAL enforcement
# layer. The GHA workflow (reject-deploy-gate-skip.yml) is the REMOTE enforcement
# layer. Both layers are required; neither is advisory-only. Using --no-verify
# bypasses this hook but not the remote GHA gate, which is a required status check.
#
# CLAUDE.md Rule #10: Never bypass local gates. Fix the underlying issue.
# Plan: omni_home/docs/plans/2026-04-30-gate-collapse-fix.md Task 8
#
# Tokens blocked (case-insensitive):
#   [skip-deploy-gate: ...]   — deploy-gate bypass (original OMN-9730)
#   [skip-receipt-gate: ...]  — receipt-gate bypass (OMN-10414)
#   [skip-<anything>: ...]    — any other [skip-*] form
#
# Escape hatch (explicit user approval only):
#   Add a line containing:  # skip-token-allowed: <receipt-id>
#   The receipt-id documents the explicit user approval hand-off.
#   This is NOT a free-text bypass — it requires a traceable approval receipt.
#
# Usage:
#   Invoked by pre-commit with staged filenames as arguments.
#   --self-test       Run synthetic self-tests and exit.
#   --check-pr-body <PR_NUMBER>   Also scan live PR body via gh cli.

set -euo pipefail

# OMN-10347: Broadened to ALL [skip-* tokens per Rule #10 (was [skip-deploy-gate: only).
SKIP_PATTERN='\[skip-[a-zA-Z]'
# Case-insensitive allowlist pattern — matches the skip-pattern's -i flag
ALLOWLIST_PATTERN='#[[:space:]]*[Ss][Kk][Ii][Pp]-[Tt][Oo][Kk][Ee][Nn]-[Aa][Ll][Ll][Oo][Ww][Ee][Dd]:[[:space:]]*[^[:space:]]'

RULE_REF="CLAUDE.md Rule #10 + docs/plans/2026-04-30-gate-collapse-fix.md Task 8"
TICKET_REF="OMN-10414"

# ──────────────────────────────────────────────────────────────────────────────
# Self-test mode
# ──────────────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--self-test" ]]; then
    PASS=0
    FAIL=0

    run_test() {
        local name="$1"
        local content="$2"
        local expect_exit="$3"

        # Use .md extension so the file-type filter includes it in scanning
        tmpfile=$(mktemp /tmp/skip-token-selftest.XXXXXX.md)
        printf '%s\n' "$content" > "$tmpfile"

        # Run hook against the temp file (not --self-test or --check-pr-body mode)
        actual_exit=0
        bash "$0" "$tmpfile" 2>/dev/null || actual_exit=$?

        rm -f "$tmpfile"

        if [[ "$actual_exit" == "$expect_exit" ]]; then
            echo "  PASS: $name"
            PASS=$((PASS + 1))
        else
            echo "  FAIL: $name (expected exit $expect_exit, got $actual_exit)"
            FAIL=$((FAIL + 1))
        fi
    }

    echo "=== reject-deploy-gate-skip-token.sh self-test ==="

    run_test "clean file passes" \
        "This is a clean PR body with no bypass tokens." \
        0

    run_test "skip-deploy-gate token rejected" \
        "[skip-deploy-gate: correctness fix, no deployable artifact change]" \
        1

    run_test "skip-receipt-gate free-text rejected (OMN-10414)" \
        "[skip-receipt-gate: docs only, no receipts needed]" \
        1

    run_test "skip-anything token rejected (OMN-10347)" \
        "[skip-anything: some reason]" \
        1

    run_test "skip-deploy-gate with allowlist receipt passes" \
        "[skip-deploy-gate: correctness fix]
# skip-token-allowed: USER-APPROVAL-2026-04-25-jonah" \
        0

    run_test "skip-receipt-gate with skip-token-allowed passes (OMN-10414)" \
        "[skip-receipt-gate: chore only]
# skip-token-allowed: USER-APPROVAL-2026-04-30-jonah" \
        0

    run_test "allowlist without skip-token passes" \
        "Normal PR body
# skip-token-allowed: some-receipt" \
        0

    run_test "case-insensitive skip-deploy-gate rejected" \
        "[Skip-Deploy-Gate: reason here]" \
        1

    run_test "case-insensitive skip-receipt-gate rejected (OMN-10414)" \
        "[Skip-Receipt-Gate: reason here]" \
        1

    echo ""
    echo "Results: $PASS passed, $FAIL failed"
    if [[ "$FAIL" -gt 0 ]]; then
        exit 1
    fi
    exit 0
fi

# ──────────────────────────────────────────────────────────────────────────────
# PR body check mode
# ──────────────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--check-pr-body" ]]; then
    PR_NUMBER="${2:-}"
    if [[ -z "$PR_NUMBER" ]]; then
        echo "ERROR: --check-pr-body requires a PR number as the next argument" >&2
        exit 1
    fi

    if ! command -v gh &>/dev/null; then
        echo "WARNING: gh cli not available — skipping PR body check" >&2
        exit 0
    fi

    PR_BODY=$(gh pr view "$PR_NUMBER" --json body --jq .body 2>/dev/null || true)
    if [[ -z "$PR_BODY" ]]; then
        echo "WARNING: could not fetch PR body for PR #$PR_NUMBER — skipping" >&2
        exit 0
    fi

    if echo "$PR_BODY" | grep -qiE "$SKIP_PATTERN"; then
        if echo "$PR_BODY" | grep -qiE "$ALLOWLIST_PATTERN"; then
            echo "WARNING: [skip-*] token found in PR #$PR_NUMBER body but explicit approval receipt present — allowed." >&2
            exit 0
        fi
        echo "ERROR: PR #$PR_NUMBER body contains a [skip-*] bypass token." >&2
        echo "  Per $RULE_REF, bypass is not permitted without explicit user approval." >&2
        echo "  Fix the gate properly: add dod_evidence or use the structured no_deployable_artifact exception." >&2
        echo "  Ticket: $TICKET_REF" >&2
        exit 1
    fi
    exit 0
fi

# ──────────────────────────────────────────────────────────────────────────────
# Commit-msg mode: invoked with a single argument pointing to COMMIT_EDITMSG.
# pre-commit passes the message file path; we read it directly (it is not a
# staged blob — it lives outside the index).
# ──────────────────────────────────────────────────────────────────────────────
if [[ "${GIT_HOOK_STAGE:-}" == "commit-msg" || "$#" -eq 1 && "${1:-}" == *COMMIT_EDITMSG* ]]; then
    msg_file="${1:-}"
    if [[ -n "$msg_file" && -f "$msg_file" ]]; then
        if grep -qiE "$SKIP_PATTERN" "$msg_file"; then
            if grep -qiE "$ALLOWLIST_PATTERN" "$msg_file"; then
                echo "WARNING: [skip-*] token found in commit message but explicit approval receipt present — allowed." >&2
                exit 0
            fi
            echo "ERROR: commit message contains a [skip-*] bypass token." >&2
            echo "  Per $RULE_REF, bypass is not permitted without explicit user approval." >&2
            echo "  Fix the gate properly:" >&2
            echo "    1. Add dod_evidence with type: no_deployable_artifact (preferred)" >&2
            echo "    2. Narrow the path patterns in validate_pr_deploy_required.py" >&2
            echo "    3. If truly exceptional, add '# skip-token-allowed: <receipt-id>' with a traceable approval receipt" >&2
            echo "  Ticket: $TICKET_REF" >&2
            exit 1
        fi
    fi
    exit 0
fi

# ──────────────────────────────────────────────────────────────────────────────
# Normal mode: scan staged files passed as arguments.
# Read staged blobs from the index (git show :$file) rather than the working
# tree to prevent bypass via working-tree edits after git add.
# Only scan file types that could plausibly be PR bodies or ticket contracts:
# markdown, yaml, yml, txt, md. Python/shell source that discusses skip tokens
# (docs, tests, validators) should not be blocked by this hook.
# ──────────────────────────────────────────────────────────────────────────────
FOUND_VIOLATION=0

for file in "$@"; do
    # Restrict to PR-body-like file types to avoid false positives on source/test files
    case "$file" in
        *.md|*.yaml|*.yml|*.txt) ;;
        *) continue ;;
    esac

    # Read the staged blob from the index. Fall back to the working-tree file
    # only when the path is not in the index (e.g. self-test temp files, deleted
    # paths). This prevents a working-tree edit after `git add` from hiding a
    # staged bypass token while keeping self-test and edge-case behaviour intact.
    if git cat-file -e ":$file" 2>/dev/null; then
        staged_content="$(git show ":$file")"
    elif [[ -f "$file" ]]; then
        staged_content="$(cat "$file")"
    else
        continue
    fi

    if grep -qiE "$SKIP_PATTERN" <<< "$staged_content"; then
        # Check for explicit allowlist receipt in the staged content (also case-insensitive)
        if grep -qiE "$ALLOWLIST_PATTERN" <<< "$staged_content"; then
            echo "WARNING: [skip-*] token found in $file but explicit approval receipt present — allowed." >&2
            continue
        fi

        echo "ERROR: $file contains a [skip-*] bypass token." >&2
        echo "  Per $RULE_REF, bypass is not permitted without explicit user approval." >&2
        echo "  Fix the gate properly:" >&2
        echo "    1. Add dod_evidence with type: no_deployable_artifact (preferred)" >&2
        echo "    2. For receipt-gate: add Evidence-Source + Evidence-Ticket to PR body and push OCC contract+receipts" >&2
        echo "    3. If truly exceptional, add '# skip-token-allowed: <receipt-id>' with a traceable approval receipt" >&2
        echo "  Ticket: $TICKET_REF" >&2
        FOUND_VIOLATION=1
    fi
done

exit "$FOUND_VIOLATION"
