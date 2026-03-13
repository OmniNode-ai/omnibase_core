#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# check_forbidden_patterns.sh — Scan src/ for decommissioned/forbidden patterns (OMN-4801)
#
# Reads patterns from scripts/validation/decommissioned_patterns.txt (one per line).
# Lines beginning with '#' and empty lines are ignored.
# Exits non-zero if any match is found in src/; prints file:line for each hit.
#
# Usage:
#   ./scripts/check_forbidden_patterns.sh
#   ./scripts/check_forbidden_patterns.sh --scan-dir <dir>
#   ./scripts/check_forbidden_patterns.sh --patterns-file <file>
#
# Exit codes:
#   0 — no forbidden patterns found
#   1 — one or more forbidden patterns detected

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SCAN_DIR="${SCAN_DIR:-${REPO_ROOT}/src}"
PATTERNS_FILE="${PATTERNS_FILE:-${SCRIPT_DIR}/validation/decommissioned_patterns.txt}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --scan-dir)
            SCAN_DIR="$2"
            shift 2
            ;;
        --patterns-file)
            PATTERNS_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [[ ! -f "${PATTERNS_FILE}" ]]; then
    echo "ERROR: patterns file not found: ${PATTERNS_FILE}" >&2
    exit 2
fi

if [[ ! -d "${SCAN_DIR}" ]]; then
    echo "ERROR: scan directory not found: ${SCAN_DIR}" >&2
    exit 2
fi

FOUND=0
RESULTS=()

while IFS= read -r pattern; do
    # Skip comments and empty lines
    [[ -z "${pattern}" || "${pattern}" =~ ^[[:space:]]*# ]] && continue

    while IFS= read -r hit; do
        RESULTS+=("  ${hit}")
        FOUND=1
    done < <(grep -rn --include="*.py" --include="*.sh" --include="*.yaml" --include="*.yml" \
        -F "${pattern}" "${SCAN_DIR}" 2>/dev/null || true)

done < "${PATTERNS_FILE}"

if [[ ${FOUND} -eq 1 ]]; then
    echo "ERROR: Forbidden/decommissioned pattern(s) found in ${SCAN_DIR}:" >&2
    for result in "${RESULTS[@]}"; do
        echo "${result}" >&2
    done
    echo "" >&2
    echo "Remove or replace these references. See scripts/validation/decommissioned_patterns.txt" >&2
    echo "for context on what was decommissioned and why." >&2
    exit 1
fi

echo "OK: No forbidden patterns found in ${SCAN_DIR}"
exit 0
