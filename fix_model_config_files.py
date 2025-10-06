#!/usr/bin/env python3
"""Fix ModelConfig files that were created without proper imports."""

import os
from pathlib import Path


def fix_model_config_file(filepath: Path):
    """Fix a single ModelConfig file."""
    content = filepath.read_text()

    # Add proper imports if missing
    if "from pydantic import BaseModel" not in content:
        lines = content.split("\n")
        # Remove any leading empty lines or indentation
        while lines and (lines[0].strip() == "" or lines[0].startswith("    ")):
            lines.pop(0)

        # Add proper imports at the beginning
        lines.insert(0, "from pydantic import BaseModel\n")
        lines.insert(1, "\n")

        # Find and fix the ModelConfig class
        for i, line in enumerate(lines):
            if line.strip().startswith("class ModelConfig:"):
                # Add BaseModel inheritance
                lines[i] = "class ModelConfig(BaseModel):"
                break

        content = "\n".join(lines)
        filepath.write_text(content)
        print(f"✓ Fixed {filepath}")


def main():
    """Fix all ModelConfig files."""
    # Find all ModelConfig files
    src_dir = Path("src/omnibase_core")
    model_config_files = list(src_dir.rglob("model_config.py"))

    print(f"Found {len(model_config_files)} ModelConfig files to fix")

    for filepath in model_config_files:
        fix_model_config_file(filepath)


if __name__ == "__main__":
    main()
