#!/usr/bin/env python3
"""
ONEX Contract Linter with Fingerprint Validation.

A comprehensive contract linting tool that validates ONEX contracts and verifies
fingerprint integrity. This script performs structural validation, ONEX compliance
checks, and fingerprint drift detection.

Features:
    - YAML contract structure validation
    - ONEX naming convention checking
    - Required field verification
    - Fingerprint computation and drift detection
    - Support for baseline fingerprint files

Usage:
    uv run python scripts/lint_contract.py <contract.yaml>
    uv run python scripts/lint_contract.py <contract.yaml> --verbose
    uv run python scripts/lint_contract.py <directory> --recursive
    uv run python scripts/lint_contract.py <contract.yaml> --baseline fingerprints.json
    uv run python scripts/lint_contract.py <contract.yaml> --json
    uv run python scripts/lint_contract.py <contract.yaml> --compute-fingerprint

Exit Codes:
    0 - Contract validation passed, no issues found
    1 - Contract validation failed, issues detected
    2 - Script error (invalid arguments, file not found, etc.)

Related:
    - Linear Ticket: OMN-263
    - Architecture: docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md
    - Fingerprinting: CONTRACT_STABILITY_SPEC.md
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from omnibase_core.contracts import (
    ContractHashRegistry,
    ModelContractFingerprint,
    compute_contract_fingerprint,
)
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class LintSeverity(Enum):
    """Severity levels for lint issues."""

    ERROR = "error"  # Blocks validation
    WARNING = "warning"  # Should be addressed
    INFO = "info"  # Informational


class LintCategory(Enum):
    """Categories of lint issues."""

    SYNTAX = "syntax"  # YAML/JSON syntax errors
    STRUCTURE = "structure"  # Missing/invalid fields
    NAMING = "naming"  # ONEX naming conventions
    FINGERPRINT = "fingerprint"  # Fingerprint validation
    SCHEMA = "schema"  # Pydantic schema validation
    COMPLIANCE = "compliance"  # ONEX compliance issues


@dataclass
class LintIssue:
    """A single lint issue found in a contract."""

    file_path: Path
    line_number: int
    column: int
    category: LintCategory
    severity: LintSeverity
    message: str
    suggestion: str = ""
    code_snippet: str = ""

    def format(self, verbose: bool = False) -> str:
        """Format issue for display.

        Args:
            verbose: If True, include code snippet in output.

        Returns:
            Formatted issue string for display.
        """
        location = f"{self.file_path}:{self.line_number}:{self.column}"
        level = self.severity.value.upper()

        result = f"[{level}] {location}\n"
        result += f"  {self.category.value}: {self.message}\n"
        if self.suggestion:
            result += f"  Suggestion: {self.suggestion}\n"
        if verbose and self.code_snippet:
            result += f"  Code: {self.code_snippet}\n"

        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "file": str(self.file_path),
            "line": self.line_number,
            "column": self.column,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class LintResult:
    """Result of linting a single contract file."""

    file_path: Path
    issues: list[LintIssue] = field(default_factory=list)
    computed_fingerprint: str | None = None
    declared_fingerprint: str | None = None
    contract_type: str | None = None
    is_valid: bool = True
    skip_reason: str | None = None
    parsed_data: dict[str, Any] | None = None  # Cache parsed YAML to avoid re-parsing

    @property
    def error_count(self) -> int:
        """Count of ERROR severity issues."""
        return sum(1 for i in self.issues if i.severity == LintSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of WARNING severity issues."""
        return sum(1 for i in self.issues if i.severity == LintSeverity.WARNING)


# Maximum file size to prevent DoS
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

# Contract type to model class mapping
CONTRACT_MODELS: dict[str, type[Any]] = {
    "effect": ModelContractEffect,
    "compute": ModelContractCompute,
    "reducer": ModelContractReducer,
    "orchestrator": ModelContractOrchestrator,
}


