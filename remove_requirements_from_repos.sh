#!/bin/bash
# Remove requirements.txt from scripts/validation/ in all repositories

set -euo pipefail  # Exit on error, unset vars are errors, and fail on pipe errors

# Enhanced error handling with ERR trap for better diagnosis
cleanup_on_error() {
    local exit_code=$?
    local line_number=$1
    print_error "Script failed at line $line_number with exit code $exit_code"
    print_error "Failed command was: ${BASH_COMMAND}"
    exit $exit_code
}
trap 'cleanup_on_error $LINENO' ERR

# Global variables for better scoping
declare FOUND_COUNT=0
declare REMOVED_COUNT=0
declare NOT_FOUND_COUNT=0
declare ERROR_COUNT=0

# Get script directory for anchoring repo paths
declare -r SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Repository list - anchor paths to script directory to avoid CWD breakage
declare -ra REPOS=(
    "$SCRIPT_DIR/../omnibase_spi"
    "$SCRIPT_DIR/../omniagent"
    "$SCRIPT_DIR/../omnibase_infra"
    "$SCRIPT_DIR/../omniplan"
    "$SCRIPT_DIR/../omnimcp"
    "$SCRIPT_DIR/../omnimemory"
)

# File path to remove
declare -r REQUIREMENTS_PATH="scripts/validation/requirements.txt"

# Output functions for consistent messaging
print_status() { echo "🔧 $1"; }
print_success() { echo "✅ $1"; }
print_error() { echo "❌ ERROR: $1" >&2; }
print_warning() { echo "⚠️  WARNING: $1" >&2; }
print_info() { echo "ℹ️  $1"; }

# Remove requirements.txt from a single repository
remove_requirements_from_repo() {
    local repo="$1"
    local repo_name
    repo_name=$(basename "$repo")
    local requirements_file="$repo/$REQUIREMENTS_PATH"

    # Validate repository directory
    if [[ ! -d "$repo" ]]; then
        print_warning "Repository directory not found: $repo"
        ((ERROR_COUNT++))
        return 1
    fi

    # Check if requirements.txt exists
    if [[ ! -f "$requirements_file" ]]; then
        print_info "No requirements.txt found in $repo_name"
        ((NOT_FOUND_COUNT++))
        return 0
    fi

    ((FOUND_COUNT++))

    # Validate the file is writable (can be deleted)
    if [[ ! -w "$requirements_file" ]]; then
        print_error "Requirements.txt not writable/deletable in $repo_name"
        ((ERROR_COUNT++))
        return 1
    fi

    # Attempt to remove the file (safer removal with --)
    if rm -f -- "$requirements_file"; then
        print_success "Removed requirements.txt from $repo_name"
        ((REMOVED_COUNT++))
        return 0
    else
        print_error "Failed to remove requirements.txt from $repo_name"
        ((ERROR_COUNT++))
        return 1
    fi
}

# Main execution
main() {
    print_status "Starting requirements.txt cleanup from all repositories..."

    print_status "Target file: $REQUIREMENTS_PATH"
    print_status "Target repositories: ${#REPOS[@]}"

    # Process each repository
    for repo in "${REPOS[@]}"; do
        remove_requirements_from_repo "$repo"
    done

    # Final status report
    print_status "Cleanup operation completed!"
    print_status "Repositories processed: ${#REPOS[@]}"
    print_status "Requirements.txt found: $FOUND_COUNT"
    print_status "Successfully removed: $REMOVED_COUNT"
    print_status "Not found: $NOT_FOUND_COUNT"

    if [[ $ERROR_COUNT -gt 0 ]]; then
        print_warning "Errors encountered: $ERROR_COUNT"
        print_error "Some operations failed"
        exit 1
    else
        print_success "All operations completed successfully!"
        exit 0
    fi
}

# Run main function
main "$@"
