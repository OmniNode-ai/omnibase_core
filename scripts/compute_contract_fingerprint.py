#!/usr/bin/env python3
"""
ONEX Contract Fingerprint Computation CLI.

Computes deterministic SHA256 fingerprints for ONEX contracts, enabling
drift detection between declarative YAML contracts and generated code.

Fingerprint Format:
    <semver>:<sha256-first-12-hex-chars>
    Example: 0.4.0:8fa1e2b4c9d1

The fingerprint serves two purposes:
    1. Version tracking: The semantic version provides human-readable context
       about the contract's compatibility level.
    2. Integrity verification: The hash prefix (from SHA256) ensures the
       contract content hasn't been modified unexpectedly.

Usage:
    # Compute fingerprint for a YAML contract
    poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml

    # Compute fingerprint with full hash output
    poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --verbose

    # Validate existing fingerprint in contract file
    poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --validate

    # Output as JSON for machine processing
    poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --json

    # Process multiple contract files
    poetry run python scripts/compute_contract_fingerprint.py contracts/*.yaml

Exit Codes:
    0 - Success (fingerprint computed or validation passed)
    1 - Validation failed (fingerprint mismatch)
    2 - Error (file not found, invalid format, etc.)

Related:
    - Linear Ticket: OMN-263
    - Architecture: docs/architecture/CONTRACT_STABILITY_SPEC.md
    - Hash Registry: src/omnibase_core/contracts/hash_registry.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml
from pydantic import BaseModel

from omnibase_core.contracts.hash_registry import (
    compute_contract_fingerprint,
)
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
# CONTRACT TYPE DETECTION
# ==============================================================================

# Mapping of node_type values to strict contract model classes
# These require all base fields (name, version, description, input_model, output_model)
NODE_TYPE_TO_STRICT_MODEL: dict[str, type[BaseModel]] = {
    # COMPUTE types
    "COMPUTE_GENERIC": ModelContractCompute,
    "TRANSFORMER": ModelContractCompute,
    "AGGREGATOR": ModelContractCompute,
    # EFFECT types
    "EFFECT_GENERIC": ModelContractEffect,
    "GATEWAY": ModelContractEffect,
    "VALIDATOR": ModelContractEffect,
    # REDUCER types
    "REDUCER_GENERIC": ModelContractReducer,
    # ORCHESTRATOR types
    "ORCHESTRATOR_GENERIC": ModelContractOrchestrator,
}


def is_strict_contract(contract_data: dict[str, object]) -> bool:
    """Check if contract data matches strict typed contract schema.

    Strict contracts have 'version' field (ModelSemVer) and required base fields
    like 'name', 'input_model', 'output_model', 'description'.

    Flexible YAML contracts use 'contract_version' instead of 'version' and
    don't require the base fields.

    Args:
        contract_data: Parsed YAML contract data.

    Returns:
        True if contract appears to be strict typed, False for flexible YAML.
    """
    # Strict contracts use 'version', flexible YAML uses 'contract_version'
    has_version = "version" in contract_data
    has_contract_version = "contract_version" in contract_data

    # Strict contracts require name, input_model, output_model, description
    has_strict_fields = all(
        field in contract_data
        for field in ("name", "input_model", "output_model", "description")
    )

    # If has 'version' (not 'contract_version') and strict fields, it's strict
    if has_version and not has_contract_version and has_strict_fields:
        return True

    # If has 'contract_version', it's flexible YAML
    if has_contract_version:
        return False

    # If missing both version fields but has strict fields, try strict
    if has_strict_fields:
        return True

    # Default to flexible for better compatibility
    return False


def detect_contract_model(contract_data: dict[str, object]) -> type[BaseModel]:
    """Detect the appropriate contract model class from YAML data.

    Uses heuristics to determine whether to use strict typed contracts
    or flexible ModelYamlContract. Falls back to ModelYamlContract
    for maximum compatibility.

    Args:
        contract_data: Parsed YAML contract data.

    Returns:
        Pydantic model class appropriate for the contract type.

    Raises:
        ModelOnexError: If node_type is missing.
    """
    node_type = contract_data.get("node_type")

    if node_type is None:
        raise ModelOnexError(
            message="Contract missing required 'node_type' field",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            contract_keys=list(contract_data.keys()),
            suggestion="Add 'node_type' field (e.g., COMPUTE_GENERIC, REDUCER_GENERIC)",
        )

    if not isinstance(node_type, str):
        raise ModelOnexError(
            message=f"Invalid node_type: expected string, got {type(node_type).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            node_type_value=str(node_type),
            node_type_type=type(node_type).__name__,
        )

    # Check if this is a strict typed contract
    if is_strict_contract(contract_data):
        model_class = NODE_TYPE_TO_STRICT_MODEL.get(node_type)
        if model_class is not None:
            return model_class

    # Fall back to flexible ModelYamlContract for maximum compatibility
    # This handles contracts with 'contract_version' and extra fields
    # Cast is needed because ModelYamlContract uses Any in some fields
    return cast(type[BaseModel], ModelYamlContract)


# ==============================================================================
# CONTRACT LOADING
# ==============================================================================


def load_contract_from_yaml(file_path: Path) -> BaseModel:
    """Load and validate a contract from a YAML file.

    Reads the YAML file, detects the contract type from node_type,
    and returns a validated Pydantic model instance.

    Args:
        file_path: Path to the YAML contract file.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ModelOnexError: If file cannot be read, parsed, or validated.
    """
    if not file_path.exists():
        raise ModelOnexError(
            message=f"Contract file not found: {file_path}",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            file_path=str(file_path),
        )

    if not file_path.is_file():
        raise ModelOnexError(
            message=f"Path is not a file: {file_path}",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            file_path=str(file_path),
        )

    # Check file extension
    suffix = file_path.suffix.lower()
    if suffix not in {".yaml", ".yml", ".json"}:
        raise ModelOnexError(
            message=f"Unsupported file format: {suffix}",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            file_path=str(file_path),
            suffix=suffix,
            supported_formats=[".yaml", ".yml", ".json"],
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ModelOnexError(
            message=f"Failed to read file (encoding error): {e}",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            file_path=str(file_path),
            encoding_error=str(e),
        ) from e
    except PermissionError as e:
        raise ModelOnexError(
            message=f"Permission denied reading file: {file_path}",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            file_path=str(file_path),
        ) from e

    # Parse YAML/JSON
    try:
        if suffix == ".json":
            contract_data = json.loads(content)
        else:
            contract_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ModelOnexError(
            message=f"YAML parsing error: {e}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            file_path=str(file_path),
            yaml_error=str(e),
        ) from e
    except json.JSONDecodeError as e:
        raise ModelOnexError(
            message=f"JSON parsing error: {e}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            file_path=str(file_path),
            json_error=str(e),
        ) from e

    if contract_data is None:
        raise ModelOnexError(
            message="Contract file is empty",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            file_path=str(file_path),
        )

    if not isinstance(contract_data, dict):
        raise ModelOnexError(
            message=f"Contract must be a mapping, got {type(contract_data).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            file_path=str(file_path),
            actual_type=type(contract_data).__name__,
        )

    # Detect contract model and validate
    model_class = detect_contract_model(contract_data)

    try:
        return model_class.model_validate(contract_data)
    except ModelOnexError:
        raise
    except ValueError as e:
        # Pydantic ValidationError inherits from ValueError
        raise ModelOnexError(
            message=f"Contract validation failed: {e}",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            file_path=str(file_path),
            model_class=model_class.__name__,
            validation_error=str(e),
        ) from e


# ==============================================================================
# FINGERPRINT OPERATIONS
# ==============================================================================


def compute_fingerprint_for_file(
    file_path: Path,
    verbose: bool = False,
) -> ModelContractFingerprint:
    """Compute fingerprint for a contract file.

    Args:
        file_path: Path to the contract file (YAML or JSON).
        verbose: If True, include normalized content in result.

    Returns:
        Computed fingerprint model.

    Raises:
        ModelOnexError: If fingerprint computation fails.
    """
    contract = load_contract_from_yaml(file_path)
    return compute_contract_fingerprint(
        contract,
        include_normalized_content=verbose,
    )


def validate_existing_fingerprint(
    contract: BaseModel,
    computed: ModelContractFingerprint,
) -> tuple[bool, str | None]:
    """Validate computed fingerprint against existing fingerprint in contract.

    Checks if the contract has a fingerprint field and compares it
    to the computed fingerprint.

    Args:
        contract: Validated contract model.
        computed: Computed fingerprint.

    Returns:
        Tuple of (is_valid, existing_fingerprint_string).
        is_valid is True if fingerprints match or no fingerprint exists.
        existing_fingerprint_string is the existing value or None.
    """
    existing_fingerprint = getattr(contract, "fingerprint", None)

    if existing_fingerprint is None:
        return True, None

    if not isinstance(existing_fingerprint, str):
        return True, None

    computed_str = str(computed)

    if existing_fingerprint == computed_str:
        return True, existing_fingerprint

    return False, existing_fingerprint


# ==============================================================================
# OUTPUT FORMATTING
# ==============================================================================


def format_result_text(
    file_path: Path,
    fingerprint: ModelContractFingerprint,
    verbose: bool = False,
    validation_result: tuple[bool, str | None] | None = None,
) -> str:
    """Format fingerprint result as human-readable text.

    Args:
        file_path: Path to the contract file.
        fingerprint: Computed fingerprint.
        verbose: If True, include full hash and normalized content.
        validation_result: Optional validation result tuple.

    Returns:
        Formatted text output.
    """
    lines: list[str] = []

    lines.append(f"File: {file_path}")
    lines.append(f"Fingerprint: {fingerprint}")

    if verbose:
        lines.append(f"Full Hash: {fingerprint.full_hash}")
        lines.append(f"Version: {fingerprint.version}")
        lines.append(f"Computed At: {fingerprint.computed_at.isoformat()}")

    if validation_result is not None:
        is_valid, existing = validation_result
        if existing is not None:
            if is_valid:
                lines.append(f"Validation: PASSED (matches existing: {existing})")
            else:
                lines.append("Validation: FAILED")
                lines.append(f"  Expected: {existing}")
                lines.append(f"  Computed: {fingerprint}")

    return "\n".join(lines)


def format_result_json(
    file_path: Path,
    fingerprint: ModelContractFingerprint,
    verbose: bool = False,
    validation_result: tuple[bool, str | None] | None = None,
) -> dict[str, object]:
    """Format fingerprint result as JSON-serializable dict.

    Args:
        file_path: Path to the contract file.
        fingerprint: Computed fingerprint.
        verbose: If True, include full hash and normalized content.
        validation_result: Optional validation result tuple.

    Returns:
        JSON-serializable dictionary.
    """
    result: dict[str, object] = {
        "file": str(file_path),
        "fingerprint": str(fingerprint),
        "version": str(fingerprint.version),
        "hash_prefix": fingerprint.hash_prefix,
    }

    if verbose:
        result["full_hash"] = fingerprint.full_hash
        result["computed_at"] = fingerprint.computed_at.isoformat()
        if fingerprint.normalized_content:
            result["normalized_content"] = fingerprint.normalized_content

    if validation_result is not None:
        is_valid, existing = validation_result
        result["validation"] = {
            "passed": is_valid,
            "existing_fingerprint": existing,
        }

    return result


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


def process_single_file(
    file_path: Path,
    verbose: bool,
    validate: bool,
    json_output: bool,
) -> tuple[int, dict[str, object] | str]:
    """Process a single contract file.

    Args:
        file_path: Path to the contract file.
        verbose: If True, include verbose output.
        validate: If True, validate against existing fingerprint.
        json_output: If True, return JSON-serializable dict.

    Returns:
        Tuple of (exit_code, output).
    """
    try:
        contract = load_contract_from_yaml(file_path)
        fingerprint = compute_contract_fingerprint(
            contract,
            include_normalized_content=verbose,
        )

        validation_result: tuple[bool, str | None] | None = None
        exit_code = 0

        if validate:
            validation_result = validate_existing_fingerprint(
                contract,
                fingerprint,
            )
            if not validation_result[0]:
                exit_code = 1

        if json_output:
            return exit_code, format_result_json(
                file_path,
                fingerprint,
                verbose,
                validation_result,
            )
        else:
            return exit_code, format_result_text(
                file_path,
                fingerprint,
                verbose,
                validation_result,
            )

    except ModelOnexError as e:
        if json_output:
            return 2, {
                "file": str(file_path),
                "error": e.message,
                "error_code": e.error_code.value if e.error_code else None,
            }
        else:
            return 2, f"Error processing {file_path}: {e.message}"


def main() -> int:
    """Main entry point for the contract fingerprint CLI.

    Parses command line arguments, processes contract files, and
    outputs fingerprint results.

    Returns:
        Exit code:
        - 0: Success (fingerprint computed or validation passed)
        - 1: Validation failed (fingerprint mismatch)
        - 2: Error (file not found, invalid format, etc.)
    """
    parser = argparse.ArgumentParser(
        description="Compute deterministic fingerprints for ONEX contracts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Compute fingerprint for a contract
    poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml

    # Show full hash and details
    poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --verbose

    # Validate existing fingerprint
    poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --validate

    # Output as JSON
    poetry run python scripts/compute_contract_fingerprint.py contracts/my_contract.yaml --json
""",
    )
    parser.add_argument(
        "files",
        type=Path,
        nargs="+",
        help="Contract file(s) to process (YAML or JSON)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Include full hash, normalized content, and additional details",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate computed fingerprint against existing fingerprint in contract",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON for machine processing",
    )

    args = parser.parse_args()

    # Track overall exit code (worst case)
    overall_exit_code = 0
    results: list[dict[str, object]] = []
    text_outputs: list[str] = []

    for file_path in args.files:
        exit_code, output = process_single_file(
            file_path,
            args.verbose,
            args.validate,
            args.json,
        )

        overall_exit_code = max(overall_exit_code, exit_code)

        if args.json:
            if isinstance(output, dict):
                results.append(output)
            else:
                results.append({"error": str(output)})
        elif isinstance(output, str):
            text_outputs.append(output)
        else:
            text_outputs.append(str(output))

    # Output results
    if args.json:
        if len(results) == 1:
            print(json.dumps(results[0], indent=2))
        else:
            print(json.dumps({"results": results}, indent=2))
    else:
        for i, output in enumerate(text_outputs):
            if i > 0:
                print()  # Blank line between files
            print(output)

    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
