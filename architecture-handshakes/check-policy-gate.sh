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
# Non-success conclusions (cancelled, skipped, timed_out, etc.) are treated
# as failures. Manually cancelled runs will show as FAIL.

set -euo pipefail

# --- Configuration -----------------------------------------------------------

GITHUB_ORG="OmniNode-ai"
WORKFLOW_FILENAME="check-handshake.yml"

# Active repos requiring handshake compliance.
# Shared list: edit repos.conf to add/remove repos.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS_CONF="${SCRIPT_DIR}/repos.conf"

# shellcheck source=_parse_repos_conf.sh
source "${SCRIPT_DIR}/_parse_repos_conf.sh"

ACTIVE_REPOS=()
while IFS= read -r line; do
    ACTIVE_REPOS+=("${line}")
done < <(parse_repos_conf "${REPOS_CONF}")

if [[ ${#ACTIVE_REPOS[@]} -eq 0 ]]; then
    echo "ERROR: no repos loaded from ${REPOS_CONF}" >&2
    exit 2
fi

# --- Options -----------------------------------------------------------------

QUIET=false
STRICT=false

# --- Output helpers ----------------------------------------------------------

log_pass()  { printf '  \033[0;32mPASS\033[0m  %s\n' "$1"; }
log_fail()  { printf '  \033[0;31mFAIL\033[0m  %s\n' "$1"; }
log_info()  {
    if [[ "${QUIET}" != "true" ]]; then
        echo "INFO: $1" >&2
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
  4. Add repo name to architecture-handshakes/repos.conf

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

    # Capture stderr separately so we can inspect the HTTP error without
    # polluting the stdout-based conclusion value.
    local api_output api_exit
    local api_stderr
    api_stderr=$(mktemp) || { echo "error"; return 0; }
    # shellcheck disable=SC2064  # Early expansion intentional: captures current api_stderr path.
    trap "rm -f '${api_stderr}'" RETURN

    # Determine the repo's actual default branch via the API.
    local branch
    branch=$(gh api "repos/${full_repo}" --jq '.default_branch // empty' 2>"${api_stderr}") || true
    if [[ -z "${branch}" ]]; then
        log_info "Could not detect default branch for ${repo}, falling back to main"
        branch="main"
    fi

    # Query the latest *completed* workflow run conclusion for check-handshake.yml.
    # The status=completed filter excludes in-progress runs whose conclusion is null.
    api_output=$(gh api \
        "repos/${full_repo}/actions/workflows/${WORKFLOW_FILENAME}/runs?branch=${branch}&status=completed&per_page=1" \
        --jq '.workflow_runs[0].conclusion // empty' \
        2>"${api_stderr}") && api_exit=0 || api_exit=$?

    if [[ ${api_exit} -ne 0 ]]; then
        local err_content
        err_content=$(<"${api_stderr}")

        # gh api returns exit code 1 for HTTP 4xx/5xx errors.
        # A 404 means the workflow file does not exist in the repo.
        if [[ "${err_content}" == *"404"* ]] || [[ "${err_content}" == *"Not Found"* ]]; then
            echo "no_workflow"
        else
            echo "error"
        fi
        return 0
    fi

    # No runs on default branch
    if [[ -z "${api_output}" ]]; then
        echo "no_runs"
        return 0
    fi

    case "${api_output}" in
        success)  echo "pass" ;;
        *)        echo "fail" ;;
    esac
}

# --- Main --------------------------------------------------------------------

# Entry point: parse args, verify prerequisites, run compliance checks for all active repos.
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
                log_fail "${repo} — check-handshake workflow exists but has no runs"
                fail_count=$((fail_count + 1))
                failed_repos+=("${repo}")
                ;;
            error)
                log_fail "${repo} — could not query workflow status (API error)"
                fail_count=$((fail_count + 1))
                failed_repos+=("${repo}")
                ;;
        esac
    done

    echo ""
    echo "=========================================="
    echo "Results: ${pass_count} pass, ${fail_count} fail"
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