def _detect_contract_type(data: dict[str, Any]) -> str | None:
    """Detect contract type from YAML data using a multi-tier heuristic approach.

    This function attempts to determine the ONEX contract type (effect, compute,
    reducer, orchestrator) from parsed YAML data. It uses a prioritized detection
    strategy to maximize accuracy while maintaining backward compatibility.

    Detection Priority (highest to lowest):
        1. **node_type field** (most reliable): Checks the 'node_type' field value
           against NODE_TYPE_MAPPING. Handles both exact matches (e.g., 'compute_generic')
           and partial matches for backward compatibility (e.g., 'compute' substring).

        2. **name field**: Falls back to checking the contract 'name' field for
           contract type substrings (e.g., 'NodeMyCompute' contains 'compute').

        3. **Type-specific fields**: As a last resort, checks for presence of
           fields that are characteristic of specific contract types:
           - 'algorithm' -> compute
           - 'io_configs' or 'retry_policy' -> effect
           - 'fsm' or 'transitions' -> reducer
           - 'workflow' or 'steps' -> orchestrator

        4. **None**: Returns None if no heuristic matches, indicating the contract
           type cannot be determined. The caller should handle this appropriately.

    Edge Cases:
        - If node_type is present but not in NODE_TYPE_MAPPING, falls through to
          partial match check, then name-based detection, then field-based detection,
          and finally returns None if nothing matches.
        - If node_type is not a string (e.g., int, list), it is treated as if not
          present and detection continues with the name field.
        - Contracts without a 'version' field are still processed; version validation
          is handled by the caller (lint_required_fields).
        - Empty string values for node_type or name are handled gracefully and
          fall through to subsequent detection tiers.

    Tie-Breaker Logic:
        - The first matching heuristic wins (priority order above).
        - For name-based detection, contract types are checked in CONTRACT_MODELS
          iteration order: effect, compute, reducer, orchestrator.
        - For field-based detection, the first matching field pattern wins
          in this order: compute ('algorithm'), effect ('io_configs'/'retry_policy'),
          reducer ('fsm'/'transitions'), orchestrator ('workflow'/'steps').
        - No ambiguity handling: if 'algorithm' and 'workflow' both exist,
          'compute' is returned because 'algorithm' is checked first.

    Implementation Notes:
        - String matching is case-insensitive (converted to lowercase).
        - The NODE_TYPE_MAPPING dict maps EnumNodeType-style values to contract types.
        - This function does NOT validate the contract; it only detects the type.
        - The function is used by lint_fingerprint() to select the appropriate
          Pydantic model class for validation and fingerprint computation.

    Args:
        data: Parsed YAML data as a dictionary. Expected to contain ONEX
            contract fields such as 'node_type', 'name', 'version', etc.
            Must not be None (caller should validate YAML parsing succeeded).

    Returns:
        Contract type string: One of 'effect', 'compute', 'reducer', 'orchestrator'.
        Returns None if the contract type cannot be determined from the data,
        which may indicate an invalid contract, a new/unknown node type, or
        missing required fields. Callers should handle None appropriately
        (e.g., skip fingerprint computation or report a warning).

    Examples:
        >>> _detect_contract_type({'node_type': 'COMPUTE_GENERIC', 'name': 'MyNode'})
        'compute'
        >>> _detect_contract_type({'node_type': 'transformer', 'name': 'DataTransformer'})
        'compute'
        >>> _detect_contract_type({'name': 'NodeMyEffect', 'version': '1.0.0'})
        'effect'
        >>> _detect_contract_type({'fsm': {...}, 'name': 'StateMachine'})
        'reducer'
        >>> _detect_contract_type({'workflow': {...}, 'steps': [...]})
        'orchestrator'
        >>> _detect_contract_type({'unknown_field': 'value'})
        None

    See Also:
        - CONTRACT_MODELS: Maps contract type strings to Pydantic model classes.
        - lint_fingerprint(): Uses this function to select validation model.
        - EnumNodeType: The enum that NODE_TYPE_MAPPING values are derived from.
    """
    # Node types mapped to contract types based on EnumNodeType
    NODE_TYPE_MAPPING: dict[str, str] = {
        # Compute types
        "compute_generic": "compute",
        "transformer": "compute",
        "aggregator": "compute",
        "function": "compute",
        "model": "compute",
        "plugin": "compute",
        "schema": "compute",
        "node": "compute",
        "service": "compute",
        # Effect types
        "effect_generic": "effect",
        "gateway": "effect",
        "validator": "effect",
        "tool": "effect",
        "agent": "effect",
        # Reducer types
        "reducer_generic": "reducer",
        # Orchestrator types
        "orchestrator_generic": "orchestrator",
        "workflow": "orchestrator",
    }

    # Check node_type field (most reliable)
    node_type = data.get("node_type", "")
    if isinstance(node_type, str):
        node_type_lower = node_type.lower()
        # Check exact match first
        if node_type_lower in NODE_TYPE_MAPPING:
            return NODE_TYPE_MAPPING[node_type_lower]
        # Check partial match for backward compatibility
        for contract_type in CONTRACT_MODELS:
            if contract_type in node_type_lower:
                return contract_type

    # Check file naming conventions
    name = data.get("name", "")
    if isinstance(name, str):
        name_lower = name.lower()
        for contract_type in CONTRACT_MODELS:
            if contract_type in name_lower:
                return contract_type

    # Default to compute if type-specific fields suggest it
    if "algorithm" in data:
        return "compute"
    if "io_configs" in data or "retry_policy" in data:
        return "effect"
    if "fsm" in data or "transitions" in data:
        return "reducer"
    if "workflow" in data or "steps" in data:
        return "orchestrator"

    # Unknown contract type: no heuristic matched. This can happen with:
    # - New/custom node types not yet in NODE_TYPE_MAPPING
    # - Contracts missing node_type and name fields
    # - Contracts with non-standard field structures
    # Callers should handle None appropriately (e.g., skip fingerprint computation).
    return None


