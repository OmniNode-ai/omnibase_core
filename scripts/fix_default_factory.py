#!/usr/bin/env python3
"""Fix default_factory type issues in Pydantic Field definitions."""

import re
import sys
from pathlib import Path


def fix_default_factory_in_file(file_path: Path) -> bool:
    """Fix default_factory issues in a single file."""
    content = file_path.read_text()
    original_content = content

    # Pattern to match: default_factory=ModelSomething,
    # Replace with: default_factory=lambda: ModelSomething(),
    pattern = r"default_factory=([A-Z][a-zA-Z0-9_]+),"
    replacement = r"default_factory=lambda: \1(),"

    content = re.sub(pattern, replacement, content)

    # Also handle cases without trailing comma
    pattern_no_comma = r"default_factory=([A-Z][a-zA-Z0-9_]+)\s*\)"
    replacement_no_comma = r"default_factory=lambda: \1()\)"

    content = re.sub(pattern_no_comma, replacement_no_comma, content)

    if content != original_content:
        file_path.write_text(content)
        print(f"Fixed: {file_path}")
        return True
    return False


def main():
    """Main entry point."""
    files = [
        "src/omnibase_core/models/configuration/model_load_balancing_algorithm.py",
        "src/omnibase_core/models/configuration/model_load_balancing_policy.py",
        "src/omnibase_core/models/configuration/model_log_destination.py",
        "src/omnibase_core/models/configuration/model_log_filter.py",
        "src/omnibase_core/models/configuration/model_rate_limit_policy.py",
        "src/omnibase_core/models/configuration/model_request_config.py",
        "src/omnibase_core/models/configuration/model_session_affinity.py",
        "src/omnibase_core/models/core/model_cli_execution.py",
        "src/omnibase_core/models/core/model_cli_tool_execution_input.py",
        "src/omnibase_core/models/core/model_connection_info.py",
        "src/omnibase_core/models/core/model_execution_context.py",
        "src/omnibase_core/models/core/model_fallback_strategy.py",
        "src/omnibase_core/models/core/model_health_status.py",
        "src/omnibase_core/models/core/model_metadata_tool_info.py",
        "src/omnibase_core/models/core/model_node_execution_result.py",
        "src/omnibase_core/models/core/model_node_information.py",
        "src/omnibase_core/models/core/model_node_instance.py",
        "src/omnibase_core/models/core/model_node_type.py",
        "src/omnibase_core/models/core/model_tool_metadata.py",
        "src/omnibase_core/models/core/model_workflow_metrics.py",
        "src/omnibase_core/models/security/model_permission_scope.py",
        "src/omnibase_core/models/security/model_trust_policy.py",
        "src/omnibase_core/models/service/model_node_service_config.py",
    ]

    root = Path("/Volumes/PRO-G40/Code/omnibase_core")
    fixed_count = 0

    for file_path_str in files:
        file_path = root / file_path_str
        if file_path.exists():
            if fix_default_factory_in_file(file_path):
                fixed_count += 1
        else:
            print(f"Not found: {file_path}")

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
