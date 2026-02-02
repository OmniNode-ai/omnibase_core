#!/usr/bin/env bash
# shellcheck shell=bash
# Architecture Handshake Verification Script
# Verifies installed handshake matches source in omnibase_core
#
# Usage: check-handshake.sh [-q|--quiet] [path-to-omnibase_core]
#
# Auto-detection (when no path provided):
#   1. ./omnibase_core       (CI pattern - repos as subdirectories)
#   2. ../omnibase_core      (local dev - repos as siblings)
#   3. Script's parent dir   (running from within omnibase_core)
#
# Examples:
#   ./check-handshake.sh                          # Auto-detect location
#   ./check-handshake.sh ./omnibase_core          # CI: subdirectory checkout
#   ./check-handshake.sh ../omnibase_core         # Local: sibling repos
#   ./check-handshake.sh /path/to/omnibase_core   # Explicit path
#
# Exit codes:
#   0 - Success (handshake is current)
#   1 - Stale/mismatch (source has changed)
#   2 - Missing files (handshake not installed or source not found)

set -euo pipefail

# Quiet mode flag (suppress INFO messages)
QUIET=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory (used to detect if running from within omnibase_core)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect omnibase_core path
# Tries multiple common locations in order of priority:
#   1. ./omnibase_core (CI pattern - repos checked out as subdirectories)
#   2. ../omnibase_core (local dev pattern - repos are siblings)
#   3. Script's parent directory (running from within omnibase_core itself)
auto_detect_omnibase_core() {
    # CI pattern: omnibase_core checked out as subdirectory
    if [[ -d "./omnibase_core/architecture-handshakes" ]]; then
        echo "./omnibase_core"
        return 0
    fi

    # Local dev pattern: repos are siblings
    if [[ -d "../omnibase_core/architecture-handshakes" ]]; then
        echo "../omnibase_core"
        return 0
    fi

    # Running from within omnibase_core itself
    # SCRIPT_DIR is architecture-handshakes/, parent is omnibase_core
    local parent_dir
    parent_dir="$(dirname "${SCRIPT_DIR}")"
    if [[ -d "${parent_dir}/architecture-handshakes" ]]; then
        echo "${parent_dir}"
        return 0
    fi

    # Not found
    return 1
}

log_success() { echo -e "${GREEN}OK${NC}: $1"; }
log_error() { echo -e "${RED}FAIL${NC}: $1" >&2; }
log_warn() { echo -e "${YELLOW}WARN${NC}: $1"; }
log_info() {
    if [[ "${QUIET}" != "true" ]]; then
        echo "INFO: $1"
    fi
}

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

# Strip metadata block from file content
# Returns content without the metadata block (for comparing to source)
# This handles both legacy files (no metadata) and new files (with metadata)
strip_metadata_block() {
    local file="$1"
    # Remove the metadata block if it exists (from <!-- HANDSHAKE_METADATA to -->)
    #
    # The second sed removes a blank first line if present. This is needed because:
    # - The metadata block format ends with "-->\n\n" (closing tag + blank line)
    # - The blank line after --> is intentional for markdown rendering (separates
    #   the HTML comment from the document content)
    # - After stripping the metadata block, this blank line becomes the first line
    # - We remove it so the stripped content matches the original source file
    sed '/^<!-- HANDSHAKE_METADATA/,/^-->/d' "${file}" | sed '1{/^$/d;}'
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
    echo "Usage: $0 [-q|--quiet] [path-to-omnibase_core]"
    echo ""
    echo "Options:"
    echo "  -q, --quiet            Suppress INFO messages (errors still shown)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Arguments:"
    echo "  path-to-omnibase_core  Path to omnibase_core repo (auto-detected if not provided)"
    echo ""
    echo "Auto-detection order:"
    echo "  1. ./omnibase_core       (CI pattern - repos as subdirectories)"
    echo "  2. ../omnibase_core      (local dev - repos as siblings)"
    echo "  3. Script's parent dir   (running from within omnibase_core)"
    echo ""
    echo "Exit codes:"
    echo "  0 - Success (handshake is current)"
    echo "  1 - Stale/mismatch (source has changed)"
    echo "  2 - Missing files"
    echo ""
    echo "Examples:"
    echo "  $0                            # Auto-detect omnibase_core location"
    echo "  $0 -q                         # Quiet mode (CI-friendly)"
    echo "  $0 ./omnibase_core            # CI: checked out as subdirectory"
    echo "  $0 -q ../omnibase_core        # Quiet mode with explicit path"
    echo "  $0 /path/to/omnibase_core     # Explicit path"
    echo ""
    echo "This script should be run from a repo with an installed handshake at"
    echo ".claude/architecture-handshake.md"
}

main() {
    # Handle flags
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
            *)
                break
                ;;
        esac
    done

    # Get path to omnibase_core
    local omnibase_core_path
    if [[ -n "${1:-}" ]]; then
        # Explicit path provided
        omnibase_core_path="$1"
    else
        # Auto-detect
        omnibase_core_path=$(auto_detect_omnibase_core) || {
            log_error "Cannot find omnibase_core in any standard location"
            log_info "Tried: ./omnibase_core, ../omnibase_core, script parent directory"
            log_info "Provide explicit path: $0 /path/to/omnibase_core"
            exit 2
        }
        log_info "Auto-detected omnibase_core at: ${omnibase_core_path}"
    fi

    # Resolve to absolute path
    if [[ ! "${omnibase_core_path}" = /* ]]; then
        omnibase_core_path="$(cd "$(pwd)" && cd "${omnibase_core_path}" 2>/dev/null && pwd)" || {
            log_error "Cannot resolve omnibase_core path: ${omnibase_core_path}"
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
        # No embedded hash - fall back to content comparison
        # Strip any metadata block before comparing (handles both legacy and new formats)
        log_warn "Installed handshake has no embedded SHA256 (legacy format)"

        # Create temp file with stripped content for hash comparison
        # Trap handles cleanup on exit (success or failure)
        local temp_file installed_content_sha256
        temp_file=$(mktemp)
        trap "rm -f '${temp_file}'" EXIT
        strip_metadata_block "${installed_handshake}" > "${temp_file}"
        installed_content_sha256=$(calculate_sha256 "${temp_file}")

        if [[ "${installed_content_sha256}" == "${current_source_sha256}" ]]; then
            log_success "Handshake for '${repo_name}' matches source (SHA256: ${current_source_sha256:0:12}...)"
            log_info "Consider reinstalling to get embedded hash: ${handshakes_dir}/install.sh ${repo_name}"
            exit 0
        else
            log_error "Handshake is stale. Run: ${handshakes_dir}/install.sh ${repo_name}"
            log_info "Installed content SHA256: ${installed_content_sha256:0:12}..."
            log_info "Source SHA256:            ${current_source_sha256:0:12}..."
            exit 1
        fi
    fi
}

main "$@"