def lint_yaml_syntax(
    file_path: Path, content: str
) -> tuple[dict[str, Any] | None, list[LintIssue]]:
    """Validate YAML syntax and parse content into a dictionary.

    Parses the raw YAML content using yaml.safe_load() and validates that
    the result is a non-empty dictionary suitable for contract processing.

    Validation Checks:
        - YAML syntax is valid (no parse errors)
        - Content is not empty (None after parsing)
        - Parsed result is a dictionary (mapping type)

    Args:
        file_path: Path to the contract file. Used for error reporting
            in LintIssue objects but not for file I/O.
        content: Raw file content as a string. Should be UTF-8 encoded
            YAML content. The caller is responsible for reading the file.

    Returns:
        Tuple of (parsed_data, issues) where:
        - parsed_data: Dictionary containing parsed YAML data, or None if
          parsing failed or content was invalid.
        - issues: List of LintIssue objects describing any problems found.
          May be empty if parsing succeeded with no issues.

    Note:
        This function does NOT raise exceptions. All errors are captured
        as LintIssue objects with LintSeverity.ERROR and returned in the
        issues list. The caller should check if parsed_data is None to
        determine if parsing succeeded.

    Examples:
        >>> data, issues = lint_yaml_syntax(Path('test.yaml'), 'name: test')
        >>> data
        {'name': 'test'}
        >>> issues
        []

        >>> data, issues = lint_yaml_syntax(Path('test.yaml'), '')
        >>> data is None
        True
        >>> len(issues)
        1
    """
    issues: list[LintIssue] = []

    try:
        data = yaml.safe_load(content)
        if data is None:
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.SYNTAX,
                    severity=LintSeverity.ERROR,
                    message="Empty YAML content",
                    suggestion="Add contract definition to the file",
                )
            )
            return None, issues

        if not isinstance(data, dict):
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.SYNTAX,
                    severity=LintSeverity.ERROR,
                    message=f"Expected YAML dict, got {type(data).__name__}",
                    suggestion="Contract must be a YAML mapping/dict",
                )
            )
            return None, issues

        return data, issues

    except yaml.YAMLError as e:
        line = getattr(e, "problem_mark", None)
        line_num = line.line + 1 if line else 1
        col = line.column + 1 if line else 1

        issues.append(
            LintIssue(
                file_path=file_path,
                line_number=line_num,
                column=col,
                category=LintCategory.SYNTAX,
                severity=LintSeverity.ERROR,
                message=f"YAML syntax error: {e}",
                suggestion="Fix the YAML syntax error",
            )
        )
        return None, issues


def lint_required_fields(file_path: Path, data: dict[str, Any]) -> list[LintIssue]:
    """Check for required contract fields defined by ModelContractBase.

    Validates that the contract contains all required fields for ONEX contracts
    and that those fields have non-empty values. Also checks for recommended
    fields like 'description'.

    Required Fields (ERROR if missing or empty):
        - name: Contract identifier
        - version: Semantic version string (e.g., '1.0.0')
        - node_type: ONEX node type (e.g., COMPUTE_GENERIC)
        - input_model: Input Pydantic model class name
        - output_model: Output Pydantic model class name

    Recommended Fields (WARNING if missing):
        - description: Human-readable contract description

    Args:
        file_path: Path to the contract file. Used for error reporting
            in LintIssue objects.
        data: Parsed YAML data as a dictionary. Should be the result of
            lint_yaml_syntax() or yaml.safe_load().

    Returns:
        List of LintIssue objects for any missing or empty required fields.
        Returns an empty list if all required fields are present and valid.
        Issues have severity ERROR for required fields, WARNING for recommended.
    """
    issues: list[LintIssue] = []

    # Fields required by ModelContractBase
    required_fields = ["name", "version", "node_type", "input_model", "output_model"]

    for field_name in required_fields:
        if field_name not in data:
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.STRUCTURE,
                    severity=LintSeverity.ERROR,
                    message=f"Missing required field: {field_name}",
                    suggestion=f"Add '{field_name}' field to the contract",
                )
            )
        elif data[field_name] is None or data[field_name] == "":
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.STRUCTURE,
                    severity=LintSeverity.ERROR,
                    message=f"Empty required field: {field_name}",
                    suggestion=f"Provide a value for '{field_name}'",
                )
            )

    # Check description (recommended but not required)
    if "description" not in data or not data.get("description"):
        issues.append(
            LintIssue(
                file_path=file_path,
                line_number=1,
                column=1,
                category=LintCategory.COMPLIANCE,
                severity=LintSeverity.WARNING,
                message="Missing description field",
                suggestion="Add a meaningful description to the contract",
            )
        )

    return issues


