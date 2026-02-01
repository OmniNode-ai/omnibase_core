#!/usr/bin/env python3
"""
Generic YAML contract validation for omni* repositories.
Validates that YAML contract files follow ONEX standards.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import yaml

# Handle timeout_utils import for both direct execution and test imports
try:
    import timeout_utils
    from timeout_utils import timeout_context
except ImportError:
    # Try relative import for when script is imported by tests
    import sys
    from pathlib import Path

    # Add the script directory to Python path for timeout_utils import
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    import timeout_utils
    from timeout_utils import timeout_context

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - prevent DoS attacks


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
                f"File too large ({file_size} bytes), max allowed: {MAX_FILE_SIZE}"
            )
            return errors
    except OSError as e:
        errors.append(f"Cannot check file size: {e}")
        return errors

    # Check file permissions
    if not os.access(file_path, os.R_OK):
        errors.append("Permission denied - cannot read file")
        return errors

    try:
        # Read file with proper encoding
        with open(file_path, encoding="utf-8") as f:
            content_str = f.read()

    except FileNotFoundError:
        errors.append("File not found")
        return errors
    except PermissionError as e:
        errors.append(f"Permission denied: {e}")
        return errors
    except UnicodeDecodeError as e:
        errors.append(f"File encoding error: {e}")
        return errors
    except OSError as e:
        errors.append(f"OS/IO error reading file: {e}")
        return errors

    # Handle whitespace-only files as valid (empty content)
    if not content_str.strip():
        # Whitespace-only files are considered valid/empty
        return errors

    # Parse YAML with specific error handling
    try:
        content = yaml.safe_load(content_str)
    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {e}")
        return errors
    except yaml.constructor.ConstructorError as e:
        errors.append(f"YAML constructor error: {e}")
        return errors
    except yaml.parser.ParserError as e:
        errors.append(f"YAML parser error: {e}")
        return errors
    except yaml.scanner.ScannerError as e:
        errors.append(f"YAML scanner error: {e}")
        return errors
    except MemoryError:
        errors.append("YAML file too large to parse in memory")
        return errors

    if content is None:
        return []  # Empty files are OK

    # YAML contract validation using Pydantic models
    if isinstance(content, dict):
        # Check if this is a handler contract (has handler_id)
        # Handler contracts use ModelHandlerContract schema and don't require contract_version/node_type
        if "handler_id" in content:
            # Validate handler contract using standalone validator
            try:
                from handler_contract_validator import MinimalHandlerContract
                from pydantic import ValidationError

                # Validate using Pydantic model
                MinimalHandlerContract.validate_yaml_content(content)

            except ValidationError as e:
                # Extract meaningful error messages from Pydantic validation
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error["loc"])
                    error_msg = error["msg"]
                    error_type = error["type"]

                    if error_type == "missing":
                        errors.append(f"Missing required field: {field_path}")
                    elif error_type == "value_error":
                        errors.append(f"Invalid value for {field_path}: {error_msg}")
                    else:
                        errors.append(f"Validation error in {field_path}: {error_msg}")

            except ImportError as e:
                # Fallback to basic validation if imports fail
                errors.append(f"Could not import handler validation models: {e}")
                # Basic fallback validation for handler contracts
                if "name" not in content:
                    errors.append("Missing required field: name")
                if "version" in content:
                    errors.append(
                        "Deprecated field: version. Use contract_version instead."
                    )
                if "contract_version" not in content:
                    errors.append("Missing required field: contract_version")
                else:
                    # Validate contract_version is a structured object (dict with major/minor/patch)
                    cv = content.get("contract_version")
                    if not isinstance(cv, dict):
                        errors.append(
                            "contract_version must be a structured object "
                            "{major: X, minor: Y, patch: Z}, not a string"
                        )
                    elif not all(k in cv for k in ("major", "minor", "patch")):
                        errors.append(
                            "contract_version must have major, minor, and patch fields"
                        )
                if "descriptor" not in content:
                    errors.append("Missing required field: descriptor")
                if "input_model" not in content:
                    errors.append("Missing required field: input_model")
                if "output_model" not in content:
                    errors.append("Missing required field: output_model")

            except Exception as e:
                # Handle any other errors during validation
                errors.append(f"Handler contract validation error: {e}")

            return errors

        # Check if this appears to be an ONEX metadata contract (has any contract-related fields)
        contract_indicators = {
            "contract_version",
            "node_type",
            "metadata",
            "inputs",
            "outputs",
            "configuration",
            "description",
        }
        if any(field in content for field in contract_indicators):
            # Use standalone validator to avoid circular imports
            try:
                from pydantic import ValidationError
                from yaml_contract_validator import MinimalYamlContract

                # Validate using Pydantic model
                MinimalYamlContract.validate_yaml_content(content)

            except ValidationError as e:
                # Extract meaningful error messages from Pydantic validation
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error["loc"])
                    error_msg = error["msg"]
                    error_type = error["type"]

                    if error_type == "missing":
                        errors.append(f"Missing required field: {field_path}")
                    elif error_type == "value_error":
                        errors.append(f"Invalid value for {field_path}: {error_msg}")
                    else:
                        errors.append(f"Validation error in {field_path}: {error_msg}")

            except ImportError as e:
                # Fallback to basic validation if imports fail
                errors.append(f"Could not import validation models: {e}")
                # Basic fallback validation
                if "contract_version" not in content:
                    errors.append("Missing required field: contract_version")
                if "node_type" not in content:
                    errors.append("Missing required field: node_type")

            except Exception as e:
                # Handle any other errors during validation
                errors.append(f"Contract validation error: {e}")

    return errors


def discover_yaml_files_optimized(base_path: Path) -> Iterator[Path]:
    """Discover YAML files in base_path, skipping archived and invalid fixture dirs."""
    try:
        # Single walk through directory tree with immediate filtering
        for root, dirs, files in os.walk(base_path):
            root_path = Path(root)

            # Skip archived directories and test fixtures early
            dirs_to_skip = []
            for dir_name in dirs:
                if dir_name in ("archived", "__pycache__") or dir_name.startswith("."):
                    dirs_to_skip.append(dir_name)

            # Remove from dirs to prevent os.walk from recursing
            for skip_dir in dirs_to_skip:
                if skip_dir in dirs:
                    dirs.remove(skip_dir)

            # Skip if we're in an archived path or invalid test fixtures
            root_str = str(root_path)
            root_parts = root_path.parts
            if (
                "/archived/" in root_str
                or "archived" in root_parts
                or "tests/fixtures/validation/invalid/" in root_str
                or "tests/unit/contracts/fixtures/" in root_str
                or (
                    "tests" in root_parts
                    and "fixtures" in root_parts
                    and "validation" in root_parts
                    and "invalid" in root_parts
                )
                or (
                    "tests" in root_parts
                    and "unit" in root_parts
                    and "contracts" in root_parts
                    and "fixtures" in root_parts
                )
            ):
                continue

            # Process files with immediate YAML filtering
            for file_name in files:
                if file_name.endswith((".yaml", ".yml")) and not file_name.startswith(
                    "."
                ):
                    yield root_path / file_name

    except (OSError, PermissionError) as e:
        print(f"Error during file discovery: {e}", file=sys.stderr)
        raise


def setup_timeout_handler() -> None:
    """Legacy no-op for backward compatibility. Use timeout_context() instead."""


def main():
    """CLI entry point: parse args, discover YAML files, validate, report results."""
    try:
        parser = argparse.ArgumentParser(description="Validate YAML contracts")
        parser.add_argument("path", nargs="?", default=".", help="Path to validate")
        args = parser.parse_args()
    except SystemExit as e:
        return e.code if e.code is not None else 1
    except Exception as e:
        print(f"❌ Error parsing arguments: {e}")
        return 1

    try:
        base_path = Path(args.path)

        # Check if base path exists and is accessible
        if not base_path.exists():
            print(f"❌ Path does not exist: {base_path}")
            return 1

        if not os.access(base_path, os.R_OK):
            print(f"❌ Cannot read path: {base_path}")
            return 1

    except OSError as e:
        print(f"❌ OS error accessing path: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error processing path: {e}")
        return 1

    # File discovery with cross-platform timeout
    try:
        yaml_files = []

        with timeout_context("file_discovery"):
            yaml_files = list(discover_yaml_files_optimized(base_path))

    except timeout_utils.TimeoutError:
        print("❌ Timeout during file discovery")
        return 1
    except PermissionError as e:
        print(f"❌ Permission denied during file discovery: {e}")
        return 1
    except OSError as e:
        print(f"❌ OS error during file discovery: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error during file discovery: {e}")
        return 1

    if not yaml_files:
        print("✅ Contract validation: No YAML files to validate")
        return 0

    total_errors = 0
    processed_files = 0

    # Validation with cross-platform timeout and cleanup
    def cleanup_on_timeout():
        """Cleanup function for timeout scenarios."""
        print(
            f"\n⚠️  Validation interrupted after processing {processed_files}/{len(yaml_files)} files"
        )
        # Could add more cleanup logic here if needed

    try:
        with timeout_context("validation", cleanup_func=cleanup_on_timeout):
            for yaml_file in yaml_files:
                try:
                    errors = validate_yaml_file(yaml_file)
                    processed_files += 1

                    if errors:
                        print(f"❌ {yaml_file}:")
                        for error in errors:
                            print(f"   {error}")
                        total_errors += len(errors)

                except Exception as e:
                    print(f"❌ {yaml_file}: Unexpected validation error: {e}")
                    total_errors += 1

    except timeout_utils.TimeoutError:
        print(
            f"❌ Validation timeout after processing {processed_files}/{len(yaml_files)} files"
        )
        return 1
    except KeyboardInterrupt:
        print(
            f"\n❌ Validation interrupted after processing {processed_files}/{len(yaml_files)} files"
        )
        return 1
    except Exception as e:
        print(f"❌ Unexpected error during validation: {e}")
        return 1

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
