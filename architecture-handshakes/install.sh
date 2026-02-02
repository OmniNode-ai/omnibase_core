#!/usr/bin/env bash
# shellcheck shell=bash
# Architecture Handshake Installer
# Installs repo-specific constraint maps to .claude/architecture-handshake.md
#
# Usage: ./install.sh <repo-name> [target-path]
#
# Examples:
#   ./install.sh omnibase_core                    # Install to ../omnibase_core
#   ./install.sh omniclaude /path/to/omniclaude   # Install to specific path

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory (works even if called from different location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS_DIR="${SCRIPT_DIR}/repos"

# Supported repos
SUPPORTED_REPOS=(
    "omnibase_core"
    "omnibase_infra"
    "omnibase_spi"
    "omniclaude"
    "omnidash"
    "omniintelligence"
    "omnimemory"
    "omninode_infra"
)

usage() {
    echo "Architecture Handshake Installer"
    echo ""
    echo "Usage: $0 <repo-name> [target-path]"
    echo ""
    echo "Arguments:"
    echo "  repo-name    Name of the repository (required)"
    echo "  target-path  Path to target repo (default: ../<repo-name>)"
    echo ""
    echo "Supported repos:"
    for repo in "${SUPPORTED_REPOS[@]}"; do
        echo "  - ${repo}"
    done
    echo ""
    echo "Examples:"
    echo "  $0 omnibase_core"
    echo "  $0 omniclaude /Volumes/PRO-G40/Code/omniclaude"
}

log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}!${NC} $1"; }
log_info() { echo "  $1"; }

# Validate repo name
is_supported_repo() {
    local repo="$1"
    for supported in "${SUPPORTED_REPOS[@]}"; do
        if [[ "${repo}" == "${supported}" ]]; then
            return 0
        fi
    done
    return 1
}

main() {
    # Check arguments
    if [[ $# -lt 1 ]]; then
        usage
        exit 1
    fi

    local repo_name="$1"
    # Go up two levels: architecture-handshakes/ -> omnibase_core/ -> Code/
    local code_dir
    code_dir="$(dirname "$(dirname "${SCRIPT_DIR}")")"
    local target_path="${2:-${code_dir}/${repo_name}}"

    # Validate repo name
    if ! is_supported_repo "${repo_name}"; then
        log_error "Unknown repo: ${repo_name}"
        echo ""
        echo "Supported repos:"
        for repo in "${SUPPORTED_REPOS[@]}"; do
            echo "  - ${repo}"
        done
        exit 1
    fi

    # Check source handshake exists
    local source_file="${REPOS_DIR}/${repo_name}.md"
    if [[ ! -f "${source_file}" ]]; then
        log_error "Handshake file not found: ${source_file}"
        exit 1
    fi

    # Validate target repo exists
    if [[ ! -d "${target_path}" ]]; then
        log_error "Target repo not found: ${target_path}"
        exit 1
    fi

    # Warn if target doesn't appear to be a git repo
    if [[ ! -d "${target_path}/.git" ]]; then
        log_warn "Target does not appear to be a git repo: ${target_path}"
    fi

    # Create .claude directory if needed
    local claude_dir="${target_path}/.claude"
    if [[ ! -d "${claude_dir}" ]]; then
        mkdir -p "${claude_dir}"
        log_info "Created ${claude_dir}"
    fi

    # Install handshake
    local dest_file="${claude_dir}/architecture-handshake.md"
    local existed=false
    local temp_backup=""

    # Check if file exists and create temp backup for diff comparison
    if [[ -f "${dest_file}" ]]; then
        existed=true
        temp_backup=$(mktemp)
        cp "${dest_file}" "${temp_backup}"
    fi

    # Copy the handshake file
    cp "${source_file}" "${dest_file}"

    log_success "Installed architecture handshake for ${repo_name}"
    log_info "Source: ${source_file}"
    log_info "Dest:   ${dest_file}"

    # Show update notice and diff info if file was replaced
    if [[ "${existed}" == "true" ]]; then
        if diff -q "${temp_backup}" "${dest_file}" > /dev/null 2>&1; then
            log_info "File unchanged (content identical)"
        else
            log_info "File updated (content changed)"
            # Show summary of changes
            local added removed
            added=$(diff "${temp_backup}" "${dest_file}" | grep -c "^>" || true)
            removed=$(diff "${temp_backup}" "${dest_file}" | grep -c "^<" || true)
            log_info "  +${added} lines added, -${removed} lines removed"
        fi
        # Clean up temp file
        rm -f "${temp_backup}"
    fi
}

main "$@"