def lint_naming_conventions(file_path: Path, data: dict[str, Any]) -> list[LintIssue]:
    """Check ONEX naming conventions for contract and model names.

    Validates that names follow ONEX project conventions:
    - Contract names should be PascalCase or snake_case
    - Model class names should start with 'Model' prefix

    Naming Rules Checked (WARNING severity):
        1. **Contract name**: Should start with uppercase (PascalCase) or
           contain underscore (snake_case). Examples: 'NodeMyCompute',
           'node_my_compute'.

        2. **input_model**: Class name should start with 'Model' prefix.
           Example: 'ModelComputeInput', not 'ComputeInput'.

        3. **output_model**: Class name should start with 'Model' prefix.
           Example: 'ModelComputeOutput', not 'ComputeOutput'.

    For fully-qualified model names (e.g., 'mypackage.models.ModelInput'),
    only the final class name component is checked.

    Args:
        file_path: Path to the contract file. Used for error reporting.
        data: Parsed YAML data as a dictionary.

    Returns:
        List of LintIssue objects for naming convention violations.
        All issues have WARNING severity (not blocking errors).
        Returns an empty list if all names follow conventions.
    """
    issues: list[LintIssue] = []

    # Check contract name follows convention
    name = data.get("name", "")
    if name:
        # Contract names should be PascalCase or snake_case for nodes
        if not (name[0].isupper() or "_" in name):  # PascalCase  # snake_case
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.NAMING,
                    severity=LintSeverity.WARNING,
                    message=f"Contract name '{name}' does not follow ONEX naming conventions",
                    suggestion="Use PascalCase (NodeMyCompute) or snake_case (node_my_compute)",
                )
            )

    # Check model names follow Model* convention
    input_model = data.get("input_model", "")
    if input_model and isinstance(input_model, str):
        model_class = input_model.split(".")[-1] if "." in input_model else input_model
        if not model_class.startswith("Model"):
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.NAMING,
                    severity=LintSeverity.WARNING,
                    message=f"Input model '{model_class}' should follow Model* naming convention",
                    suggestion="Rename to start with 'Model' (e.g., ModelMyInput)",
                )
            )

    output_model = data.get("output_model", "")
    if output_model and isinstance(output_model, str):
        model_class = (
            output_model.split(".")[-1] if "." in output_model else output_model
        )
        if not model_class.startswith("Model"):
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.NAMING,
                    severity=LintSeverity.WARNING,
                    message=f"Output model '{model_class}' should follow Model* naming convention",
                    suggestion="Rename to start with 'Model' (e.g., ModelMyOutput)",
                )
            )

    return issues


