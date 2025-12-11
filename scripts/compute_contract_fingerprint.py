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
# SECURITY CONSTANTS
# ==============================================================================

# Maximum file size to prevent DoS (consistent with lint_contract.py)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


# ==============================================================================
# CONTRACT TYPE DETECTION
# ==============================================================================

# Mapping of node_type values to strict contract model classes
# These require all base fields (name, version, description, input_model, output_model)
# Note: Keys are uppercase to match EnumNodeType values directly
NODE_TYPE_TO_STRICT_MODEL: dict[str, type[BaseModel]] = {
    # COMPUTE types (maps to ModelContractCompute)
    "COMPUTE_GENERIC": ModelContractCompute,
    "TRANSFORMER": ModelContractCompute,
    "AGGREGATOR": ModelContractCompute,
    "FUNCTION": ModelContractCompute,
    "MODEL": ModelContractCompute,
    "PLUGIN": ModelContractCompute,
    "SCHEMA": ModelContractCompute,
    "NODE": ModelContractCompute,
    "SERVICE": ModelContractCompute,
    # EFFECT types (maps to ModelContractEffect)
    "EFFECT_GENERIC": ModelContractEffect,
    "GATEWAY": ModelContractEffect,
    "VALIDATOR": ModelContractEffect,
    "TOOL": ModelContractEffect,
    "AGENT": ModelContractEffect,
    # REDUCER types (maps to ModelContractReducer)
    "REDUCER_GENERIC": ModelContractReducer,
    # ORCHESTRATOR types (maps to ModelContractOrchestrator)
    "ORCHESTRATOR_GENERIC": ModelContractOrchestrator,
    "WORKFLOW": ModelContractOrchestrator,
}


