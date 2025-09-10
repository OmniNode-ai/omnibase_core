#!/usr/bin/env python3
"""
Fix semi-redundant to_dict() methods by removing them and updating callers.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# List of semi-redundant methods from our analysis
SEMI_REDUNDANT_FILES = [
    "src/omnibase_core/core/errors/core_errors.py",
    "src/omnibase_core/model/configuration/model_git_hub_issues_event.py",
    "src/omnibase_core/model/configuration/model_health_check_config.py",
    "src/omnibase_core/model/configuration/model_pool_recommendations.py",
    "src/omnibase_core/model/configuration/model_latency_profile.py",
    "src/omnibase_core/model/configuration/model_git_hub_issue_comment_event.py",
    "src/omnibase_core/model/configuration/model_git_hub_release_event.py",
    "src/omnibase_core/model/configuration/model_parsed_connection_info.py",
    "src/omnibase_core/model/configuration/model_cache_settings.py",
    "src/omnibase_core/model/core/model_trend_data.py",
    "src/omnibase_core/model/core/model_performance_profile.py",
    "src/omnibase_core/model/core/model_masked_connection_properties.py",
    "src/omnibase_core/model/core/model_generic_metadata.py",
    "src/omnibase_core/model/core/model_error_summary.py",
    "src/omnibase_core/model/core/model_business_impact.py",
    "src/omnibase_core/model/core/model_node_information.py",
    "src/omnibase_core/model/core/model_connection_properties.py",  # Has 3 methods
    "src/omnibase_core/model/core/model_security_assessment.py",
    "src/omnibase_core/model/core/model_resource_allocation.py",
    "src/omnibase_core/model/core/model_health_check_result.py",
    "src/omnibase_core/model/core/model_custom_filter_base.py",
    "src/omnibase_core/model/core/model_audit_entry.py",
    "src/omnibase_core/model/core/model_performance_summary.py",
    "src/omnibase_core/model/core/model_monitoring_metrics.py",
    "src/omnibase_core/model/core/model_orchestrator_info.py",
    "src/omnibase_core/model/security/model_security_context.py",
    "src/omnibase_core/model/security/model_password_policy.py",
    "src/omnibase_core/model/security/model_session_policy.py",
    "src/omnibase_core/model/security/model_network_restrictions.py",
    "src/omnibase_core/model/service/model_error_details.py",
    "src/omnibase_core/model/generation/model_cli_command.py",
    "src/omnibase_core/model/generation/model_contract_document.py",
]


def extract_class_name_from_file(file_path: Path) -> str:
    """Extract the primary class name from a model file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Look for class definitions, prefer ones that match file naming convention
    class_matches = re.findall(r"class\s+(\w+)\s*\([^)]*\):", content)
    if not class_matches:
        return ""

    # Prefer classes with "Model" prefix that match the filename pattern
    file_name = file_path.stem  # e.g., "model_trend_data"
    expected_class = "".join(
        word.capitalize() for word in file_name.split("_")
    )  # "ModelTrendData"

    if expected_class in class_matches:
        return expected_class

    # Fallback to first class found
    return class_matches[0]


def find_to_dict_method(content: str) -> Tuple[int, int, str]:
    """
    Find the to_dict method in content and return its start line, end line, and parameters.
    Returns (start_line, end_line, params) or (0, 0, "") if not found.
    """
    lines = content.split("\n")

    for i, line in enumerate(lines):
        if re.search(r"def\s+to_dict\s*\(", line):
            start_line = i

            # Extract parameters from method signature
            params_match = re.search(r"def\s+to_dict\s*\((.*?)\):", line)
            params = params_match.group(1) if params_match else "self"

            # Find method end by tracking indentation
            method_indent = len(line) - len(line.lstrip())
            end_line = start_line

            for j in range(start_line + 1, len(lines)):
                current_line = lines[j]
                if current_line.strip() == "":
                    continue

                current_indent = len(current_line) - len(current_line.lstrip())

                # If we hit a line with same or less indentation, we've reached the end
                if current_indent <= method_indent:
                    end_line = j - 1
                    break
            else:
                # Reached end of file
                end_line = len(lines) - 1

            return (start_line, end_line, params)

    return (0, 0, "")


def analyze_to_dict_method(content: str, start_line: int, end_line: int) -> dict:
    """Analyze what the to_dict method does to determine replacement strategy."""
    lines = content.split("\n")
    method_lines = lines[start_line : end_line + 1]
    method_body = "\n".join(method_lines)

    # Check for specific patterns
    has_model_dump = "model_dump(" in method_body
    has_exclude_none = "exclude_none=True" in method_body
    has_exclude_unset = "exclude_unset=True" in method_body
    is_simple_return = (
        len(
            [
                l
                for l in method_lines
                if l.strip()
                and not l.strip().startswith('"""')
                and not l.strip().startswith("#")
                and "def to_dict" not in l
            ]
        )
        <= 1
    )

    return {
        "has_model_dump": has_model_dump,
        "has_exclude_none": has_exclude_none,
        "has_exclude_unset": has_exclude_unset,
        "is_simple_return": is_simple_return,
        "method_body": method_body,
    }


