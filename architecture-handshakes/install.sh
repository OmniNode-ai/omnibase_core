#!/usr/bin/env bash
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

    # Create .claude directory if needed
    local claude_dir="${target_path}/.claude"
    if [[ ! -d "${claude_dir}" ]]; then
        mkdir -p "${claude_dir}"
        log_info "Created ${claude_dir}"
    fi

    # Install handshake
    local dest_file="${claude_dir}/architecture-handshake.md"
    cp "${source_file}" "${dest_file}"

    log_success "Installed architecture handshake for ${repo_name}"
    log_info "Source: ${source_file}"
    log_info "Dest:   ${dest_file}"

    # Show diff if file already existed
    if command -v diff &> /dev/null && [[ -f "${dest_file}" ]]; then
        if ! diff -q "${source_file}" "${dest_file}" &> /dev/null; then
            log_warn "File was updated (content changed)"
        fi
    fi
}

main "$@"
