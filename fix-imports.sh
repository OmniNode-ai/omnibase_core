#!/bin/bash
# Cross-platform import pattern fixes for ONEX codebase
# Now with dynamic repo detection and portable operations

set -euo pipefail  # Exit on error, unset vars are errors, and fail on pipe errors

# Global variables for better scoping
declare REPO_ROOT=""
declare PLATFORM=""
declare PYTHON_CMD=""

# Color output functions
print_status() { echo "🔧 $1"; }
print_success() { echo "✅ $1"; }
print_error() { echo "❌ ERROR: $1" >&2; }
print_warning() { echo "⚠️  WARNING: $1" >&2; }

# Cross-platform detection with enhanced error handling
detect_platform() {
    local detected_platform=""

    if [[ -n "${OSTYPE:-}" ]]; then
        case "$OSTYPE" in
            darwin*)
                detected_platform="macos"
                ;;
            linux-gnu*|linux*)
                detected_platform="linux"
                ;;
            cygwin*|msys*|mingw*|win32)
                detected_platform="windows"
                ;;
            *)
                detected_platform="unknown"
                ;;
        esac
    else
        # Fallback detection if OSTYPE is not set
        if command -v uname >/dev/null 2>&1; then
            local uname_result
            uname_result=$(uname -s 2>/dev/null || echo "unknown")
            case "$uname_result" in
                Darwin)
                    detected_platform="macos"
                    ;;
                Linux)
                    detected_platform="linux"
                    ;;
                CYGWIN*|MINGW*|MSYS*)
                    detected_platform="windows"
                    ;;
                *)
                    detected_platform="unknown"
                    ;;
            esac
        else
            detected_platform="unknown"
        fi
    fi

    if [[ "$detected_platform" == "unknown" ]]; then
        print_warning "Could not detect platform, assuming POSIX-compatible"
        detected_platform="posix"
    fi

    echo "$detected_platform"
}

# Dynamic repo root detection with enhanced error handling
get_repo_root() {
    local repo_root=""
    local git_exit_code=0

    # Check if git is available first
    if ! command -v git >/dev/null 2>&1; then
        print_error "Git is not available in PATH"
        return 1
    fi

    # Try to get the repository root
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || git_exit_code=$?

    if [[ $git_exit_code -ne 0 ]]; then
        print_error "Not in a git repository or git command failed (exit code: $git_exit_code)"
        return 1
    fi

    # Validate the repository root exists and is accessible
    if [[ -z "$repo_root" ]]; then
        print_error "Git returned empty repository root"
        return 1
    fi

    if [[ ! -d "$repo_root" ]]; then
        print_error "Repository root directory not found or not accessible: $repo_root"
        return 1
    fi

    # Ensure we have read access
    if [[ ! -r "$repo_root" ]]; then
        print_error "Repository root is not readable: $repo_root"
        return 1
    fi

    echo "$repo_root"
    return 0
}

# Python command detection with cross-platform compatibility
detect_python_command() {
    local python_candidates=("python3" "python" "py")
    local detected_python=""

    for cmd in "${python_candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            # Verify it's actually Python 3
            local python_version
            python_version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}')" 2>/dev/null || echo "0")
            if [[ "$python_version" == "3" ]]; then
                detected_python="$cmd"
                break
            fi
        fi
    done

    if [[ -z "$detected_python" ]]; then
        print_error "Python 3 is required but not found in PATH"
        return 1
    fi

    echo "$detected_python"
    return 0
}

# Safer file replacement using Python for complex operations
fix_imports_in_file() {
    local file="$1"
    local temp_file=""
    local python_exit_code=0

    # Input validation
    if [[ -z "$file" ]]; then
        print_error "No file specified for import fixing"
        return 1
    fi

    if [[ ! -f "$file" ]]; then
        print_error "File not found: $file"
        return 1
    fi

    if [[ ! -r "$file" ]]; then
        print_error "File not readable: $file"
        return 1
    fi

    if [[ ! -w "$(dirname "$file")" ]]; then
        print_error "Directory not writable: $(dirname "$file")"
        return 1
    fi

    # Validate Python command is available
    if [[ -z "$PYTHON_CMD" ]]; then
        print_error "Python command not detected"
        return 1
    fi

    # Set temp file name
    temp_file="${file}.tmp.$$"

    # Ensure temp file cleanup on exit
    trap 'rm -f "$temp_file" 2>/dev/null || true' EXIT

    "$PYTHON_CMD" - "$file" "$temp_file" << 'EOF' || python_exit_code=$?
import sys
import re

def fix_import_patterns(content):
    """Fix import patterns using regex replacements."""

    # Define replacement patterns
    patterns = [
        # Triple-dot imports
        (r'from \.\.\.enums\.', 'from omnibase_core.enums.'),
        (r'from \.\.\.exceptions\.', 'from omnibase_core.exceptions.'),
        (r'from \.\.\.protocols_local\.', 'from omnibase_core.protocols_local.'),
        (r'from \.\.\.utils\.', 'from omnibase_core.utils.'),
        (r'from \.\.\.models\.', 'from omnibase_core.models.'),

        # Double-dot imports to models subdirectories
        (r'from \.\.common\.', 'from omnibase_core.models.common.'),
        (r'from \.\.metadata\.', 'from omnibase_core.models.metadata.'),
        (r'from \.\.infrastructure\.', 'from omnibase_core.models.infrastructure.'),
        (r'from \.\.core\.', 'from omnibase_core.models.core.'),
        (r'from \.\.connections\.', 'from omnibase_core.models.connections.'),
        (r'from \.\.nodes\.', 'from omnibase_core.models.nodes.'),
    ]

    # Apply replacements
    for old_pattern, replacement in patterns:
        content = re.sub(old_pattern, replacement, content)

    return content

if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        fixed_content = fix_import_patterns(content)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

    except Exception as e:
        print(f"Error processing {input_file}: {e}", file=sys.stderr)
        sys.exit(1)
EOF

    # Check Python script execution result
    if [[ $python_exit_code -ne 0 ]]; then
        print_error "Python script failed with exit code: $python_exit_code"
        return 1
    fi

    # Verify temp file was created successfully
    if [[ ! -f "$temp_file" ]]; then
        print_error "Temporary file was not created: $temp_file"
        return 1
    fi

    # Verify temp file is not empty (basic sanity check)
    if [[ ! -s "$temp_file" ]]; then
        print_warning "Temporary file is empty, skipping replacement: $temp_file"
        return 1
    fi

    # Atomically replace the original file
    if mv "$temp_file" "$file" 2>/dev/null; then
        # Clear the trap since we successfully moved the file
        trap - EXIT
        return 0
    else
        print_error "Failed to replace file: $file"
        return 1
    fi
}

