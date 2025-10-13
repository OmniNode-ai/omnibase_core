#!/usr/bin/env python3
"""Script to process violations 101-159 systematically."""

import ast
import os
from pathlib import Path
from typing import Any, Dict, List


def read_file_content(filepath: Path) -> str:
    """Read file content."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


def write_file_content(filepath: Path, content: str) -> bool:
    """Write file content."""
    try:
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False


def extract_classes_from_file(filepath: Path, classes: list[str]) -> dict[str, str]:
    """Extract classes from a file."""
    content = read_file_content(filepath)
    if not content:
        return {}

    tree = ast.parse(content)
    class_contents = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in classes:
            # Get the lines for this class
            start_line = node.lineno - 1  # 0-based
            end_line = node.end_lineno

            lines = content.split("\n")
            class_lines = lines[start_line:end_line]

            # Find proper indentation
            class_content = "\n".join(class_lines)
            class_contents[node.name] = class_content

    return class_contents


def process_violation_101():
    """Process violation 101: model_service_discovery_manager.py"""
    print("Processing violation 101: model_service_discovery_manager.py")

    # This is already done manually, just verify
    filepath = Path("src/omnibase_core/models/core/model_service_discovery_manager.py")
    content = read_file_content(filepath)

    if (
        "ModelConfig" in content
        and "from .model_service_discovery_config import ModelConfig" in content
    ):
        print("✓ Violation 101 already processed")
        return True

    print("✗ Violation 101 not properly processed")
    return False


def process_violation_102():
    """Process violation 102: model_tool_health_status.py"""
    print("Processing violation 102: model_tool_health_status.py")

    filepath = Path("src/omnibase_core/models/core/model_tool_health_status.py")
    classes = ["ModelToolHealthStatus", "ModelConfig"]

    class_contents = extract_classes_from_file(filepath, classes)

    # Create ModelConfig file
    config_path = Path("src/omnibase_core/models/core/model_tool_health_config.py")
    if "ModelConfig" in class_contents:
        config_content = f"""from pydantic import BaseModel


{class_contents["ModelConfig"]}
"""
        write_file_content(config_path, config_content)
        print(f"✓ Created {config_path}")

    # Update original file
    if "ModelToolHealthStatus" in class_contents:
        original_content = read_file_content(filepath)
        updated_content = original_content.replace(
            "class ModelConfig:",
            "from .model_tool_health_config import ModelConfig\n\n\nclass ModelToolHealthStatus(BaseModel):\n",
        )
        # Remove the ModelConfig class
        lines = updated_content.split("\n")
        filtered_lines = []
        skip_next = False
        for line in lines:
            if line.strip().startswith("class ModelConfig:"):
                skip_next = True
                continue
            if (
                skip_next
                and line.strip()
                and not line.startswith("    ")
                and not line.startswith("\t")
            ):
                skip_next = False
            if not skip_next:
                filtered_lines.append(line)

        # Add config reference
        final_lines = []
        for line in filtered_lines:
            final_lines.append(line)
            if "health_check_interval: int = Field(" in line:
                # Find the end of this field
                final_lines.append("")
                final_lines.append("    class Config(ModelConfig):")
                final_lines.append(
                    '        """Configuration for tool health status."""'
                )
                final_lines.append("        pass")

        updated_content = "\n".join(final_lines)
        write_file_content(filepath, updated_content)
        print(f"✓ Updated {filepath}")

    return True


def main():
    """Main processing function."""
    print("Starting to process violations 101-159...")

    # Process violation 101 (already done)
    result1 = process_violation_101()

    # Process violation 102
    result2 = process_violation_102()

    print("\nResults:")
    print(f"Violation 101: {'✓' if result1 else '✗'}")
    print(f"Violation 102: {'✓' if result2 else '✗'}")


if __name__ == "__main__":
    main()
