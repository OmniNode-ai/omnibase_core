#!/usr/bin/env python3
"""
ONEX Contract Fingerprint Regeneration Script.

Regenerates fingerprints for ONEX contracts in-place by:
1. Reading contract YAML files
2. Computing SHA256 of canonical content (excluding fingerprint field)
3. Updating fingerprint field with `{version}:{first-12-chars-of-hash}`
4. Writing back YAML preserving formatting

This script is essential for maintaining contract integrity after modifications.
Run it whenever contract content changes to ensure fingerprints stay in sync.

Fingerprint Format:
    <semver>:<sha256-first-12-hex-chars>
    Example: 0.4.0:8fa1e2b4c9d1

Usage:
    # Regenerate fingerprint for a single contract
    poetry run python scripts/regenerate_fingerprints.py contracts/my_contract.yaml

    # Regenerate fingerprints for all contracts in a directory
    poetry run python scripts/regenerate_fingerprints.py contracts/ --recursive

    # Dry-run mode (show changes without modifying files)
    poetry run python scripts/regenerate_fingerprints.py contracts/ --dry-run

    # Verbose output showing before/after fingerprints
    poetry run python scripts/regenerate_fingerprints.py contracts/ -v

    # Output results as JSON for CI/CD integration
    poetry run python scripts/regenerate_fingerprints.py contracts/ --json

Exit Codes:
    0 - Success (fingerprints regenerated or already up-to-date)
    1 - Some files had fingerprint changes (useful for CI to detect drift)
    2 - Error (file not found, invalid format, etc.)

When to Run:
    - After modifying contract YAML content
    - After upgrading contract version
    - Before committing contract changes
    - In CI/CD to verify fingerprints are current

Related:
    - Linear Ticket: OMN-263
    - Architecture: docs/architecture/CONTRACT_STABILITY_SPEC.md
    - Hash Registry: src/omnibase_core/contracts/hash_registry.py
    - Fingerprint CLI: scripts/compute_contract_fingerprint.py
    - Contract Linter: scripts/lint_contract.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel  # noqa: TC002 - Used at runtime in type dict

from omnibase_core.contracts.hash_registry import compute_contract_fingerprint
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_contract_fingerprint import (
        ModelContractFingerprint,
    )


# ==============================================================================
# CONSTANTS
# ==============================================================================

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB - DoS prevention

# Node type to model class mapping (from compute_contract_fingerprint.py)
NODE_TYPE_TO_MODEL: dict[str, type[BaseModel]] = {
    # COMPUTE types
    "COMPUTE_GENERIC": ModelContractCompute,
    "TRANSFORMER": ModelContractCompute,
    "AGGREGATOR": ModelContractCompute,
    "FUNCTION": ModelContractCompute,
    "MODEL": ModelContractCompute,
    "PLUGIN": ModelContractCompute,
    "SCHEMA": ModelContractCompute,
    "NODE": ModelContractCompute,
    "SERVICE": ModelContractCompute,
    # EFFECT types
    "EFFECT_GENERIC": ModelContractEffect,
    "GATEWAY": ModelContractEffect,
    "VALIDATOR": ModelContractEffect,
    "TOOL": ModelContractEffect,
    "AGENT": ModelContractEffect,
    # REDUCER types
    "REDUCER_GENERIC": ModelContractReducer,
    # ORCHESTRATOR types
    "ORCHESTRATOR_GENERIC": ModelContractOrchestrator,
    "WORKFLOW": ModelContractOrchestrator,
}


# ==============================================================================
# DATA CLASSES
# ==============================================================================


@dataclass
class RegenerateResult:
    """Result of regenerating a single contract file's fingerprint."""

    file_path: Path
    old_fingerprint: str | None
    new_fingerprint: str | None
    changed: bool
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON output."""
        return {
            "file": str(self.file_path),
            "old_fingerprint": self.old_fingerprint,
            "new_fingerprint": self.new_fingerprint,
            "changed": self.changed,
            "error": self.error,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


# ==============================================================================
# CONTRACT MODEL DETECTION
# ==============================================================================


def detect_contract_model(contract_data: dict[str, object]) -> type[BaseModel] | None:
    """Detect the appropriate contract model class from YAML data.

    Args:
        contract_data: Parsed YAML contract data as a dictionary.

    Returns:
        Pydantic model class for the contract type, or None if not determinable.
    """
    node_type = contract_data.get("node_type")

    if node_type is None or not isinstance(node_type, str):
        return None

    # Check for strict contract (has version and required fields)
    has_strict_fields = all(
        field in contract_data
        for field in ("name", "input_model", "output_model", "description")
    )
    has_version = "version" in contract_data
    has_contract_version = "contract_version" in contract_data

    if has_version and not has_contract_version and has_strict_fields:
        model_class = NODE_TYPE_TO_MODEL.get(node_type.upper())
        if model_class is not None:
            return model_class

    # Fall back to flexible ModelYamlContract
    return ModelYamlContract


# ==============================================================================
# FINGERPRINT REGENERATION
# ==============================================================================


@dataclass
class FingerprintResult:
    """Result of fingerprint computation attempt."""

    fingerprint: ModelContractFingerprint | None
    error: str | None = None


def compute_fingerprint_for_contract(
    contract_data: dict[str, object],
) -> FingerprintResult:
    """Compute fingerprint for parsed contract data.

    Args:
        contract_data: Parsed YAML contract data.

    Returns:
        FingerprintResult with computed fingerprint or error message.
    """
    model_class = detect_contract_model(contract_data)
    if model_class is None:
        return FingerprintResult(
            fingerprint=None,
            error="Could not detect contract model type",
        )

    try:
        # Remove existing fingerprint to avoid circular dependency
        data_for_fingerprint = {
            k: v for k, v in contract_data.items() if k != "fingerprint"
        }
        contract = model_class.model_validate(data_for_fingerprint)
        fingerprint = compute_contract_fingerprint(contract)
        return FingerprintResult(fingerprint=fingerprint)
    except ModelOnexError as e:
        return FingerprintResult(
            fingerprint=None,
            error=f"ONEX error: {e.message}",
        )
    except ValueError as e:
        # Pydantic ValidationError inherits from ValueError
        return FingerprintResult(
            fingerprint=None,
            error=f"Validation error: {e}",
        )
    except TypeError as e:
        return FingerprintResult(
            fingerprint=None,
            error=f"Type error: {e}",
        )


def update_fingerprint_in_yaml(
    content: str,
    new_fingerprint: str,
) -> str:
    """Update fingerprint field in YAML content while preserving formatting.

    Args:
        content: Original YAML file content.
        new_fingerprint: New fingerprint value to set.

    Returns:
        Updated YAML content with new fingerprint.
    """
    # Pattern to match existing fingerprint field
    fingerprint_pattern = re.compile(
        r'^(\s*)fingerprint:\s*["\']?[\w.:/-]+["\']?\s*$',
        re.MULTILINE,
    )

    match = fingerprint_pattern.search(content)
    if match:
        # Replace existing fingerprint
        indent = match.group(1)
        return fingerprint_pattern.sub(
            f'{indent}fingerprint: "{new_fingerprint}"',
            content,
        )

    # No existing fingerprint - add after version field
    version_pattern = re.compile(
        r'^(\s*)(version:\s*["\']?[\w./-]+["\']?\s*)$',
        re.MULTILINE,
    )
    version_match = version_pattern.search(content)
    if version_match:
        indent = version_match.group(1)
        version_line = version_match.group(0)
        return content.replace(
            version_line,
            f'{version_line}\n{indent}fingerprint: "{new_fingerprint}"',
        )

    # Fallback: add at end of file
    return content.rstrip() + f'\nfingerprint: "{new_fingerprint}"\n'


def regenerate_fingerprint(
    file_path: Path,
    dry_run: bool = False,
) -> RegenerateResult:
    """Regenerate fingerprint for a single contract file.

    Args:
        file_path: Path to the contract YAML file.
        dry_run: If True, don't modify the file.

    Returns:
        RegenerateResult with details of the operation.
    """
    # Validate file exists
    if not file_path.exists():
        return RegenerateResult(
            file_path=file_path,
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            error=f"File not found: {file_path}",
        )

    if not file_path.is_file():
        return RegenerateResult(
            file_path=file_path,
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            error=f"Not a file: {file_path}",
        )

    # Check file size
    try:
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            return RegenerateResult(
                file_path=file_path,
                old_fingerprint=None,
                new_fingerprint=None,
                changed=False,
                error=f"File too large: {file_size} bytes",
            )
    except OSError as e:
        return RegenerateResult(
            file_path=file_path,
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            error=f"Cannot read file: {e}",
        )

    # Read file
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return RegenerateResult(
            file_path=file_path,
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            error=f"Encoding error: {e}",
        )

    # Parse YAML first, then validate with Pydantic model
    # Note: yaml.safe_load is required here as the first step before Pydantic validation
    # because we need to detect the contract type from node_type before selecting the model
    try:
        contract_data = yaml.safe_load(content)  # noqa: ONEX-YAML
    except yaml.YAMLError as e:
        return RegenerateResult(
            file_path=file_path,
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            error=f"YAML parse error: {e}",
        )

    if not isinstance(contract_data, dict):
        return RegenerateResult(
            file_path=file_path,
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            skipped=True,
            skip_reason="Not a YAML mapping (might not be a contract)",
        )

    # Check for required contract fields
    if "node_type" not in contract_data:
        return RegenerateResult(
            file_path=file_path,
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            skipped=True,
            skip_reason="Missing node_type field (not an ONEX contract)",
        )

    # Get existing fingerprint
    old_fingerprint = contract_data.get("fingerprint")
    if old_fingerprint and not isinstance(old_fingerprint, str):
        old_fingerprint = str(old_fingerprint)

    # Compute new fingerprint
    fingerprint_result = compute_fingerprint_for_contract(contract_data)
    if fingerprint_result.fingerprint is None:
        return RegenerateResult(
            file_path=file_path,
            old_fingerprint=old_fingerprint,
            new_fingerprint=None,
            changed=False,
            error=fingerprint_result.error or "Failed to compute fingerprint",
        )

    new_fingerprint = str(fingerprint_result.fingerprint)

    # Check if changed
    changed = old_fingerprint != new_fingerprint

    # Write back if not dry run and changed
    if changed and not dry_run:
        try:
            updated_content = update_fingerprint_in_yaml(content, new_fingerprint)
            file_path.write_text(updated_content, encoding="utf-8")
        except OSError as e:
            return RegenerateResult(
                file_path=file_path,
                old_fingerprint=old_fingerprint,
                new_fingerprint=new_fingerprint,
                changed=changed,
                error=f"Failed to write file: {e}",
            )

    return RegenerateResult(
        file_path=file_path,
        old_fingerprint=old_fingerprint,
        new_fingerprint=new_fingerprint,
        changed=changed,
    )


# ==============================================================================
# FILE DISCOVERY
# ==============================================================================


def find_contract_files(
    directory: Path,
    recursive: bool = False,
) -> list[Path]:
    """Find contract YAML files in a directory.

    Args:
        directory: Directory to search.
        recursive: Search recursively.

    Returns:
        List of contract file paths.
    """
    patterns = ["*.yaml", "*.yml"]
    files: list[Path] = []

    for pattern in patterns:
        if recursive:
            files.extend(directory.rglob(pattern))
        else:
            files.extend(directory.glob(pattern))

    # Filter out non-contract directories
    excluded_dirs = {
        "__pycache__",
        ".git",
        "node_modules",
        ".venv",
        "archived",
        "archive",
    }
    contract_files = [
        f for f in files if not any(part in excluded_dirs for part in f.parts)
    ]

    return sorted(contract_files)


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


def main() -> int:
    """Main entry point for fingerprint regeneration CLI.

    Returns:
        Exit code:
        - 0: Success (all fingerprints up-to-date or regenerated)
        - 1: Fingerprints were changed (useful for CI drift detection)
        - 2: Error occurred
    """
    parser = argparse.ArgumentParser(
        description="Regenerate fingerprints for ONEX contracts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Regenerate single contract
    poetry run python scripts/regenerate_fingerprints.py contracts/my_contract.yaml

    # Regenerate all contracts in directory
    poetry run python scripts/regenerate_fingerprints.py contracts/ --recursive

    # Dry-run (preview changes)
    poetry run python scripts/regenerate_fingerprints.py contracts/ --dry-run -v

    # CI/CD: check if fingerprints are current
    poetry run python scripts/regenerate_fingerprints.py contracts/ --dry-run --json
""",
    )
    parser.add_argument(
        "paths",
        type=Path,
        nargs="+",
        help="Contract file(s) or directory(ies) to process",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively search directories",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output for each file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Collect files to process
    files_to_process: list[Path] = []
    for path in args.paths:
        if path.is_file():
            files_to_process.append(path)
        elif path.is_dir():
            files_to_process.extend(find_contract_files(path, args.recursive))
        else:
            if args.json:
                print(json.dumps({"error": f"Path not found: {path}"}))
            else:
                print(f"Error: Path not found: {path}", file=sys.stderr)
            return 2

    if not files_to_process:
        if args.json:
            print(json.dumps({"error": "No contract files found"}))
        else:
            print("No contract files found", file=sys.stderr)
        return 2

    # Process files
    results: list[RegenerateResult] = []
    for file_path in files_to_process:
        result = regenerate_fingerprint(file_path, dry_run=args.dry_run)
        results.append(result)

    # Calculate summary
    total_files = len(results)
    changed_count = sum(1 for r in results if r.changed)
    error_count = sum(1 for r in results if r.error)
    skipped_count = sum(1 for r in results if r.skipped)

    # Output results
    if args.json:
        output = {
            "summary": {
                "total_files": total_files,
                "changed": changed_count,
                "errors": error_count,
                "skipped": skipped_count,
                "dry_run": args.dry_run,
            },
            "results": [r.to_dict() for r in results],
        }
        print(json.dumps(output, indent=2))
    else:
        if args.verbose or args.dry_run:
            for result in results:
                if result.error:
                    print(f"ERROR: {result.file_path}: {result.error}")
                elif result.skipped:
                    print(f"SKIP: {result.file_path}: {result.skip_reason}")
                elif result.changed:
                    action = "WOULD UPDATE" if args.dry_run else "UPDATED"
                    print(f"{action}: {result.file_path}")
                    print(f"  Old: {result.old_fingerprint or '(none)'}")
                    print(f"  New: {result.new_fingerprint}")
                elif args.verbose:
                    print(f"OK: {result.file_path}: {result.new_fingerprint}")

        # Summary
        print()
        print("=" * 60)
        print("Fingerprint Regeneration Summary")
        print("=" * 60)
        print(f"  Total files: {total_files}")
        print(f"  Changed: {changed_count}")
        print(f"  Errors: {error_count}")
        print(f"  Skipped: {skipped_count}")
        if args.dry_run:
            print("  Mode: DRY RUN (no files modified)")

    # Return exit code
    if error_count > 0:
        return 2
    if changed_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