# Process directory with import fixes
fix_directory_imports() {
    local dir_path="$1"
    local dir_name
    dir_name=$(basename "$dir_path")

    if [[ ! -d "$dir_path" ]]; then
        print_warning "Directory not found: $dir_path"
        return 1
    fi

    print_status "Processing $dir_name directory..."

    local processed=0
    local failed=0
    local found_any=0

    # Use NUL-delimited stream to handle spaces/newlines in paths
    while IFS= read -r -d '' file; do
        found_any=1
        if fix_imports_in_file "$file"; then
            ((processed++))
        else
            print_warning "Failed to process: $file"
            ((failed++))
        fi
    done < <(find "$dir_path" -type f -name '*.py' -print0 2>/dev/null)

    if [[ $found_any -eq 0 ]]; then
        print_warning "No Python files found in $dir_path"
        return 0
    fi

    if [[ $failed -eq 0 ]]; then
        print_success "$dir_name directory fixed ($processed files)"
    else
        print_warning "$dir_name directory processed with $failed failures ($processed successes)"
    fi

    return $failed
}

# Main execution
main() {
    print_status "Starting cross-platform import pattern fixes..."

    # Initialize global variables
    PLATFORM=$(detect_platform) || {
        print_error "Failed to detect platform"
        exit 1
    }

    REPO_ROOT=$(get_repo_root) || {
        print_error "Failed to get repository root"
        exit 1
    }

    PYTHON_CMD=$(detect_python_command) || {
        print_error "Failed to detect Python command"
        exit 1
    }

    print_status "Platform: $PLATFORM"
    print_status "Repository root: $REPO_ROOT"
    print_status "Python command: $PYTHON_CMD"

    # Verify required directories exist
    local src_dir="$REPO_ROOT/src/omnibase_core"
    if [[ ! -d "$src_dir" ]]; then
        print_error "Source directory not found: $src_dir"
        exit 1
    fi

    # Save original directory
    local original_dir
    original_dir=$(pwd)
    trap 'cd "$original_dir" > /dev/null 2>&1 || true' EXIT
    local total_failures=0

    # Define directories to process (with their expected violation counts in comments)
    local directories=(
        "$src_dir/models/config"        # 54 violations
        "$src_dir/models/nodes"         # 108 violations
        "$src_dir/models/cli"           # 92 violations
        "$src_dir/models/metadata"      # 83 violations
        "$src_dir/models/core"          # 51 violations
        "$src_dir/models/connections"   # 26 violations
        "$src_dir/models/infrastructure" # 46 violations
        "$src_dir/models/contracts"     # 3 violations
        "$src_dir/models/validation"    # 8 violations
        "$src_dir/models/common"        # 24 violations
        "$src_dir/models/utils"         # 1 violation
    )

    # Process each directory
    for dir_path in "${directories[@]}"; do
        if ! fix_directory_imports "$dir_path"; then
            ((total_failures++))
        fi
    done

    # Return to original directory
    cd "$original_dir"

    print_success "All directories processed!"

    # Run validation if available
    local validation_script="$REPO_ROOT/scripts/validation/validate-import-patterns.py"
    if [[ -f "$validation_script" ]] && command -v poetry >/dev/null 2>&1; then
        print_status "Running validation to check results..."
        cd "$REPO_ROOT" || {
            print_error "Failed to change to repository root directory"
            return 1
        }

        if poetry run python "$validation_script" src/ --max-violations 0 2>/dev/null; then
            print_success "Validation passed - all import patterns fixed!"
        else
            print_warning "Validation found remaining issues - manual review may be needed"
            total_failures=$((total_failures + 1))
        fi
    else
        print_warning "Validation script not found or poetry not available - skipping validation"
    fi

    # Final status
    if [[ $total_failures -eq 0 ]]; then
        print_success "Import fixes completed successfully!"
        exit 0
    else
        print_error "Import fixes completed with $total_failures issues"
        exit 1
    fi
}

# Run main function
main "$@"
