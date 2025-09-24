#!/bin/bash
# Copy scripts directory to all 6 repositories

set -euo pipefail  # Exit on error, unset vars are errors, and fail on pipe errors

# Global variables for better scoping
declare SCRIPT_DIR=""
declare SUCCESS_COUNT=0
declare FAILURE_COUNT=0

# Repository list
declare -ra REPOS=(
    "../omnibase_spi"
    "../omniagent"
    "../omnibase_infra"
    "../omniplan"
    "../omnimcp"
    "../omnimemory"
)

# Output functions for consistent messaging
print_status() { echo "🔧 $1"; }
print_success() { echo "✅ $1"; }
print_error() { echo "❌ ERROR: $1" >&2; }
print_warning() { echo "⚠️  WARNING: $1" >&2; }

# Validate source scripts directory
validate_scripts_directory() {
    SCRIPT_DIR="$(pwd)/scripts"

    if [[ ! -d "$SCRIPT_DIR" ]]; then
        print_error "Scripts directory not found: $SCRIPT_DIR"
        return 1
    fi

    if [[ ! -r "$SCRIPT_DIR" ]]; then
        print_error "Scripts directory not readable: $SCRIPT_DIR"
        return 1
    fi

    return 0
}

# Copy scripts to a single repository
copy_scripts_to_repo() {
    local repo="$1"
    local repo_name
    repo_name=$(basename "$repo")

    # Validate repository directory
    if [[ ! -d "$repo" ]]; then
        print_warning "Repository directory not found: $repo"
        return 1
    fi

    if [[ ! -w "$repo" ]]; then
        print_error "Repository directory not writable: $repo"
        return 1
    fi

    print_status "Copying scripts/ to $repo_name..."

    # Remove existing scripts directory if it exists
    if [[ -d "$repo/scripts" ]]; then
        if ! rm -rf "$repo/scripts" 2>/dev/null; then
            print_error "Failed to remove existing scripts directory in $repo_name"
            return 1
        fi
    fi

    # Copy scripts directory
    if cp -r "$SCRIPT_DIR" "$repo/" 2>/dev/null; then
        print_success "Copied scripts/ directory to $repo_name"
        return 0
    else
        print_error "Failed to copy scripts/ directory to $repo_name"
        return 1
    fi
}

# Main execution
main() {
    print_status "Starting scripts directory copy to all repositories..."

    # Validate scripts directory exists
    if ! validate_scripts_directory; then
        exit 1
    fi

    print_status "Source directory: $SCRIPT_DIR"
    print_status "Target repositories: ${#REPOS[@]}"

    # Process each repository
    for repo in "${REPOS[@]}"; do
        if copy_scripts_to_repo "$repo"; then
            ((SUCCESS_COUNT++))
        else
            ((FAILURE_COUNT++))
        fi
    done

    # Final status
    print_status "Copy operation completed!"
    print_status "Successful: $SUCCESS_COUNT"
    if [[ $FAILURE_COUNT -gt 0 ]]; then
        print_warning "Failed: $FAILURE_COUNT"
        exit 1
    else
        print_success "All repositories updated successfully!"
        exit 0
    fi
}

# Run main function
main "$@"