def is_strict_contract(contract_data: dict[str, object]) -> bool:
    """Check if contract data matches strict typed contract schema.

    Determines whether the contract should be validated against strict typed
    models (ModelContractCompute, etc.) or the flexible ModelYamlContract.

    Strict vs Flexible Contracts:
        **Strict Contracts** use:
        - 'version' field (ModelSemVer format, e.g., '1.0.0')
        - Required base fields: 'name', 'input_model', 'output_model', 'description'
        - Type-specific validation rules

        **Flexible YAML Contracts** use:
        - 'contract_version' field (alternative versioning)
        - Arbitrary extra fields allowed
        - Minimal validation for maximum compatibility

    Detection Logic:
        1. If has 'version' (not 'contract_version') AND all strict fields -> strict
        2. If has 'contract_version' -> flexible (regardless of other fields)
        3. If missing both version fields but has strict fields -> try strict
        4. Otherwise -> flexible (default for compatibility)

    Args:
        contract_data: Parsed YAML contract data as a dictionary.

    Returns:
        True if contract should use strict typed models (ModelContractCompute, etc.).
        False if contract should use flexible ModelYamlContract.

    Examples:
        >>> is_strict_contract({'version': '1.0.0', 'name': 'Test', ...})
        True
        >>> is_strict_contract({'contract_version': '1.0', 'name': 'Test'})
        False
        >>> is_strict_contract({'random_field': 'value'})
        False
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
    (ModelContractCompute, ModelContractEffect, etc.) or flexible ModelYamlContract.
    Falls back to ModelYamlContract for maximum compatibility with non-standard
    or legacy contracts.

    Detection Strategy:
        1. **Validate node_type**: Ensures node_type field exists and is a string.
           Raises ModelOnexError if missing or invalid type.

        2. **Check for strict contract**: Uses is_strict_contract() to determine if
           the contract has strict typed fields ('version' vs 'contract_version',
           required base fields like 'name', 'input_model', 'output_model').

        3. **Map to strict model**: If strict and node_type is in NODE_TYPE_TO_STRICT_MODEL,
           returns the corresponding typed model class (e.g., ModelContractCompute).

        4. **Fallback to flexible**: Returns ModelYamlContract if:
           - The contract is not strict (uses 'contract_version', missing base fields)
           - The node_type is not in NODE_TYPE_TO_STRICT_MODEL (new/custom types)

    Fallback Behavior:
        When node_type is not found in NODE_TYPE_TO_STRICT_MODEL mapping, this
        function falls back to ModelYamlContract. This ensures:
        - Forward compatibility with new node types added to the system
        - Backward compatibility with legacy contracts using non-standard fields
        - Maximum flexibility for experimental or custom contracts

        The fallback does NOT raise an error because:
        - The contract may still be valid for fingerprinting purposes
        - ModelYamlContract can handle arbitrary extra fields
        - Validation errors will surface during model_validate() if truly invalid

    Args:
        contract_data: Parsed YAML contract data as a dictionary. Must contain
            at minimum a 'node_type' field. Other required fields depend on
            whether it's a strict or flexible contract.

    Returns:
        Pydantic model class appropriate for the contract type:
        - ModelContractCompute for COMPUTE_GENERIC, TRANSFORMER, AGGREGATOR
        - ModelContractEffect for EFFECT_GENERIC, GATEWAY, VALIDATOR
        - ModelContractReducer for REDUCER_GENERIC
        - ModelContractOrchestrator for ORCHESTRATOR_GENERIC
        - ModelYamlContract for unknown node_types or flexible contracts

    Raises:
        ModelOnexError: If node_type field is missing from contract_data.
            Error code: VALIDATION_ERROR
            Context includes: contract_keys (list of keys in data)
            Suggestion provided for adding node_type field.

        ModelOnexError: If node_type is not a string (e.g., int, list, dict).
            Error code: VALIDATION_ERROR
            Context includes: node_type_value, node_type_type

    Examples:
        >>> detect_contract_model({'node_type': 'COMPUTE_GENERIC', 'version': '1.0.0', ...})
        ModelContractCompute

        >>> detect_contract_model({'node_type': 'CUSTOM_TYPE', 'contract_version': '1.0'})
        ModelYamlContract  # Falls back for unknown type

        >>> detect_contract_model({'name': 'test'})  # Missing node_type
        ModelOnexError: Contract missing required 'node_type' field

    See Also:
        - NODE_TYPE_TO_STRICT_MODEL: Mapping of node_type values to model classes.
        - is_strict_contract(): Determines if contract uses strict typed schema.
        - ModelYamlContract: Flexible contract model for non-standard contracts.
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
    and returns a validated Pydantic model instance. Handles both
    strict typed contracts and flexible ModelYamlContract.

    Process:
        1. Resolve symlinks for security
        2. Validate file exists and is a file
        3. Check file extension (.yaml, .yml, .json)
        4. Read file content with UTF-8 encoding
        5. Parse YAML/JSON content
        6. Detect appropriate model class (detect_contract_model)
        7. Validate against Pydantic model

    Security Measures:
        - Resolves symlinks to prevent path traversal attacks
        - Uses yaml.safe_load to prevent arbitrary code execution
        - Validates file extension to ensure expected format

    Supported Formats:
        - .yaml, .yml: YAML format (recommended)
        - .json: JSON format (also supported)

    Args:
        file_path: Path to the YAML or JSON contract file.
            Symlinks are resolved before reading.

    Returns:
        Validated Pydantic model instance. The specific model class
        depends on the contract's node_type and whether it's strict
        or flexible (see detect_contract_model).

    Raises:
        ModelOnexError: If file cannot be read, parsed, or validated.
            Error codes include:
            - FILE_NOT_FOUND: File does not exist
            - INVALID_INPUT: Path is not a file, unsupported format, etc.
            - VALIDATION_ERROR: YAML/JSON parse error or Pydantic validation failed
            - CONTRACT_VALIDATION_ERROR: Contract-specific validation failed

    Examples:
        >>> contract = load_contract_from_yaml(Path('contracts/my_compute.yaml'))
        >>> type(contract)
        <class 'ModelContractCompute'>
    """
    # Resolve symlinks to get the real path (security: prevent path traversal)
    try:
        resolved_path = file_path.resolve(strict=False)
    except (OSError, RuntimeError) as e:
        raise ModelOnexError(
            message=f"Failed to resolve file path: {e}",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            file_path=str(file_path),
        ) from e

    if not resolved_path.exists():
        raise ModelOnexError(
            message=f"Contract file not found: {file_path}",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            file_path=str(file_path),
        )

    if not resolved_path.is_file():
        raise ModelOnexError(
            message=f"Path is not a file: {file_path}",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            file_path=str(file_path),
        )

    # Security: Check file size before reading content (DoS prevention)
    try:
        file_size = resolved_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ModelOnexError(
                message=f"File too large: {file_size} bytes exceeds {MAX_FILE_SIZE_BYTES} limit (10MB)",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                file_path=str(file_path),
                file_size=file_size,
                max_size=MAX_FILE_SIZE_BYTES,
            )
    except OSError as e:
        raise ModelOnexError(
            message=f"Cannot read file metadata: {e}",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            file_path=str(file_path),
        ) from e

    # Check file extension
    suffix = resolved_path.suffix.lower()
    if suffix not in {".yaml", ".yml", ".json"}:
        raise ModelOnexError(
            message=f"Unsupported file format: {suffix}",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            file_path=str(file_path),
            suffix=suffix,
            supported_formats=[".yaml", ".yml", ".json"],
        )

    try:
        content = resolved_path.read_text(encoding="utf-8")
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

    Convenience function that loads a contract and computes its fingerprint
    in a single call. Uses load_contract_from_yaml and compute_contract_fingerprint.

    Fingerprint Format:
        '<semver>:<12-hex-chars>'
        Example: '1.0.0:abcdef123456'

    Args:
        file_path: Path to the contract file (YAML or JSON).
        verbose: If True, include normalized content in the fingerprint
            result for debugging purposes.

    Returns:
        ModelContractFingerprint containing:
        - version: Contract's semantic version
        - hash_prefix: First 12 chars of SHA256 hash
        - full_hash: Complete SHA256 hash (64 hex chars)
        - computed_at: Timestamp of computation
        - normalized_content: (if verbose) The normalized content used for hashing

    Raises:
        ModelOnexError: If file cannot be loaded or fingerprint computation fails.
            See load_contract_from_yaml for specific error codes.
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

    Checks if the contract has a 'fingerprint' field and compares it
    to the computed fingerprint. Used to detect contract drift.

    Validation Logic:
        1. If contract has no 'fingerprint' field -> valid (new contract)
        2. If fingerprint is not a string -> valid (ignore invalid format)
        3. If fingerprints match exactly -> valid
        4. If fingerprints differ -> invalid (drift detected)

    Fingerprint Format Expected:
        '<semver>:<12-hex-chars>'
        Example: '1.0.0:abcdef123456'

    Args:
        contract: Validated Pydantic contract model. May or may not have
            a 'fingerprint' attribute.
        computed: The freshly computed fingerprint to compare against.

    Returns:
        Tuple of (is_valid, existing_fingerprint_string):
        - is_valid: True if fingerprints match OR no fingerprint declared.
        - existing_fingerprint_string: The existing fingerprint value from
          the contract, or None if not declared.

    Note:
        This function does NOT raise exceptions. Invalid fingerprint formats
        are treated as if no fingerprint was declared (returns True, None).
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

    Generates a multi-line text output suitable for terminal display.
    Includes file path, fingerprint, and optionally detailed information.

    Output Format (normal):
        File: /path/to/contract.yaml
        Fingerprint: 1.0.0:abcdef123456

    Output Format (verbose):
        File: /path/to/contract.yaml
        Fingerprint: 1.0.0:abcdef123456
        Full Hash: abcdef1234567890...
        Version: 1.0.0
        Computed At: 2024-01-15T10:30:00+00:00

    Output Format (with validation):
        File: /path/to/contract.yaml
        Fingerprint: 1.0.0:abcdef123456
        Validation: PASSED (matches existing: 1.0.0:abcdef123456)
        -- or --
        Validation: FAILED
          Expected: 1.0.0:oldvalue123
          Computed: 1.0.0:abcdef123456

    Args:
        file_path: Path to the contract file (for display).
        fingerprint: Computed fingerprint model.
        verbose: If True, include full hash, version, and timestamp.
        validation_result: Optional tuple from validate_existing_fingerprint().
            If provided and existing fingerprint was found, shows validation status.

    Returns:
        Multi-line formatted string for terminal output.
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
    """Format fingerprint result as JSON-serializable dictionary.

    Generates a dictionary suitable for JSON serialization, useful for
    machine processing, CI/CD integration, and API responses.

    Output Structure (normal):
        {
            "file": "/path/to/contract.yaml",
            "fingerprint": "1.0.0:abcdef123456",
            "version": "1.0.0",
            "hash_prefix": "abcdef123456"
        }

    Output Structure (verbose):
        {
            ...normal fields...,
            "full_hash": "abcdef1234567890abcdef1234567890...",
            "computed_at": "2024-01-15T10:30:00+00:00",
            "normalized_content": "..."
        }

    Output Structure (with validation):
        {
            ...normal fields...,
            "validation": {
                "passed": true,
                "existing_fingerprint": "1.0.0:abcdef123456"
            }
        }

    Args:
        file_path: Path to the contract file.
        fingerprint: Computed fingerprint model.
        verbose: If True, include full hash, timestamp, and normalized content.
        validation_result: Optional tuple from validate_existing_fingerprint().

    Returns:
        JSON-serializable dictionary with fingerprint data.
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
    """Process a single contract file and compute its fingerprint.

    Loads a contract, computes fingerprint, optionally validates against
    existing fingerprint, and formats the output.

    Args:
        file_path: Path to the contract file (YAML or JSON).
        verbose: If True, include full hash and normalized content in output.
        validate: If True, validate computed fingerprint against existing
            fingerprint in the contract file.
        json_output: If True, return JSON-serializable dict.
            If False, return formatted text string.

    Returns:
        Tuple of (exit_code, output):
        - exit_code: 0 for success, 1 for validation failure, 2 for error
        - output: Formatted result (dict for JSON, str for text)
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

    Parses command line arguments, processes one or more contract files,
    and outputs fingerprint results in text or JSON format.

    Command-Line Arguments:
        files: One or more contract files to process (required)
        --verbose, -v: Include full hash and normalized content
        --validate: Validate against existing fingerprint in contract
        --json: Output results as JSON for machine processing

    Output Behavior:
        - Single file: Outputs result directly
        - Multiple files: Outputs results separated by blank lines (text)
          or wrapped in {"results": [...]} (JSON)

    Returns:
        Exit code (worst case across all files):
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
