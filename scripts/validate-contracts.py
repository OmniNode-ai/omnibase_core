#!/usr/bin/env python3
"""
Generic YAML contract validation for omni* repositories.
Validates that YAML contract files follow ONEX standards.
"""

import argparse
import sys
from pathlib import Path
from typing import List

# Import the contract model and safe YAML loader
try:
    from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract
    from omnibase_core.utils.safe_yaml_loader import (
        YamlLoadingError,
        load_and_validate_yaml_model,
    )
except ImportError:
    # Fallback for when running as script directly
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "archived", "src"))
    from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract
    from omnibase_core.utils.safe_yaml_loader import (
        YamlLoadingError,
        load_and_validate_yaml_model,
    )


def validate_yaml_file(file_path: Path) -> List[str]:
    """Validate a single YAML file using approved Pydantic model validation."""
    errors = []

    try:
        # First check if file is empty
        if file_path.stat().st_size == 0:
            return []  # Empty files are OK

        # Quick check to see if this looks like a contract file by reading content
        with open(file_path, "r") as f:
            content = f.read()

        if not content.strip():
            return []  # Empty or whitespace-only files are OK

        # Check if this looks like a contract (has contract field keywords in content)
        if "contract_version" in content or "node_type" in content:
            try:
                # Use approved load_and_validate_yaml_model instead of manual validation
                load_and_validate_yaml_model(file_path, ModelYamlContract)
            except YamlLoadingError as e:
                # Convert YAML loading errors to readable messages
                if "validation error" in str(e).lower():
                    # Extract validation details from the error
                    error_msg = str(e)
                    errors.append(f"Validation error: {error_msg}")
                else:
                    errors.append(f"YAML validation failed: {e}")

    except Exception as e:
        errors.append(f"File reading error: {e}")

    return errors


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate YAML contracts")
    parser.add_argument("path", nargs="?", default=".", help="Path to validate")
    args = parser.parse_args()

    base_path = Path(args.path)
    yaml_files = list(base_path.rglob("*.yaml")) + list(base_path.rglob("*.yml"))

    # Filter out archived files
    yaml_files = [
        f
        for f in yaml_files
        if "/archived/" not in str(f) and "archived" not in f.parts
    ]

    if not yaml_files:
        print("✅ Contract validation: No YAML files to validate")
        return 0

    total_errors = 0

    for yaml_file in yaml_files:
        errors = validate_yaml_file(yaml_file)
        if errors:
            print(f"❌ {yaml_file}:")
            for error in errors:
                print(f"   {error}")
            total_errors += len(errors)

    if total_errors == 0:
        print(
            f"✅ Contract validation: {len(yaml_files)} YAML files validated successfully"
        )
        return 0
    else:
        print(
            f"❌ Contract validation: {total_errors} errors found in {len(yaml_files)} files"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
