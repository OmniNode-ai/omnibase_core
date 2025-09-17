#!/usr/bin/env python3
"""
Update callers that were using the removed simple to_dict() wrapper methods.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Files we know we removed to_dict() methods from, mapped to their replacement
REMOVED_TO_DICT_METHODS = {
    # Simple wrappers that used exclude_none=True
    "model_trend_data.py": "model_dump(exclude_none=True)",
    "model_performance_profile.py": "model_dump(exclude_none=True)",
    "model_generic_metadata.py": "model_dump(exclude_none=True)",
    "model_git_hub_issues_event.py": "model_dump(exclude_none=True)",
    "model_health_check_config.py": "model_dump(exclude_none=True)",
    "model_pool_recommendations.py": "model_dump(exclude_none=True)",
    "model_latency_profile.py": "model_dump(exclude_none=True)",
    "model_git_hub_issue_comment_event.py": "model_dump(exclude_none=True)",
    "model_git_hub_release_event.py": "model_dump(exclude_none=True)",
    "model_parsed_connection_info.py": "model_dump(exclude_none=True)",
    "model_cache_settings.py": "model_dump(exclude_none=True)",
    "model_masked_connection_properties.py": "model_dump(exclude_none=True)",
    "model_node_information.py": "model_dump(exclude_none=True)",
    "model_connection_properties.py": "model_dump(exclude_none=True)",
    "model_security_assessment.py": "model_dump(exclude_none=True)",
    "model_resource_allocation.py": "model_dump(exclude_none=True)",
    "model_health_check_result.py": "model_dump(exclude_none=True)",
    "model_custom_filter_base.py": "model_dump(exclude_none=True)",
    "model_audit_entry.py": "model_dump(exclude_none=True)",
    "model_performance_summary.py": "model_dump(exclude_none=True)",
    "model_monitoring_metrics.py": "model_dump(exclude_none=True)",
    "model_orchestrator_info.py": "model_dump(exclude_none=True)",
    "model_error_details.py": "model_dump(exclude_none=True)",
    "model_cli_command.py": "model_dump(exclude_none=True)",
    "model_contract_document.py": "model_dump(exclude_none=True)",
}

# Files that still have to_dict() methods (complex ones we're keeping)
COMPLEX_TO_DICT_METHODS = [
    "model_schema_dict.py",
    "model_json_schema.py",
    "model_schema.py",
    "model_custom_filters.py",
    "model_mask_data.py",
    "model_dependency_graph.py",
    "model_cli_interface.py",
    # Many others with complex logic
]


def find_to_dict_callers(file_path: Path) -> List[Tuple[int, str, str]]:
    """Find .to_dict() calls in a file and return (line_num, full_line, variable_context)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        callers = []

        for i, line in enumerate(lines, 1):
            if ".to_dict()" in line:
                # Try to extract the variable/object being called
                matches = re.findall(r"(\w+)\.to_dict\(\)", line)
                var_context = matches[0] if matches else "unknown"
                callers.append((i, line.strip(), var_context))

        return callers

    except Exception:
        return []


def should_update_call(file_path: Path, line_content: str, var_context: str) -> bool:
    """Determine if a .to_dict() call should be updated to model_dump()."""

    # Don't update calls in files we know still have complex to_dict methods
    file_name = file_path.name
    if any(complex_file in file_name for complex_file in COMPLEX_TO_DICT_METHODS):
        # Exception: calls to self.to_dict() in files that still have the method should be updated
        if var_context == "self" and "return self.to_dict()" not in line_content:
            return False
        # But calls like self.items.to_dict() or obj.to_dict() might need updating
        return var_context != "self"

    return True


def update_caller_line(line: str) -> str:
    """Update a line to replace .to_dict() with .model_dump(exclude_none=True)."""
    # Replace .to_dict() with .model_dump(exclude_none=True)
    return line.replace(".to_dict()", ".model_dump(exclude_none=True)")


def update_file_callers(file_path: Path) -> int:
    """Update .to_dict() callers in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        callers = find_to_dict_callers(file_path)
        if not callers:
            return 0

        lines = content.split("\n")
        updates_made = 0

        for line_num, line_content, var_context in callers:
            line_index = line_num - 1

            if should_update_call(file_path, line_content, var_context):
                old_line = lines[line_index]
                new_line = update_caller_line(old_line)

                if old_line != new_line:
                    lines[line_index] = new_line
                    updates_made += 1
                    print(
                        f"    Line {line_num}: {var_context}.to_dict() → {var_context}.model_dump(exclude_none=True)"
                    )

        if updates_made > 0:
            new_content = "\n".join(lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        return updates_made

    except Exception as e:
        print(f"    ❌ Error updating {file_path}: {e}")
        return 0


def main():
    """Main function to update .to_dict() callers."""
    print("🔄 Updating .to_dict() callers to use model_dump()...")
    print("=" * 60)

    # Find all Python files that might have callers
    all_files = list(Path("src").rglob("*.py"))

    total_updates = 0
    files_with_updates = 0

    for file_path in sorted(all_files):
        callers = find_to_dict_callers(file_path)
        if not callers:
            continue

        print(f"\n📁 {file_path.relative_to(Path.cwd())}")

        # Show what we found
        for line_num, line_content, var_context in callers:
            should_update = should_update_call(file_path, line_content, var_context)
            status = "🔄" if should_update else "⏭️ "
            print(
                f"  {status} Line {line_num}: {var_context}.to_dict() - {line_content[:60]}{'...' if len(line_content) > 60 else ''}"
            )

        # Apply updates
        updates = update_file_callers(file_path)
        if updates > 0:
            files_with_updates += 1
            total_updates += updates
            print(f"  ✅ Updated {updates} caller(s)")

    print(f"\n" + "=" * 60)
    print(f"🎯 Summary:")
    print(
        f"  📊 Total files processed: {len([f for f in all_files if find_to_dict_callers(f)])}"
    )
    print(f"  🔄 Files with updates: {files_with_updates}")
    print(f"  ✅ Total updates made: {total_updates}")


if __name__ == "__main__":
    main()