def determine_model_dump_replacement(analysis: dict) -> str:
    """Determine the appropriate model_dump() replacement based on method analysis."""
    if analysis["has_exclude_none"]:
        return "model_dump(exclude_none=True)"
    elif analysis["has_exclude_unset"]:
        return "model_dump(exclude_unset=True)"
    else:
        return "model_dump()"


def remove_to_dict_method(file_path: Path) -> bool:
    """Remove the to_dict method from a file if it's semi-redundant."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Find the to_dict method
        start_line, end_line, params = find_to_dict_method(content)
        if start_line == 0:
            print(f"  ⚠️  No to_dict method found in {file_path}")
            return False

        # Analyze the method
        analysis = analyze_to_dict_method(content, start_line, end_line)

        # Verify it's actually semi-redundant
        if not (analysis["has_model_dump"] and analysis["is_simple_return"]):
            print(f"  ⚠️  Method in {file_path} doesn't look semi-redundant, skipping")
            return False

        # Remove the method
        lines = content.split("\n")
        new_lines = lines[:start_line] + lines[end_line + 1 :]
        new_content = "\n".join(new_lines)

        # Write back the file
        with open(file_path, "w") as f:
            f.write(new_content)

        print(f"  ✅ Removed to_dict() method from {file_path}")
        return True

    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False


def find_callers_in_file(file_path: Path, class_name: str) -> List[Tuple[int, str]]:
    """Find places in a file where ClassName.to_dict() or instance.to_dict() might be called."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        lines = content.split("\n")
        callers = []

        for i, line in enumerate(lines, 1):
            # Look for .to_dict() calls - be conservative and catch various patterns
            if ".to_dict()" in line:
                callers.append((i, line.strip()))

        return callers

    except Exception:
        return []


def update_callers_in_file(file_path: Path, model_dump_replacement: str) -> int:
    """Update .to_dict() calls to use model_dump() in a file."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Count replacements made
        original_count = content.count(".to_dict()")

        # Replace all .to_dict() with appropriate model_dump call
        new_content = content.replace(".to_dict()", f".{model_dump_replacement}")

        if new_content != content:
            with open(file_path, "w") as f:
                f.write(new_content)

        replacement_count = original_count - new_content.count(".to_dict()")
        return replacement_count

    except Exception as e:
        print(f"  ❌ Error updating callers in {file_path}: {e}")
        return 0


def main():
    """Main function to fix semi-redundant to_dict methods."""
    print("🔧 Fixing semi-redundant to_dict() methods...")

    removed_methods = 0
    updated_callers = 0

    for file_path_str in SEMI_REDUNDANT_FILES:
        file_path = Path(file_path_str)

        if not file_path.exists():
            print(f"  ⚠️  File not found: {file_path}")
            continue

        print(f"\n📁 Processing {file_path}")

        # First, analyze what model_dump parameters we need
        with open(file_path, "r") as f:
            content = f.read()

        start_line, end_line, params = find_to_dict_method(content)
        if start_line == 0:
            print(f"  ⚠️  No to_dict method found")
            continue

        analysis = analyze_to_dict_method(content, start_line, end_line)
        replacement = determine_model_dump_replacement(analysis)

        print(f"  📝 Will replace .to_dict() with .{replacement}")

        # Remove the method definition
        if remove_to_dict_method(file_path):
            removed_methods += 1

        # Update callers in the same file
        callers_updated = update_callers_in_file(file_path, replacement)
        if callers_updated > 0:
            print(f"  🔄 Updated {callers_updated} caller(s) in same file")
            updated_callers += callers_updated

    # Now find and update external callers
    print(f"\n🔍 Searching for external callers...")

    # Search all Python files for .to_dict() calls
    for root, dirs, files in os.walk("src"):
        for filename in files:
            if filename.endswith(".py"):
                file_path = Path(root) / filename

                # Skip files we already processed
                if str(file_path) in SEMI_REDUNDANT_FILES:
                    continue

                callers = find_callers_in_file(file_path, "")
                if callers:
                    print(f"\n📁 Found callers in {file_path}:")
                    for line_num, line_content in callers:
                        print(f"  Line {line_num}: {line_content}")

                    # For now, just report them - we'll need manual review
                    print(f"  ⚠️  Manual review required for these callers")

    print(f"\n✅ Summary:")
    print(f"  - Removed {removed_methods} semi-redundant to_dict() methods")
    print(f"  - Updated {updated_callers} direct callers")
    print(f"  - External callers require manual review")


if __name__ == "__main__":
    main()
