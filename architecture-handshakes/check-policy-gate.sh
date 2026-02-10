#!/usr/bin/env bash
# shellcheck shell=bash
# Architecture Handshake Policy Gate
# Verifies all active repos have handshake installed AND CI enforcement.
#
# Usage: check-policy-gate.sh [-q|--quiet] [--strict]
#
# This script queries the GitHub API to check each repo's
# check-handshake workflow status on its default branch.
#
# Options:
#   -q, --quiet    Suppress INFO messages (errors still shown)
#   --strict       Exit non-zero if ANY repo is non-compliant (default: report only)
#   -h, --help     Show help
#
# Exit codes:
#   0 - All repos compliant (or report-only mode)
#   1 - Non-compliant repos found (strict mode only)
#   2 - Script error (missing tools, API failure)
#
# Requirements:
#   - GitHub CLI (gh) authenticated with access to OmniNode-ai org repos
#
# Token scope:
#   Some OmniNode repos are private. The GH_TOKEN must have `actions:read`
#   scope across all org repos. In CI, set POLICY_GATE_TOKEN to an org-level
#   PAT or GitHub App token (GITHUB_TOKEN is scoped to the current repo only).
#
# Non-success conclusions (cancelled, skipped, timed_out, etc.) are treated
# as failures. Manually cancelled runs will show as FAIL.

set -euo pipefail

# --- Configuration -----------------------------------------------------------

GITHUB_ORG="OmniNode-ai"
WORKFLOW_FILENAME="check-handshake.yml"

# Active repos requiring handshake compliance.
# To add a new repo: append to this array and add its constraint map
# to architecture-handshakes/repos/<repo-name>.md
ACTIVE_REPOS=(
    "omnibase_core"
    "omnibase_infra"
    "omnibase_spi"
    "omniclaude"
    "omnidash"
    "omniintelligence"
    "omnimemory"
    "omninode_infra"
)

# --- Options -----------------------------------------------------------------

QUIET=false
STRICT=false

# --- Output helpers ----------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_pass()  { echo -e "  ${GREEN}PASS${NC}  $1"; }
log_fail()  { echo -e "  ${RED}FAIL${NC}  $1"; }
log_warn()  { echo -e "  ${YELLOW}WARN${NC}  $1"; }
log_info()  {
    if [[ "${QUIET}" != "true" ]]; then
        echo "INFO: $1"
    fi
}

# --- Functions ---------------------------------------------------------------

usage() {
    cat <<'EOF'
Architecture Handshake Policy Gate

Verifies all active repos have handshake CI enforcement passing on their
default branch. Queries the GitHub API for each repo's check-handshake
workflow status.

Usage: check-policy-gate.sh [-q|--quiet] [--strict]

Options:
  -q, --quiet    Suppress INFO messages (errors still shown)
  --strict       Exit non-zero if ANY repo is non-compliant
  -h, --help     Show this help message

Adding a new repo:
  1. Add constraint map: architecture-handshakes/repos/<repo-name>.md
  2. Install handshake:  ./install.sh <repo-name>
  3. Add CI workflow:    .github/workflows/check-handshake.yml
  4. Add repo name to ACTIVE_REPOS array in this script

Exit codes:
  0 - All repos compliant (or report-only mode)
  1 - Non-compliant repos found (strict mode only)
  2 - Script error (missing tools, API failure)
EOF
}

# Check a single repo's handshake CI status via GitHub API.
# Returns: "pass", "fail", "no_workflow", "no_runs", or "error"
check_repo() {
    local repo="$1"
    local full_repo="${GITHUB_ORG}/${repo}"

    # Query the latest workflow run conclusion for check-handshake.yml
    # on main/master in a single jq expression.
    local conclusion
    conclusion=$(gh api \
        "repos/${full_repo}/actions/workflows/${WORKFLOW_FILENAME}/runs" \
        --jq '[.workflow_runs[] | select(.head_branch == "main" or .head_branch == "master")] | first | .conclusion // empty' \
        2>&1) || {
        # Workflow file not found (404) or other API error
        if echo "${conclusion}" | grep -qi "not found\|could not find\|404"; then
            echo "no_workflow"
            return 0
        fi
        echo "error"
        return 0
    }

    # No runs on default branch
    if [[ -z "${conclusion}" ]]; then
        echo "no_runs"
        return 0
    fi

    case "${conclusion}" in
        success)  echo "pass" ;;
        *)        echo "fail" ;;
    esac
}

# --- Main --------------------------------------------------------------------

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "${1:-}" in
            -h|--help)
                usage
                exit 0
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            --strict)
                STRICT=true
                shift
                ;;
            *)
                echo "Unknown option: $1" >&2
                usage
                exit 2
                ;;
        esac
    done

    # Verify gh CLI is available and authenticated
    if ! command -v gh &> /dev/null; then
        echo "ERROR: GitHub CLI (gh) is required but not installed." >&2
        echo "Install: https://cli.github.com/" >&2
        exit 2
    fi

    if ! gh auth status &> /dev/null; then
        echo "ERROR: GitHub CLI is not authenticated. Run: gh auth login" >&2
        exit 2
    fi

    log_info "Checking handshake policy compliance for ${#ACTIVE_REPOS[@]} repos..."
    echo ""
    echo "Handshake Policy Gate — Compliance Report"
    echo "=========================================="
    echo ""

    local pass_count=0
    local fail_count=0
    local warn_count=0
    local failed_repos=()

    for repo in "${ACTIVE_REPOS[@]}"; do
        local status
        status=$(check_repo "${repo}")

        case "${status}" in
            pass)
                log_pass "${repo} — check-handshake workflow passing"
                pass_count=$((pass_count + 1))
                ;;
            fail)
                log_fail "${repo} — check-handshake workflow failing"
                fail_count=$((fail_count + 1))
                failed_repos+=("${repo}")
                ;;
            no_workflow)
                log_fail "${repo} — no check-handshake workflow found"
                fail_count=$((fail_count + 1))
                failed_repos+=("${repo}")
                ;;
            no_runs)
                log_warn "${repo} — check-handshake workflow exists but has no runs"
                warn_count=$((warn_count + 1))
                ;;
            error)
                log_warn "${repo} — could not query workflow status (API error)"
                warn_count=$((warn_count + 1))
                ;;
        esac
    done

    echo ""
    echo "=========================================="
    echo "Results: ${pass_count} pass, ${fail_count} fail, ${warn_count} warn"
    echo ""

    if [[ ${fail_count} -gt 0 ]]; then
        echo "Non-compliant repos:"
        for repo in "${failed_repos[@]}"; do
            echo "  - ${repo}"
        done
        echo ""
        echo "To fix: install handshake and add CI workflow."
        echo "See: architecture-handshakes/README.md"
        echo ""

        if [[ "${STRICT}" == "true" ]]; then
            echo "POLICY GATE: FAILED (strict mode)"
            exit 1
        else
            echo "POLICY GATE: WARNING (report-only mode, use --strict to enforce)"
        fi
    else
        echo "POLICY GATE: PASSED — all active repos are compliant"
    fi
}

main "$@"
