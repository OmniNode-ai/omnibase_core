#!/bin/bash
# Cross-platform import pattern fixes for ONEX codebase
# Now with dynamic repo detection and portable operations

set -euo pipefail  # Exit on error, unset vars are errors, and fail on pipe errors

# Color output functions
print_status() { echo "🔧 $1"; }
print_success() { echo "✅ $1"; }
print_error() { echo "❌ ERROR: $1" >&2; }
print_warning() { echo "⚠️  WARNING: $1" >&2; }

# Cross-platform detection
detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == cygwin* || "$OSTYPE" == msys* || "$OSTYPE" == mingw* || "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Dynamic repo root detection
get_repo_root() {
    local repo_root
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
    if [[ $? -ne 0 ]]; then
        print_error "Not in a git repository or git not available"
        exit 1
    fi
    if [[ ! -d "$repo_root" ]]; then
        print_error "Repository root not found: $repo_root"
        exit 1
    fi
    echo "$repo_root"
}

# (portable_sed removed; not used)

# Safer file replacement using Python for complex operations
fix_imports_in_file() {
    local file="$1"
    local temp_file="${file}.tmp"

    python3 - "$file" "$temp_file" << 'EOF'
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

    if [[ $? -eq 0 && -f "$temp_file" ]]; then
        mv "$temp_file" "$file"
        return 0
    else
        [[ -f "$temp_file" ]] && rm -f "$temp_file"
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

    # Detect platform and git repo
    local platform
    platform=$(detect_platform)
    local repo_root
    repo_root=$(get_repo_root)

    print_status "Platform: $platform"
    print_status "Repository root: $repo_root"

    # Verify required directories exist
    local src_dir="$repo_root/src/omnibase_core"
    if [[ ! -d "$src_dir" ]]; then
        print_error "Source directory not found: $src_dir"
        exit 1
    fi

    # Check if Python3 is available
    if ! command -v python3 &> /dev/null; then
        print_error "python3 is required but not found in PATH"
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
    local validation_script="$repo_root/scripts/validation/validate-import-patterns.py"
    if [[ -f "$validation_script" ]] && command -v poetry &> /dev/null; then
        print_status "Running validation to check results..."
        cd "$repo_root"

        if poetry run python "$validation_script" src/ --max-violations 0; then
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
