#!/usr/bin/env bash
# shellcheck shell=bash
# Architecture Handshake Verification Script
# Verifies installed handshake matches source in omnibase_core
#
# Usage: check-handshake.sh [path-to-omnibase_core]
#
# Examples:
#   ./check-handshake.sh                          # Use default ../omnibase_core
#   ./check-handshake.sh /path/to/omnibase_core   # Use specific path
#
# Exit codes:
#   0 - Success (handshake is current)
#   1 - Stale/mismatch (source has changed)
#   2 - Missing files (handshake not installed or source not found)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default path to omnibase_core (relative to current working directory)
DEFAULT_OMNIBASE_CORE="../omnibase_core"

log_success() { echo -e "${GREEN}OK${NC}: $1"; }
log_error() { echo -e "${RED}FAIL${NC}: $1" >&2; }
log_warn() { echo -e "${YELLOW}WARN${NC}: $1"; }
log_info() { echo "INFO: $1"; }

# Cross-platform SHA256 calculation
calculate_sha256() {
    local file="$1"
    if command -v shasum &> /dev/null; then
        # macOS
        shasum -a 256 "$file" | cut -d' ' -f1
    elif command -v sha256sum &> /dev/null; then
        # Linux
        sha256sum "$file" | cut -d' ' -f1
    else
        log_error "No SHA256 tool found (need shasum or sha256sum)"
        exit 2
    fi
}

# Extract repo name from handshake header or metadata
# Looks for: # OmniNode Architecture – Constraint Map (repo_name)
# Or metadata: source: omnibase_core/architecture-handshakes/repos/<repo_name>.md
extract_repo_name() {
    local file="$1"
    local repo_name

    # Try to extract from header line (may be after metadata block)
    # Note: don't use ^ anchor as header may be preceded by metadata block end marker
    repo_name=$(grep -m1 "# OmniNode Architecture" "$file" | sed -n 's/.*(\([^)]*\)).*/\1/p')

    if [[ -z "${repo_name}" ]]; then
        # Try to extract from metadata source field
        # source: omnibase_core/architecture-handshakes/repos/<repo_name>.md
        repo_name=$(grep -m1 "^source:" "$file" | sed -n 's|.*/repos/\([^.]*\)\.md.*|\1|p')
    fi

    if [[ -z "${repo_name}" ]]; then
        return 1
    fi

    echo "${repo_name}"
}

# Extract source_sha256 from installed handshake
# Handles multiple formats:
# - Metadata block: source_sha256: <hash>
# - Markdown: > **Source SHA256**: <hash>
extract_source_sha256() {
    local file="$1"
    local sha256

    # Try YAML-style in metadata block: source_sha256: <hash>
    # Note: may have leading whitespace in metadata block
    sha256=$(grep -m1 "source_sha256:" "$file" | sed -n 's/.*source_sha256: *\([a-f0-9]\{64\}\).*/\1/p')

    if [[ -z "${sha256}" ]]; then
        # Try markdown format: > **Source SHA256**: <hash>
        sha256=$(grep -m1 "Source SHA256" "$file" | sed -n 's/.*: *\([a-f0-9]\{64\}\).*/\1/p')
    fi

    if [[ -z "${sha256}" ]]; then
        return 1
    fi

    echo "${sha256}"
}

usage() {
    echo "Architecture Handshake Verification Script"
    echo ""
    echo "Usage: $0 [path-to-omnibase_core]"
    echo ""
    echo "Arguments:"
    echo "  path-to-omnibase_core  Path to omnibase_core repo (default: ../omnibase_core)"
    echo ""
    echo "Exit codes:"
    echo "  0 - Success (handshake is current)"
    echo "  1 - Stale/mismatch (source has changed)"
    echo "  2 - Missing files"
    echo ""
    echo "Examples:"
    echo "  $0                            # Check using default path"
    echo "  $0 /path/to/omnibase_core     # Check using specific path"
    echo ""
    echo "This script should be run from a repo with an installed handshake at"
    echo ".claude/architecture-handshake.md"
}

