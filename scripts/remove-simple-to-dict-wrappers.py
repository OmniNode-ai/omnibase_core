#!/usr/bin/env python3
"""
Remove simple wrapper to_dict() methods that just call model_dump().
"""

import re
from pathlib import Path
from typing import Any, Dict, List

# Semi-redundant methods that are simple wrappers (remaining after manual fixes)
SIMPLE_WRAPPER_FILES = [
    "src/omnibase_core/core/errors/core_errors.py",
    "src/omnibase_core/model/configuration/model_git_hub_issues_event.py",
    "src/omnibase_core/model/configuration/model_health_check_config.py",
    "src/omnibase_core/model/configuration/model_pool_recommendations.py",
    "src/omnibase_core/model/configuration/model_latency_profile.py",
    "src/omnibase_core/model/configuration/model_git_hub_issue_comment_event.py",
    "src/omnibase_core/model/configuration/model_git_hub_release_event.py",
    "src/omnibase_core/model/configuration/model_parsed_connection_info.py",
    "src/omnibase_core/model/configuration/model_cache_settings.py",
    # model_trend_data.py - already done
    # model_performance_profile.py - already done
    "src/omnibase_core/model/core/model_masked_connection_properties.py",
    # model_generic_metadata.py - already done
    "src/omnibase_core/model/core/model_error_summary.py",
    "src/omnibase_core/model/core/model_business_impact.py",
    "src/omnibase_core/model/core/model_node_information.py",
    "src/omnibase_core/model/core/model_connection_properties.py",  # Has multiple classes
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


def analyze_to_dict_method(content: str) -> Dict[str, Any]:
    """Analyze to_dict method(s) in file content."""
    # Find all to_dict methods
    pattern = r'def to_dict\(self\) -> dict\[str, Any\]:\s*\n\s*"""[^"]*"""\s*\n\s*return self\.model_dump\([^)]*\)'
    matches = re.findall(pattern, content, re.MULTILINE)

    # Also check for simpler patterns
    simple_pattern = r'def to_dict\(self\)[^:]*:\s*\n[^"]*"""[^"]*"""\s*\n[^"]*return self\.model_dump\([^)]*\)'
    simple_matches = re.findall(simple_pattern, content, re.MULTILINE | re.DOTALL)

    # Extract parameters from model_dump calls
    model_dump_calls = re.findall(r"return self\.model_dump\(([^)]*)\)", content)

    return {
        "has_to_dict": "def to_dict(" in content,
        "method_count": len(re.findall(r"def to_dict\(", content)),
        "model_dump_calls": model_dump_calls,
        "appears_simple": len(matches) > 0 or len(simple_matches) > 0,
    }


def remove_simple_to_dict_methods(file_path: Path) -> bool:
    """Remove simple to_dict wrapper methods from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Analyze the file first
        analysis = analyze_to_dict_method(original_content)
        if not analysis["has_to_dict"]:
            print(f"  ⚠️  No to_dict method found in {file_path}")
            return False

        print(f"  📊 Found {analysis['method_count']} to_dict method(s)")
        print(f"  📊 Model dump calls: {analysis['model_dump_calls']}")

        # Pattern for simple wrapper methods
        patterns_to_remove = [
            # Pattern 1: Standard simple wrapper with exclude_none=True
            r'\s*def to_dict\(self\) -> dict\[str, Any\]:\s*\n\s*"""Convert to dictionary using pydantic model_dump\."""\s*\n\s*return self\.model_dump\(exclude_none=True\)\s*\n',
            # Pattern 2: Standard simple wrapper with no parameters
            r'\s*def to_dict\(self\) -> dict\[str, Any\]:\s*\n\s*"""Convert to dictionary using pydantic model_dump\."""\s*\n\s*return self\.model_dump\(\)\s*\n',
            # Pattern 3: Simple wrapper with different docstring
            r'\s*def to_dict\(self\) -> dict\[str, Any\]:\s*\n\s*"""[^"]*"""\s*\n\s*return self\.model_dump\([^)]*\)\s*\n',
            # Pattern 4: Variation with exclude_unset
            r'\s*def to_dict\(self\) -> dict\[str, Any\]:\s*\n\s*"""[^"]*"""\s*\n\s*return self\.model_dump\(exclude_unset=True\)\s*\n',
        ]

        content = original_content
        removed_count = 0

        for pattern in patterns_to_remove:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            if matches:
                content = re.sub(pattern, "\n", content, flags=re.MULTILINE | re.DOTALL)
                removed_count += len(matches)
                print(f"  ✂️  Removed {len(matches)} method(s) with pattern")

        # Clean up extra blank lines
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✅ Successfully removed {removed_count} to_dict method(s)")
            return True
        else:
            print(f"  ⚠️  No simple patterns matched, manual review needed")
            return False

    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False


def main():
    """Main function to remove simple to_dict wrapper methods."""
    print("🧹 Removing simple to_dict() wrapper methods...")
    print("=" * 60)

    removed_files = 0
    total_files = len(SIMPLE_WRAPPER_FILES)

    for i, file_path_str in enumerate(SIMPLE_WRAPPER_FILES, 1):
        file_path = Path(file_path_str)

        if not file_path.exists():
            print(f"\n📁 [{i}/{total_files}] ⚠️  File not found: {file_path}")
            continue

        print(f"\n📁 [{i}/{total_files}] Processing: {file_path}")

        if remove_simple_to_dict_methods(file_path):
            removed_files += 1

    print(f"\n" + "=" * 60)
    print(f"🎯 Summary:")
    print(f"  ✅ Successfully processed: {removed_files}/{total_files} files")
    print(f"  ⚠️  Need manual review: {total_files - removed_files} files")

    if removed_files < total_files:
        print(f"\n🔍 Files needing manual review:")
        for file_path_str in SIMPLE_WRAPPER_FILES:
            # You could add logic here to identify which ones still need work
            pass


if __name__ == "__main__":
    main()
