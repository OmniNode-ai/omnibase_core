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
    poetry run python scripts/lint_contract.py <contract.yaml>
    poetry run python scripts/lint_contract.py <contract.yaml> --verbose
    poetry run python scripts/lint_contract.py <directory> --recursive
    poetry run python scripts/lint_contract.py <contract.yaml> --baseline fingerprints.json
    poetry run python scripts/lint_contract.py <contract.yaml> --json
    poetry run python scripts/lint_contract.py <contract.yaml> --compute-fingerprint

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
from typing import Any, Literal

import yaml

from omnibase_core.contracts import (
    ContractHashRegistry,
    ModelContractFingerprint,
    compute_contract_fingerprint,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
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
    """Detect contract type from YAML data.

    Args:
        data: Parsed YAML data.

    Returns:
        Contract type string ('effect', 'compute', 'reducer', 'orchestrator')
        or None if not determinable.
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
        "tool": "effect",
        "agent": "effect",
        # Reducer types
        "reducer_generic": "reducer",
        # Orchestrator types
        "orchestrator_generic": "orchestrator",
        "gateway": "orchestrator",
        "validator": "orchestrator",
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

    return None


def lint_yaml_syntax(
    file_path: Path, content: str
) -> tuple[dict[str, Any] | None, list[LintIssue]]:
    """Validate YAML syntax and parse content.

    Args:
        file_path: Path to the contract file.
        content: Raw file content.

    Returns:
        Tuple of (parsed_data, issues). parsed_data is None if syntax error.
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
    """Check for required contract fields.

    Args:
        file_path: Path to the contract file.
        data: Parsed YAML data.

    Returns:
        List of lint issues for missing required fields.
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
    """Check ONEX naming conventions.

    Args:
        file_path: Path to the contract file.
        data: Parsed YAML data.

    Returns:
        List of naming convention issues.
    """
    issues: list[LintIssue] = []

    # Check contract name follows convention
    name = data.get("name", "")
    if name:
        # Contract names should be PascalCase or snake_case for nodes
        if not (
            name[0].isupper()  # PascalCase
            or "_" in name  # snake_case
        ):
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
) -> tuple[list[LintIssue], str | None, str | None]:
    """Validate contract fingerprint.

    This is the core fingerprint validation logic for OMN-263.

    Args:
        file_path: Path to the contract file.
        data: Parsed YAML data.
        registry: Optional registry with baseline fingerprints.

    Returns:
        Tuple of (issues, computed_fingerprint, declared_fingerprint).
    """
    issues: list[LintIssue] = []
    computed_fp: str | None = None
    declared_fp: str | None = None

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
            # Validate and create contract model
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

        except Exception as e:
            # Schema validation failed - can't compute fingerprint
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=1,
                    column=1,
                    category=LintCategory.SCHEMA,
                    severity=LintSeverity.ERROR,
                    message=f"Contract schema validation failed: {e}",
                    suggestion="Fix schema errors to enable fingerprint computation",
                )
            )

    return issues, computed_fp, declared_fp


def lint_contract_file(
    file_path: Path,
    registry: ContractHashRegistry | None = None,
    compute_fingerprint_only: bool = False,
) -> LintResult:
    """Lint a single contract file.

    Args:
        file_path: Path to the contract YAML file.
        registry: Optional baseline fingerprint registry.
        compute_fingerprint_only: If True, only compute and report fingerprint.

    Returns:
        LintResult with all issues found.
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

    # Detect contract type
    result.contract_type = _detect_contract_type(data)

    if compute_fingerprint_only:
        # Only compute fingerprint
        fp_issues, computed_fp, declared_fp = lint_fingerprint(file_path, data, None)
        result.issues.extend(fp_issues)
        result.computed_fingerprint = computed_fp
        result.declared_fingerprint = declared_fp
        result.is_valid = result.error_count == 0
        return result

    # Run all lint checks
    result.issues.extend(lint_required_fields(file_path, data))
    result.issues.extend(lint_naming_conventions(file_path, data))

    fp_issues, computed_fp, declared_fp = lint_fingerprint(file_path, data, registry)
    result.issues.extend(fp_issues)
    result.computed_fingerprint = computed_fp
    result.declared_fingerprint = declared_fp

    result.is_valid = result.error_count == 0
    return result


def find_contract_files(directory: Path, recursive: bool = False) -> list[Path]:
    """Find all YAML contract files in a directory.

    Args:
        directory: Directory to search.
        recursive: If True, search recursively.

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

    # Filter out likely non-contract files
    contract_files = [
        f
        for f in files
        if not any(
            part in str(f) for part in ["__pycache__", ".git", "node_modules", ".venv"]
        )
    ]

    return sorted(contract_files)


def load_baseline_registry(baseline_path: Path) -> ContractHashRegistry:
    """Load baseline fingerprints from JSON file.

    Args:
        baseline_path: Path to baseline JSON file.

    Returns:
        Registry populated with baseline fingerprints.
    """
    if not baseline_path.exists():
        return ContractHashRegistry()

    content = baseline_path.read_text(encoding="utf-8")
    data = json.loads(content)

    return ContractHashRegistry.from_dict(data)


def save_baseline_registry(registry: ContractHashRegistry, baseline_path: Path) -> None:
    """Save baseline fingerprints to JSON file.

    Args:
        registry: Registry with fingerprints to save.
        baseline_path: Path to baseline JSON file.
    """
    data = registry.to_dict()
    content = json.dumps(data, indent=2, sort_keys=True)
    baseline_path.write_text(content, encoding="utf-8")


def main() -> int:
    """Main entry point for the contract linter.

    Returns:
        Exit code:
        - 0: Linting passed
        - 1: Linting failed (issues found)
        - 2: Script error
    """
    parser = argparse.ArgumentParser(
        description="ONEX Contract Linter with Fingerprint Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  poetry run python scripts/lint_contract.py contract.yaml
  poetry run python scripts/lint_contract.py contracts/ --recursive
  poetry run python scripts/lint_contract.py contract.yaml --baseline fingerprints.json
  poetry run python scripts/lint_contract.py contract.yaml --compute-fingerprint
  poetry run python scripts/lint_contract.py contract.yaml --json
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
                # Get contract name from file
                try:
                    content = result.file_path.read_text(encoding="utf-8")
                    data = yaml.safe_load(content)
                    contract_name = data.get("name", result.file_path.stem)
                    registry.register(contract_name, result.computed_fingerprint)
                except Exception:
                    pass  # Skip files that can't be parsed

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
