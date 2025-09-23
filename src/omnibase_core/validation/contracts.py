"""
Contract validation tools for ONEX compliance.

This module provides validation functions for contract files:
- YAML contract validation
- Manual YAML prevention
- Contract structure validation
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

import yaml

from .validation_utils import ValidationResult

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - prevent DoS attacks
VALIDATION_TIMEOUT = 300  # 5 minutes


class TimeoutError(Exception):
    """Raised when validation times out."""


def timeout_handler(signum: int, frame: object) -> None:
    """Handle timeout signal."""
    raise TimeoutError("Validation timed out")


def validate_yaml_file(file_path: Path) -> list[str]:
    """Validate a single YAML file."""
    errors = []

    # Check file existence and basic properties
    if not file_path.exists():
        errors.append("File does not exist")
        return errors

    if not file_path.is_file():
        errors.append("Path is not a regular file")
        return errors

    # Check file size to prevent DoS attacks
    try:
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            errors.append(
                f"File too large ({file_size} bytes), max allowed: {MAX_FILE_SIZE}",
            )
            return errors
    except OSError as e:
        errors.append(f"Cannot check file size: {e}")
        return errors

    # Check file permissions
    if not os.access(file_path, os.R_OK):
        errors.append("Permission denied - cannot read file")
        return errors

    # Validate YAML syntax and structure
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Use Pydantic model validation instead of manual YAML parsing
        try:
            from ..models.contracts.model_yaml_contract import ModelYamlContract

            # Parse and validate in one step using safe_yaml_loader
            from ..utils.safe_yaml_loader import load_yaml_content

            # Load YAML safely and validate with Pydantic model
            yaml_data = load_yaml_content(content)
            contract = ModelYamlContract.validate_yaml_content(yaml_data)

            # Validation successful if we reach here

        except Exception as e:
            errors.append(f"Contract validation failed: {e}")
            return errors

        # All validation is now handled by Pydantic model
        # Legacy manual validation removed for ONEX compliance

        # Legacy check for compatibility - this can be removed once all contracts are migrated
        if isinstance(yaml_data, dict):
            # Check for common contract fields (legacy support)
            required_fields = ["metadata", "specification"]
            missing_fields = [
                field for field in required_fields if field not in yaml_data
            ]

            if missing_fields:
                errors.append(f"Missing required fields: {', '.join(missing_fields)}")

            # Validate metadata section
            if "metadata" in yaml_data:
                metadata = yaml_data["metadata"]
                if not isinstance(metadata, dict):
                    errors.append("metadata field must be an object")
                else:
                    # Check for required metadata fields
                    required_metadata = ["name", "version"]
                    missing_metadata = [
                        field for field in required_metadata if field not in metadata
                    ]
                    if missing_metadata:
                        errors.append(
                            f"Missing required metadata fields: {', '.join(missing_metadata)}",
                        )

            # Validate specification section
            if "specification" in yaml_data:
                spec = yaml_data["specification"]
                if not isinstance(spec, dict):
                    errors.append("specification field must be an object")

    except Exception as e:
        errors.append(f"Error reading file: {e}")

    return errors


def validate_no_manual_yaml(directory: Path) -> list[str]:
    """Validate that there are no manually created YAML files in restricted areas."""
    errors = []

    # Define restricted patterns
    restricted_patterns = [
        "**/generated/**/*.yaml",
        "**/generated/**/*.yml",
        "**/auto/**/*.yaml",
        "**/auto/**/*.yml",
    ]

    for pattern in restricted_patterns:
        for yaml_file in directory.glob(pattern):
            # Check if file appears to be manually created
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    content = f.read()

                # Look for manual creation indicators
                manual_indicators = [
                    "# Manual",
                    "# TODO",
                    "# FIXME",
                    "# NOTE:",
                    "# manually created",
                ]

                for indicator in manual_indicators:
                    if indicator.lower() in content.lower():
                        errors.append(
                            f"Manual YAML detected in restricted area: {yaml_file}",
                        )
                        break

            except Exception as e:
                errors.append(f"Error checking {yaml_file}: {e}")

    return errors


def validate_contracts_directory(directory: Path) -> ValidationResult:
    """Validate all contract files in a directory."""
    yaml_files: list[Path] = []

    # Find YAML files
    for ext in ["*.yaml", "*.yml"]:
        yaml_files.extend(directory.rglob(ext))

    # Filter out excluded files
    yaml_files = [
        f
        for f in yaml_files
        if not any(part in str(f) for part in ["__pycache__", ".git", "node_modules"])
    ]

    all_errors = []
    files_with_errors = []

    # Validate each YAML file
    for yaml_file in yaml_files:
        errors = validate_yaml_file(yaml_file)
        if errors:
            files_with_errors.append(str(yaml_file))
            all_errors.extend([f"{yaml_file}: {error}" for error in errors])

    # Check for manual YAML in restricted areas
    manual_yaml_errors = validate_no_manual_yaml(directory)
    all_errors.extend(manual_yaml_errors)

    success = len(all_errors) == 0

    return ValidationResult(
        success=success,
        errors=all_errors,
        files_checked=len(yaml_files),
        violations_found=len(all_errors),
        files_with_violations=len(files_with_errors),
        metadata={
            "validation_type": "contracts",
            "yaml_files_found": len(yaml_files),
            "manual_yaml_violations": len(manual_yaml_errors),
        },
    )


def validate_contracts_cli() -> int:
    """CLI interface for contract validation."""
    parser = argparse.ArgumentParser(
        description="Generic YAML contract validation for omni* repositories",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["."],
        help="Directories to validate",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=VALIDATION_TIMEOUT,
        help=f"Validation timeout in seconds (default: {VALIDATION_TIMEOUT})",
    )

    args = parser.parse_args()

    # Set up timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(args.timeout)

    try:
        print("🔍 YAML Contract Validation")
        print("=" * 40)

        overall_result = ValidationResult(success=True, errors=[], files_checked=0)

        for directory in args.directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                print(f"❌ Directory not found: {directory}")
                continue

            print(f"📁 Scanning {directory}...")
            result = validate_contracts_directory(dir_path)

            # Merge results
            overall_result.success = overall_result.success and result.success
            overall_result.errors.extend(result.errors)
            overall_result.files_checked += result.files_checked

            if result.errors:
                print(f"\n❌ Issues found in {directory}:")
                for error in result.errors:
                    print(f"   {error}")

        print("\n📊 Contract Validation Summary:")
        print(f"   • Files checked: {overall_result.files_checked}")
        print(f"   • Issues found: {len(overall_result.errors)}")

        if overall_result.success:
            print("✅ Contract validation PASSED")
            return 0
        print("❌ Contract validation FAILED")
        return 1

    except TimeoutError:
        print(f"❌ Validation timed out after {args.timeout} seconds")
        return 1
    except KeyboardInterrupt:
        print("❌ Validation interrupted by user")
        return 1
    finally:
        signal.alarm(0)  # Cancel timeout


if __name__ == "__main__":
    sys.exit(validate_contracts_cli())
