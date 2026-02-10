#!/usr/bin/env bash
# shellcheck shell=bash
# Architecture Handshake Installer
# Installs repo-specific constraint maps to .claude/architecture-handshake.md
# with SHA256 metadata for CI verification.
#
# Usage: ./install.sh <repo-name> [target-path]
#
# Examples:
#   ./install.sh omnibase_core                    # Install to ../omnibase_core
#   ./install.sh omniclaude /path/to/omniclaude   # Install to specific path
#
# The installed file includes a metadata block:
#   <!-- HANDSHAKE_METADATA
#   source: omnibase_core/architecture-handshakes/repos/{repo}.md
#   source_version: {version from pyproject.toml}
#   source_sha256: {calculated hash}
#   installed_at: {ISO 8601 timestamp}
#   installed_by: {current user}
#   -->

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory (works even if called from different location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS_DIR="${SCRIPT_DIR}/repos"
PYPROJECT_TOML="${SCRIPT_DIR}/../pyproject.toml"

# Supported repos - loaded from shared config.
REPOS_CONF="${SCRIPT_DIR}/repos.conf"

if [[ ! -f "${REPOS_CONF}" ]]; then
    echo "ERROR: repos.conf not found at ${REPOS_CONF}" >&2
    exit 2
fi

# Read repos.conf into array (portable — works on bash 3.2+ for macOS).
# NOTE: Parsing logic duplicated in check-policy-gate.sh — keep both in sync.
SUPPORTED_REPOS=()
while IFS= read -r line; do
    SUPPORTED_REPOS+=("${line}")
done < <(sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//' "${REPOS_CONF}" | grep -v '^$')

if [[ ${#SUPPORTED_REPOS[@]} -eq 0 ]]; then
    echo "ERROR: repos.conf contains no repo entries" >&2
    exit 2
fi

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

# Extract version from pyproject.toml
# Looks for: version = "x.y.z" in the [project] section
get_omnibase_version() {
    if [[ ! -f "${PYPROJECT_TOML}" ]]; then
        echo "unknown"
        return
    fi
    # Extract version from line like: version = "0.12.0"
    # Uses simple pattern that works on both macOS and Linux
    local version
    version=$(grep -E '^version = "' "${PYPROJECT_TOML}" | head -1 | sed 's/.*"\(.*\)".*/\1/')
    if [[ -z "${version}" ]]; then
        echo "unknown"
    else
        echo "${version}"
    fi
}

# Calculate SHA256 hash (cross-platform: macOS vs Linux)
calculate_sha256() {
    local file="$1"
    if command -v shasum &> /dev/null; then
        # macOS
        shasum -a 256 "${file}" | cut -d' ' -f1
    elif command -v sha256sum &> /dev/null; then
        # Linux
        sha256sum "${file}" | cut -d' ' -f1
    else
        log_error "No SHA256 tool found (need shasum or sha256sum)"
        exit 2
    fi
}

# Return current UTC time in ISO 8601 format.
get_iso_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Return the username of the current shell user.
get_current_user() {
    whoami
}

# Generate the HANDSHAKE_METADATA HTML comment block prepended to installed handshakes.
generate_metadata_block() {
    local repo_name="$1"
    local source_file="$2"
    local version sha256 timestamp user

    version=$(get_omnibase_version)
    sha256=$(calculate_sha256 "${source_file}")
    timestamp=$(get_iso_timestamp)
    user=$(get_current_user)

    # Note: The trailing newline after --> is important for markdown rendering
    printf '<!-- HANDSHAKE_METADATA\n'
    printf 'source: omnibase_core/architecture-handshakes/repos/%s.md\n' "${repo_name}"
    printf 'source_version: %s\n' "${version}"
    printf 'source_sha256: %s\n' "${sha256}"
    printf 'installed_at: %s\n' "${timestamp}"
    printf 'installed_by: %s\n' "${user}"
    printf -- '-->\n\n'
}

# Check if the given repo name is in the supported repos list. Returns 0 if supported, 1 otherwise.
is_supported_repo() {
    local repo="$1"
    for supported in "${SUPPORTED_REPOS[@]}"; do
        if [[ "${repo}" == "${supported}" ]]; then
            return 0
        fi
    done
    return 1
}

# Entry point: validate args, install handshake file with metadata to target repo.
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

    # Generate metadata block and combine with source content
    # Note: We call generate_metadata_block directly in the pipeline to preserve
    # trailing newlines (command substitution strips them)
    {
        generate_metadata_block "${repo_name}" "${source_file}"
        cat "${source_file}"
    } > "${dest_file}"

    local version sha256
    version=$(get_omnibase_version)
    sha256=$(calculate_sha256 "${source_file}")

    log_success "Installed architecture handshake for ${repo_name}"
    log_info "Source:  ${source_file}"
    log_info "Dest:    ${dest_file}"
    log_info "Version: ${version}"
    log_info "SHA256:  ${sha256:0:16}..." # Show first 16 chars

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