def lint_fingerprint(
    file_path: Path,
    data: dict[str, Any],
    registry: ContractHashRegistry | None,
    validated_model: Any | None = None,
) -> tuple[list[LintIssue], str | None, str | None, Any | None]:
    """Validate contract fingerprint and detect drift from baseline.

    This is the core fingerprint validation logic for OMN-263. It computes
    the fingerprint from contract content and compares it against:
    1. The declared fingerprint in the contract file (if present)
    2. The baseline fingerprint in the registry (if provided)

    Fingerprint Format:
        '<semver>:<12-hex-chars>'
        Example: '1.0.0:abcdef123456'

        The format consists of:
        - semver: The contract's semantic version (e.g., '1.0.0', '0.4.0')
        - 12-hex-chars: First 12 characters of the SHA256 hash of normalized content

    Validation Process:
        1. Extract declared fingerprint from contract (if present)
        2. Detect contract type using _detect_contract_type()
        3. Validate contract against appropriate Pydantic model
        4. Compute fingerprint from validated model
        5. Compare declared vs computed (ERROR if mismatch)
        6. Compare computed vs baseline registry (ERROR if drift detected)

    Args:
        file_path: Path to the contract file. Used for error reporting.
        data: Parsed YAML data as a dictionary.
        registry: Optional ContractHashRegistry with baseline fingerprints
            for drift detection. If None, baseline comparison is skipped.
        validated_model: Optional pre-validated Pydantic model to avoid
            re-validation. If provided, skips model_validate() call for
            better performance. Useful when the caller has already validated.

    Returns:
        Tuple of (issues, computed_fingerprint, declared_fingerprint, validated_model):
        - issues: List of LintIssue objects for any fingerprint problems.
        - computed_fingerprint: String representation of computed fingerprint,
          or None if computation failed (e.g., schema validation error).
        - declared_fingerprint: String from contract's 'fingerprint' field,
          or None if not declared.
        - validated_model: The validated Pydantic model instance, returned
          for caching/reuse by the caller.

    Note:
        If contract type cannot be detected or is not in CONTRACT_MODELS,
        fingerprint computation is skipped and computed_fingerprint will be None.
        This is not treated as an error - the caller decides how to handle it.
    """
    issues: list[LintIssue] = []
    computed_fp: str | None = None
    declared_fp: str | None = None
    contract_model: Any | None = validated_model

    # Get declared fingerprint from contract
    declared_fp = data.get("fingerprint")
    if declared_fp and not isinstance(declared_fp, str):
        issues.append(
            LintIssue(
                file_path=file_path,
                line_number=1,
                column=1,
                category=LintCategory.FINGERPRINT,
                severity=LintSeverity.ERROR,
                message=f"Fingerprint must be a string, got {type(declared_fp).__name__}",
                suggestion="Use format '<version>:<hash>' (e.g., '1.0.0:abcdef123456')",
            )
        )
        declared_fp = None

    # Try to compute fingerprint by validating against Pydantic model
    contract_type = _detect_contract_type(data)
    if contract_type and contract_type in CONTRACT_MODELS:
        model_class = CONTRACT_MODELS[contract_type]
        try:
            # Use pre-validated model if available, otherwise validate now
            if contract_model is None:
                contract_model = model_class.model_validate(data)

            # Compute fingerprint
            fingerprint = compute_contract_fingerprint(contract_model)
            computed_fp = str(fingerprint)

            # Compare declared vs computed if both exist
            if declared_fp:
                try:
                    declared_parsed = ModelContractFingerprint.from_string(declared_fp)
                    if not fingerprint.matches(declared_parsed):
                        issues.append(
                            LintIssue(
                                file_path=file_path,
                                line_number=1,
                                column=1,
                                category=LintCategory.FINGERPRINT,
                                severity=LintSeverity.ERROR,
                                message=(
                                    f"Fingerprint mismatch: declared '{declared_fp}' "
                                    f"does not match computed '{computed_fp}'"
                                ),
                                suggestion=(
                                    f"Update fingerprint to '{computed_fp}' or verify "
                                    "contract content matches expected"
                                ),
                            )
                        )
                except ModelOnexError as e:
                    issues.append(
                        LintIssue(
                            file_path=file_path,
                            line_number=1,
                            column=1,
                            category=LintCategory.FINGERPRINT,
                            severity=LintSeverity.ERROR,
                            message=f"Invalid declared fingerprint format: {e.message}",
                            suggestion="Use format '<version>:<hash>' (e.g., '1.0.0:abcdef123456')",
                        )
                    )

            # Check against registry baseline if provided
            if registry:
                contract_name = data.get("name", "")
                if contract_name:
                    drift_result = registry.detect_drift(contract_name, fingerprint)
                    if drift_result.has_drift:
                        if drift_result.drift_type == "not_registered":
                            issues.append(
                                LintIssue(
                                    file_path=file_path,
                                    line_number=1,
                                    column=1,
                                    category=LintCategory.FINGERPRINT,
                                    severity=LintSeverity.INFO,
                                    message=f"Contract '{contract_name}' not found in baseline registry",
                                    suggestion="Add to baseline with --update-baseline if this is expected",
                                )
                            )
                        else:
                            expected = (
                                str(drift_result.expected_fingerprint)
                                if drift_result.expected_fingerprint
                                else "unknown"
                            )
                            issues.append(
                                LintIssue(
                                    file_path=file_path,
                                    line_number=1,
                                    column=1,
                                    category=LintCategory.FINGERPRINT,
                                    severity=LintSeverity.ERROR,
                                    message=(
                                        f"Contract '{contract_name}' has drifted from baseline. "
                                        f"Drift type: {drift_result.drift_type}. "
                                        f"Expected: {expected}, "
                                        f"Computed: {computed_fp}"
                                    ),
                                    suggestion=(
                                        "Update baseline with --update-baseline if drift is intentional, "
                                        "or revert contract changes"
                                    ),
                                )
                            )

        except ValidationError as e:
            # Pydantic schema validation failed - provide detailed error information
            error_details = []
            for error in e.errors():
                loc = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_details.append(f"  - {loc}: {msg}")
            error_list = "\n".join(error_details[:5])  # Limit to first 5 errors
            if len(e.errors()) > 5:
                error_list += f"\n  ... and {len(e.errors()) - 5} more errors"

            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.SCHEMA,
                    severity=LintSeverity.ERROR,
                    message=f"Contract schema validation failed ({len(e.errors())} errors):\n{error_list}",
                    suggestion="Fix the schema errors listed above to enable fingerprint computation",
                )
            )
            contract_model = None

        except (TypeError, ModelOnexError) as e:
            # Other validation errors - can't compute fingerprint
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.SCHEMA,
                    severity=LintSeverity.ERROR,
                    message=f"Contract validation failed: {e}",
                    suggestion="Fix schema errors to enable fingerprint computation",
                )
            )
            contract_model = None

    return issues, computed_fp, declared_fp, contract_model


