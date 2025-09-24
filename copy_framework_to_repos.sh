#!/bin/bash
# Copy updated framework to all 6 repositories

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
declare SOURCE_DIR=""
declare SUCCESS_COUNT=0
declare FAILURE_COUNT=0
declare FILES_COPIED=0

# Get script directory for anchoring repo paths
declare -r SCRIPT_BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Repository list - use canonicalized paths anchored to script directory
declare -ra REPOS=(
    "$(realpath "$SCRIPT_BASE_DIR/../omnibase_spi" 2>/dev/null || echo "$SCRIPT_BASE_DIR/../omnibase_spi")"
    "$(realpath "$SCRIPT_BASE_DIR/../omniagent" 2>/dev/null || echo "$SCRIPT_BASE_DIR/../omniagent")"
    "$(realpath "$SCRIPT_BASE_DIR/../omnibase_infra" 2>/dev/null || echo "$SCRIPT_BASE_DIR/../omnibase_infra")"
    "$(realpath "$SCRIPT_BASE_DIR/../omniplan" 2>/dev/null || echo "$SCRIPT_BASE_DIR/../omniplan")"
    "$(realpath "$SCRIPT_BASE_DIR/../omnimcp" 2>/dev/null || echo "$SCRIPT_BASE_DIR/../omnimcp")"
    "$(realpath "$SCRIPT_BASE_DIR/../omnimemory" 2>/dev/null || echo "$SCRIPT_BASE_DIR/../omnimemory")"
)

# Files to copy
declare -ra FILES_TO_COPY=(
    "OMNI_ECOSYSTEM_STANDARDIZATION_FRAMEWORK.md"
    "VALIDATION_SCRIPTS.md"
    "ARCHITECTURE_DECISION_RECORDS.md"
)

# Output functions for consistent messaging
print_status() { echo "🔧 $1"; }
print_success() { echo "✅ $1"; }
print_error() { echo "❌ ERROR: $1" >&2; }
print_warning() { echo "⚠️  WARNING: $1" >&2; }

# Validate source files and directory
validate_source_files() {
    # Use script directory as default SOURCE_DIR instead of CWD
    SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local missing_files=0

    print_status "Validating source files in: $SOURCE_DIR"

    for file in "${FILES_TO_COPY[@]}"; do
        local file_path="$SOURCE_DIR/$file"
        if [[ ! -f "$file_path" ]]; then
            print_warning "Source file not found: $file"
            ((missing_files++))
        elif [[ ! -r "$file_path" ]]; then
            print_error "Source file not readable: $file"
            ((missing_files++))
        fi
    done

    if [[ $missing_files -gt 0 ]]; then
        print_error "$missing_files source files are missing or unreadable"
        return 1
    fi

    return 0
}

# Copy files to a single repository
copy_files_to_repo() {
    local repo="$1"
    local repo_name
    repo_name=$(basename "$repo")
    local repo_success=0
    local repo_failures=0

    # Validate repository directory
    if [[ ! -d "$repo" ]]; then
        print_warning "Repository directory not found: $repo"
        return 1
    fi

    if [[ ! -w "$repo" ]]; then
        print_error "Repository directory not writable: $repo"
        return 1
    fi

    print_status "Copying framework files to $repo_name..."

    # Copy each file
    for file in "${FILES_TO_COPY[@]}"; do
        local source_file="$SOURCE_DIR/$file"
        local dest_file="$repo/$file"

        if [[ -f "$source_file" ]]; then
            # Ensure destination directory exists
            local dest_dir="$(dirname "$dest_file")"
            if [[ ! -d "$dest_dir" ]]; then
                if ! mkdir -p "$dest_dir"; then
                    print_error "  Failed to create destination directory: $dest_dir"
                    ((repo_failures++))
                    continue
                fi
            fi

            # Copy with preserved permissions and metadata
            if cp -a "$source_file" "$dest_file"; then
                print_success "  Copied $file to $repo_name"
                ((repo_success++))
                ((FILES_COPIED++))
            else
                print_error "  Failed to copy $file to $repo_name"
                ((repo_failures++))
            fi
        else
            print_warning "  Source file not found: $file"
            ((repo_failures++))
        fi
    done

    if [[ $repo_failures -eq 0 ]]; then
        print_success "Successfully copied all files to $repo_name"
        return 0
    else
        print_error "Failed to copy $repo_failures files to $repo_name"
        return 1
    fi
}

# Main execution
main() {
    print_status "Starting framework files copy to all repositories..."

    # Validate source files exist
    if ! validate_source_files; then
        exit 1
    fi

    print_status "Source directory: $SOURCE_DIR"
    print_status "Files to copy: ${#FILES_TO_COPY[@]}"
    print_status "Target repositories: ${#REPOS[@]}"

    # Process each repository
    for repo in "${REPOS[@]}"; do
        if copy_files_to_repo "$repo"; then
            ((SUCCESS_COUNT++))
        else
            ((FAILURE_COUNT++))
        fi
    done

    # Final status
    print_status "Copy operation completed!"
    print_status "Repositories successful: $SUCCESS_COUNT"
    print_status "Total files copied: $FILES_COPIED"
    if [[ $FAILURE_COUNT -gt 0 ]]; then
        print_warning "Repositories failed: $FAILURE_COUNT"
        exit 1
    else
        print_success "All repositories updated successfully!"
        exit 0
    fi
}

# Run main function
main "$@"
