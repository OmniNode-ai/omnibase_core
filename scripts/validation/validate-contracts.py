#!/usr/bin/env python3
"""
Generic YAML contract validation for omni* repositories.
Validates that YAML contract files follow ONEX standards.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


def validate_yaml_file(file_path: Path) -> List[str]:
    """Validate a single YAML file."""
    errors = []

    try:
        with open(file_path, "r") as f:
            content = yaml.safe_load(f)

        if not content:
            return []  # Empty files are OK

        # Basic YAML contract validation
        if isinstance(content, dict):
            # Check for required contract fields if this looks like a contract
            if "contract_version" in content or "node_type" in content:
                if "contract_version" not in content:
                    errors.append("Missing required field: contract_version")
                if "node_type" not in content:
                    errors.append("Missing required field: node_type")

    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {e}")
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