def lint_contract_file(
    file_path: Path,
    registry: ContractHashRegistry | None = None,
    compute_fingerprint_only: bool = False,
) -> LintResult:
    """Lint a single contract file with all validation checks.

    This is the main entry point for linting a single contract. It performs
    all validation checks in sequence and aggregates results into a LintResult.

    Validation Sequence:
        1. File existence and accessibility check
        2. File size check (max 10MB to prevent DoS)
        3. UTF-8 encoding validation
        4. YAML syntax validation (lint_yaml_syntax)
        5. Contract type detection (_detect_contract_type)
        6. Required fields check (lint_required_fields) - unless fingerprint_only
        7. Naming conventions check (lint_naming_conventions) - unless fingerprint_only
        8. Fingerprint validation (lint_fingerprint)

    Args:
        file_path: Path to the contract YAML file. Must be an existing file
            with .yaml or .yml extension.
        registry: Optional ContractHashRegistry with baseline fingerprints
            for drift detection. If None, baseline comparison is skipped.
        compute_fingerprint_only: If True, only runs YAML parsing and
            fingerprint computation, skipping structural and naming checks.
            Useful for quick fingerprint verification.

    Returns:
        LintResult containing:
        - file_path: The input file path
        - issues: List of all LintIssue objects found
        - computed_fingerprint: Computed fingerprint string or None
        - declared_fingerprint: Declared fingerprint from contract or None
        - contract_type: Detected contract type ('compute', 'effect', etc.) or None
        - is_valid: True if no ERROR severity issues were found
        - parsed_data: Cached parsed YAML data for reuse

    Note:
        The function returns early with is_valid=False on critical errors
        like file not found, encoding errors, or YAML syntax errors.
    """
    result = LintResult(file_path=file_path)

    # Check file existence and size
    if not file_path.exists():
        result.issues.append(
            LintIssue(
                file_path=file_path,
                line_number=0,
                column=0,
                category=LintCategory.SYNTAX,
                severity=LintSeverity.ERROR,
                message="File not found",
                suggestion="Check the file path",
            )
        )
        result.is_valid = False
        return result

    try:
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            result.issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=0,
                    column=0,
                    category=LintCategory.SYNTAX,
                    severity=LintSeverity.ERROR,
                    message=f"File too large: {file_size} bytes exceeds {MAX_FILE_SIZE_BYTES} limit",
                    suggestion="Split contract or reduce content size",
                )
            )
            result.is_valid = False
            return result
    except OSError as e:
        result.issues.append(
            LintIssue(
                file_path=file_path,
                line_number=0,
                column=0,
                category=LintCategory.SYNTAX,
                severity=LintSeverity.ERROR,
                message=f"Cannot read file: {e}",
                suggestion="Check file permissions",
            )
        )
        result.is_valid = False
        return result

    # Read file content
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        result.issues.append(
            LintIssue(
                file_path=file_path,
                line_number=0,
                column=0,
                category=LintCategory.SYNTAX,
                severity=LintSeverity.ERROR,
                message=f"Encoding error: {e}",
                suggestion="Ensure file is UTF-8 encoded",
            )
        )
        result.is_valid = False
        return result

    # Parse YAML
    data, syntax_issues = lint_yaml_syntax(file_path, content)
    result.issues.extend(syntax_issues)

    if data is None:
        result.is_valid = False
        return result

    # Store parsed data to avoid re-parsing during baseline update
    result.parsed_data = data

    # Detect contract type
    result.contract_type = _detect_contract_type(data)

    if compute_fingerprint_only:
        # Only compute fingerprint
        fp_issues, computed_fp, declared_fp, _ = lint_fingerprint(file_path, data, None)
        result.issues.extend(fp_issues)
        result.computed_fingerprint = computed_fp
        result.declared_fingerprint = declared_fp
        result.is_valid = result.error_count == 0
        return result

    # Run all lint checks
    result.issues.extend(lint_required_fields(file_path, data))
    result.issues.extend(lint_naming_conventions(file_path, data))

    fp_issues, computed_fp, declared_fp, _ = lint_fingerprint(file_path, data, registry)
    result.issues.extend(fp_issues)
    result.computed_fingerprint = computed_fp
    result.declared_fingerprint = declared_fp

    result.is_valid = result.error_count == 0
    return result


