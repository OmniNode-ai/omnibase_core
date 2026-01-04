"""
Contract validation tools for ONEX compliance.

This module provides validation functions for contract files:
- YAML contract validation
- Manual YAML prevention
- Contract structure validation
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .validator_utils import ModelValidationResult

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - prevent DoS attacks
VALIDATION_TIMEOUT = 300  # 5 minutes


def timeout_handler(_signum: int, _frame: object) -> None:
    """Handle timeout signal."""
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.TIMEOUT_ERROR,
        message="Validation timed out",
    )


def load_and_validate_yaml_model(content: str) -> ModelYamlContract:
    """Load and validate YAML content with Pydantic model - recognized utility function.

    Uses lazy import to avoid circular dependency with models module.
    """
    # LAZY IMPORT: Import ModelYamlContract only when function is called
    # This breaks circular import: contracts -> models -> mixins -> contracts
    from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract

    # Parse YAML and validate with Pydantic model directly
    # Note: yaml.safe_load is required here for parsing before Pydantic validation
    parsed_yaml = yaml.safe_load(content)
    return ModelYamlContract.model_validate(parsed_yaml)


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

        # Handle whitespace-only files as valid (empty content)
        if not content.strip():
            # Whitespace-only files are considered valid/empty
            return errors

        # Use Pydantic model validation instead of manual YAML parsing
        try:
            # Use recognized YAML utility function for Pydantic validation
            _contract = load_and_validate_yaml_model(content)

            # Validation successful if we reach here

        except yaml.YAMLError as e:
            # Wrap in ModelOnexError for consistent error handling
            wrapped_error = ModelOnexError(
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                message=f"YAML parsing failed: {e}",
                context={
                    "file_path": str(file_path),
                    "exception_type": type(e).__name__,
                },
            )
            logging.exception(f"YAML parsing error: {wrapped_error.message}")
            errors.append(wrapped_error.message)
        except ValidationError as e:
            # Wrap in ModelOnexError for consistent error handling
            wrapped_error = ModelOnexError(
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                message=f"Contract validation failed: {e}",
                context={
                    "file_path": str(file_path),
                    "exception_type": type(e).__name__,
                },
            )
            logging.exception(f"Contract validation error: {wrapped_error.message}")
            errors.append(wrapped_error.message)
        # Note: load_and_validate_yaml_model() only raises yaml.YAMLError
        # and ValidationError. No ModelOnexError handler needed here.

    except OSError as e:
        # boundary-ok: handles TOCTOU race conditions where file changes after
        # preliminary checks (lines 67-91) but before open(). Wraps in ModelOnexError
        # for consistent error handling across the validation framework.
        wrapped_error = ModelOnexError(
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            message=f"OS error reading file: {e}",
            context={
                "file_path": str(file_path),
                "exception_type": type(e).__name__,
            },
        )
        logging.exception(f"File read error: {wrapped_error.message}")
        errors.append(wrapped_error.message)
    except UnicodeDecodeError as e:
        # boundary-ok: handles encoding errors from f.read() that can occur
        # with invalid UTF-8 content. Wraps in ModelOnexError for consistent
        # error handling across the validation framework.
        wrapped_error = ModelOnexError(
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            message=f"Error decoding file: {e}",
            context={
                "file_path": str(file_path),
                "exception_type": type(e).__name__,
            },
        )
        logging.exception(f"File read error: {wrapped_error.message}")
        errors.append(wrapped_error.message)

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

            except OSError as e:
                # Wrap in ModelOnexError for consistent error handling
                wrapped_error = ModelOnexError(
                    error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                    message=f"Error reading {yaml_file}: {e}",
                    context={
                        "file_path": str(yaml_file),
                        "exception_type": type(e).__name__,
                    },
                )
                logging.exception(f"File read error: {wrapped_error.message}")
                errors.append(wrapped_error.message)
            except UnicodeDecodeError as e:
                # Wrap in ModelOnexError for consistent error handling
                wrapped_error = ModelOnexError(
                    error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                    message=f"Error decoding {yaml_file}: {e}",
                    context={
                        "file_path": str(yaml_file),
                        "exception_type": type(e).__name__,
                    },
                )
                logging.exception(f"File decode error: {wrapped_error.message}")
                errors.append(wrapped_error.message)

    return errors


def validate_contracts_directory(directory: Path) -> ModelValidationResult[None]:
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

    is_valid = len(all_errors) == 0

    return ModelValidationResult(
        is_valid=is_valid,
        errors=all_errors,
        metadata=ModelValidationMetadata(
            validation_type="contracts",
            files_processed=len(yaml_files),
            yaml_files_found=len(yaml_files),
            manual_yaml_violations=len(manual_yaml_errors),
            violations_found=len(all_errors),
            files_with_violations=len(files_with_errors),
        ),
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

    # Initialize to None for finally block
    original_handler = None

    try:
        # Set up timeout AFTER entering try block for proper exception handling
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(args.timeout)

        print("🔍 YAML Contract Validation")
        print("=" * 40)

        overall_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            errors=[],
            metadata=ModelValidationMetadata(files_processed=0),
        )

        for directory in args.directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                print(f"❌ Directory not found: {directory}")
                continue

            print(f"📁 Scanning {directory}...")
            result = validate_contracts_directory(dir_path)

            # Merge results
            overall_result.is_valid = overall_result.is_valid and result.is_valid
            overall_result.errors.extend(result.errors)
            if overall_result.metadata and result.metadata:
                overall_result.metadata.files_processed = (
                    overall_result.metadata.files_processed or 0
                ) + (result.metadata.files_processed or 0)

            if result.errors:
                print(f"\n❌ Issues found in {directory}:")
                for error in result.errors:
                    print(f"   {error}")

        print("\n📊 Contract Validation Summary:")
        files_processed = (
            overall_result.metadata.files_processed if overall_result.metadata else 0
        )
        print(f"   • Files checked: {files_processed}")
        print(f"   • Issues found: {len(overall_result.errors)}")

        if overall_result.is_valid:
            print("✅ Contract validation PASSED")
            return 0
        print("❌ Contract validation FAILED")
        return 1

    except ModelOnexError as e:
        if e.error_code == EnumCoreErrorCode.TIMEOUT_ERROR:
            print(f"❌ Validation timed out after {args.timeout} seconds")
        else:
            print(f"❌ Validation error: {e.message}")
        return 1
    except KeyboardInterrupt:
        print("❌ Validation interrupted by user")
        return 1
    finally:
        # Clean up signal handling to prevent test pollution
        signal.alarm(0)  # Cancel timeout
        if original_handler is not None:
            signal.signal(signal.SIGALRM, original_handler)  # Restore original handler


if __name__ == "__main__":
    sys.exit(validate_contracts_cli())