main() {
    # Handle help flag
    if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
        usage
        exit 0
    fi

    # Get path to omnibase_core
    local omnibase_core_path="${1:-${DEFAULT_OMNIBASE_CORE}}"

    # Resolve to absolute path
    if [[ ! "${omnibase_core_path}" = /* ]]; then
        omnibase_core_path="$(cd "$(pwd)" && cd "${omnibase_core_path}" 2>/dev/null && pwd)" || {
            log_error "Cannot resolve omnibase_core path: ${1:-${DEFAULT_OMNIBASE_CORE}}"
            log_info "Make sure omnibase_core exists at the specified location"
            exit 2
        }
    fi

    # Check omnibase_core exists
    if [[ ! -d "${omnibase_core_path}" ]]; then
        log_error "omnibase_core not found at: ${omnibase_core_path}"
        exit 2
    fi

    # Check handshakes directory exists
    local handshakes_dir="${omnibase_core_path}/architecture-handshakes"
    if [[ ! -d "${handshakes_dir}" ]]; then
        log_error "Handshakes directory not found: ${handshakes_dir}"
        exit 2
    fi

    # Check installed handshake exists
    local installed_handshake=".claude/architecture-handshake.md"
    if [[ ! -f "${installed_handshake}" ]]; then
        log_error "No handshake installed. Run: ${handshakes_dir}/install.sh <repo-name>"
        exit 2
    fi

    # Extract repo name from installed handshake
    local repo_name
    repo_name=$(extract_repo_name "${installed_handshake}") || {
        log_error "Cannot determine repo name from installed handshake"
        log_info "Expected header: # OmniNode Architecture – Constraint Map (<repo-name>)"
        exit 2
    }

    # Check source handshake exists
    local source_handshake="${handshakes_dir}/repos/${repo_name}.md"
    if [[ ! -f "${source_handshake}" ]]; then
        log_error "Source handshake not found in omnibase_core: ${source_handshake}"
        log_info "Repo '${repo_name}' may not be supported or handshake was removed"
        exit 2
    fi

    # Try to extract embedded source_sha256 from installed file
    local embedded_sha256
    embedded_sha256=$(extract_source_sha256 "${installed_handshake}") || embedded_sha256=""

    # Calculate current source hash
    local current_source_sha256
    current_source_sha256=$(calculate_sha256 "${source_handshake}")

    if [[ -n "${embedded_sha256}" ]]; then
        # Compare embedded hash to current source hash
        if [[ "${embedded_sha256}" == "${current_source_sha256}" ]]; then
            log_success "Handshake for '${repo_name}' is current (SHA256: ${current_source_sha256:0:12}...)"
            exit 0
        else
            log_error "Handshake is stale. Run: ${handshakes_dir}/install.sh ${repo_name}"
            log_info "Installed SHA256: ${embedded_sha256:0:12}..."
            log_info "Current SHA256:   ${current_source_sha256:0:12}..."
            exit 1
        fi
    else
        # No embedded hash - fall back to direct file comparison
        log_warn "Installed handshake has no embedded SHA256 (legacy format)"

        # Calculate hash of installed file for comparison
        local installed_sha256
        installed_sha256=$(calculate_sha256 "${installed_handshake}")

        if [[ "${installed_sha256}" == "${current_source_sha256}" ]]; then
            log_success "Handshake for '${repo_name}' matches source (SHA256: ${current_source_sha256:0:12}...)"
            log_info "Consider reinstalling to get embedded hash: ${handshakes_dir}/install.sh ${repo_name}"
            exit 0
        else
            log_error "Handshake is stale. Run: ${handshakes_dir}/install.sh ${repo_name}"
            log_info "Installed SHA256: ${installed_sha256:0:12}..."
            log_info "Source SHA256:    ${current_source_sha256:0:12}..."
            exit 1
        fi
    fi
}

main "$@"