def find_contract_files(directory: Path, recursive: bool = False) -> list[Path]:
    """Find all YAML contract files in a directory.

    Searches for .yaml and .yml files, excluding common non-contract
    directories like __pycache__, .git, node_modules, and .venv.

    Args:
        directory: Directory path to search. Must be an existing directory.
        recursive: If True, searches subdirectories recursively using rglob.
            If False, only searches the immediate directory using glob.

    Returns:
        Sorted list of Path objects for contract files found.
        Returns an empty list if no YAML files are found or if
        all files are in excluded directories.

    Note:
        Files are filtered by checking if any path component matches
        the excluded directories set. This ensures precise matching
        (e.g., 'my__pycache__dir' would NOT be excluded).
    """
    patterns = ["*.yaml", "*.yml"]
    files: list[Path] = []

    for pattern in patterns:
        if recursive:
            files.extend(directory.rglob(pattern))
        else:
            files.extend(directory.glob(pattern))

    # Filter out likely non-contract files using Path.parts for precise matching
    excluded_dirs = {"__pycache__", ".git", "node_modules", ".venv"}
    contract_files = [
        f for f in files if not any(part in excluded_dirs for part in f.parts)
    ]

    return sorted(contract_files)


def load_baseline_registry(baseline_path: Path) -> ContractHashRegistry:
    """Load baseline fingerprints from JSON file.

    Reads and parses a JSON file containing baseline fingerprints for
    drift detection. If the file does not exist, returns an empty registry.

    Args:
        baseline_path: Path to the baseline JSON file. The file should
            contain a JSON object compatible with ContractHashRegistry.from_dict().

    Returns:
        ContractHashRegistry populated with baseline fingerprints.
        Returns an empty registry if the file does not exist.

    Raises:
        json.JSONDecodeError: If the file contains invalid JSON.
        OSError: If the file exists but cannot be read.
    """
    if not baseline_path.exists():
        return ContractHashRegistry()

    content = baseline_path.read_text(encoding="utf-8")
    data = json.loads(content)

    return ContractHashRegistry.from_dict(data)


def save_baseline_registry(registry: ContractHashRegistry, baseline_path: Path) -> None:
    """Save baseline fingerprints to JSON file.

    Serializes the registry to a formatted JSON file with sorted keys
    for consistent, diff-friendly output.

    Args:
        registry: ContractHashRegistry with fingerprints to save.
        baseline_path: Path to the output JSON file. Parent directories
            must exist. Will overwrite existing file.

    Raises:
        OSError: If the file cannot be written (permissions, disk space, etc.).
    """
    data = registry.to_dict()
    content = json.dumps(data, indent=2, sort_keys=True)
    baseline_path.write_text(content, encoding="utf-8")


