#!/usr/bin/env python3
"""
Generic YAML contract validation for omni* repositories.
Validates that YAML contract files follow ONEX standards.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path
from typing import Any

import yaml

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - prevent DoS attacks
FILE_DISCOVERY_TIMEOUT = 30  # seconds
VALIDATION_TIMEOUT = 300  # 5 minutes


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
        with open(file_path, "r", encoding="utf-8") as f:
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
        errors.append(f"OS error reading file: {e}")
        return errors
    except IOError as e:
        errors.append(f"IO error reading file: {e}")
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

    return errors


def setup_timeout_handler():
    """Setup timeout handler for long-running validations."""

    def timeout_handler(signum, frame):
        raise TimeoutError("Validation operation timed out")

    signal.signal(signal.SIGALRM, timeout_handler)


def main():
    """Main validation function."""
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

    # Setup timeout for file discovery (30 seconds)
    setup_timeout_handler()

    try:
        signal.alarm(FILE_DISCOVERY_TIMEOUT)
        yaml_files = list(base_path.rglob("*.yaml")) + list(base_path.rglob("*.yml"))
        signal.alarm(0)  # Cancel timeout
    except TimeoutError:
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

    # Filter out archived files and invalid test fixtures
    try:
        yaml_files = [
            f
            for f in yaml_files
            if "/archived/" not in str(f)
            and "archived" not in f.parts
            and "tests/fixtures/validation/invalid/" not in str(f)
        ]
    except Exception as e:
        print(f"❌ Error filtering files: {e}")
        return 1

    if not yaml_files:
        print("✅ Contract validation: No YAML files to validate")
        return 0

    total_errors = 0
    processed_files = 0

    # Setup timeout for validation
    try:
        signal.alarm(VALIDATION_TIMEOUT)

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

        signal.alarm(0)  # Cancel timeout

    except TimeoutError:
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