def main() -> int:
    """Main entry point for the contract linter CLI.

    Parses command-line arguments, processes contract files, and outputs
    results in text or JSON format. Supports recursive directory scanning,
    baseline registry management, and various output modes.

    Command-Line Arguments:
        paths: Contract files or directories to lint (required)
        --recursive, -r: Search directories recursively
        --verbose, -v: Include code snippets in output
        --json: Output results as JSON
        --baseline: Path to baseline fingerprints JSON file
        --update-baseline: Update baseline with computed fingerprints
        --compute-fingerprint: Only compute fingerprints (skip other checks)
        --errors-only: Only report ERROR severity issues

    Returns:
        Exit code:
        - 0: Linting passed (no ERROR severity issues)
        - 1: Linting failed (ERROR severity issues found)
        - 2: Script error (invalid arguments, file not found, etc.)
    """
    parser = argparse.ArgumentParser(
        description="ONEX Contract Linter with Fingerprint Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/lint_contract.py contract.yaml
  uv run python scripts/lint_contract.py contracts/ --recursive
  uv run python scripts/lint_contract.py contract.yaml --baseline fingerprints.json
  uv run python scripts/lint_contract.py contract.yaml --compute-fingerprint
  uv run python scripts/lint_contract.py contract.yaml --json
        """,
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Contract files or directories to lint",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively search directories for contract files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with code snippets",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Path to baseline fingerprints JSON file",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline file with computed fingerprints",
    )
    parser.add_argument(
        "--compute-fingerprint",
        action="store_true",
        help="Only compute and display fingerprints (skip other checks)",
    )
    parser.add_argument(
        "--errors-only",
        action="store_true",
        help="Only report ERROR severity issues",
    )

    args = parser.parse_args()

    # Collect all files to lint
    files_to_lint: list[Path] = []
    for path in args.paths:
        if path.is_file():
            files_to_lint.append(path)
        elif path.is_dir():
            files_to_lint.extend(find_contract_files(path, args.recursive))
        else:
            if args.json:
                print(json.dumps({"error": f"Path not found: {path}"}))
            else:
                print(f"Error: Path not found: {path}", file=sys.stderr)
            return 2

    if not files_to_lint:
        if args.json:
            print(json.dumps({"error": "No contract files found"}))
        else:
            print("No contract files found", file=sys.stderr)
        return 2

    # Load baseline registry if specified
    registry: ContractHashRegistry | None = None
    if args.baseline:
        try:
            registry = load_baseline_registry(args.baseline)
        except Exception as e:
            if args.json:
                print(json.dumps({"error": f"Failed to load baseline: {e}"}))
            else:
                print(f"Error loading baseline: {e}", file=sys.stderr)
            return 2

    # Lint all files
    results: list[LintResult] = []
    for file_path in files_to_lint:
        result = lint_contract_file(
            file_path,
            registry=registry,
            compute_fingerprint_only=args.compute_fingerprint,
        )
        results.append(result)

    # Update baseline if requested
    if args.update_baseline and args.baseline:
        if registry is None:
            registry = ContractHashRegistry()

        for result in results:
            if result.computed_fingerprint:
                # Use cached parsed_data to avoid re-parsing YAML
                if result.parsed_data is not None:
                    contract_name = result.parsed_data.get(
                        "name", result.file_path.stem
                    )
                    registry.register(contract_name, result.computed_fingerprint)
                else:
                    # Fallback: parsed_data not available (shouldn't happen normally)
                    print(
                        f"Warning: Skipped {result.file_path} during baseline update: "
                        "parsed data not available (file may have had syntax errors)",
                        file=sys.stderr,
                    )

        try:
            save_baseline_registry(registry, args.baseline)
            if not args.json:
                print(f"Updated baseline: {args.baseline}")
        except Exception as e:
            if args.json:
                print(json.dumps({"error": f"Failed to save baseline: {e}"}))
            else:
                print(f"Error saving baseline: {e}", file=sys.stderr)
            return 2

    # Calculate summary
    total_files = len(results)
    passed_files = sum(1 for r in results if r.is_valid)
    failed_files = total_files - passed_files
    total_errors = sum(r.error_count for r in results)
    total_warnings = sum(r.warning_count for r in results)

    # Output results
    if args.json:
        output: dict[str, Any] = {
            "summary": {
                "total_files": total_files,
                "passed_files": passed_files,
                "failed_files": failed_files,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            "results": [],
        }

        for result in results:
            issues = result.issues
            if args.errors_only:
                issues = [i for i in issues if i.severity == LintSeverity.ERROR]

            result_dict: dict[str, Any] = {
                "file": str(result.file_path),
                "is_valid": result.is_valid,
                "contract_type": result.contract_type,
                "computed_fingerprint": result.computed_fingerprint,
                "declared_fingerprint": result.declared_fingerprint,
                "issues": [i.to_dict() for i in issues],
            }
            output["results"].append(result_dict)

        print(json.dumps(output, indent=2))
        return 0 if failed_files == 0 else 1

    # Text output
    if not args.compute_fingerprint:
        if args.verbose:
            print(f"Linting {total_files} contract files...")
            print()

    for result in results:
        if args.compute_fingerprint:
            # Simple fingerprint output
            if result.computed_fingerprint:
                print(f"{result.file_path}: {result.computed_fingerprint}")
            else:
                print(f"{result.file_path}: <unable to compute>")
            continue

        issues = result.issues
        if args.errors_only:
            issues = [i for i in issues if i.severity == LintSeverity.ERROR]

        if issues:
            for issue in issues:
                print(issue.format(args.verbose))

    if args.compute_fingerprint:
        return 0

    # Summary
    print()
    print("=" * 60)
    print("Contract Linter Summary")
    print("=" * 60)
    print(f"  Total files: {total_files}")
    print(f"  Passed: {passed_files}")
    print(f"  Failed: {failed_files}")
    print(f"  Errors: {total_errors}")
    print(f"  Warnings: {total_warnings}")

    if failed_files > 0:
        print()
        print("FAILED: Contract linting detected issues")
        return 1

    print()
    print("PASSED: Contract linting successful")
    return 0


if __name__ == "__main__":
    sys.exit(main())
