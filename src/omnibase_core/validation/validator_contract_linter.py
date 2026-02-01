"""
ValidatorContractLinter - Contract-driven YAML contract file validator.

This module provides the ValidatorContractLinter class for validating ONEX
contract YAML files for compliance with ONEX standards.

The validator checks:
- YAML syntax validity
- Deprecated field names (e.g., 'version' should be 'contract_version')
- Required fields (name, contract_version, node_type)
- Recommended fields (description)
- Naming conventions (PascalCase/snake_case, Model prefix)
- Fingerprint format (semver:12-hex)
- Fingerprint match (declared vs computed)
- Pydantic schema validation

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorContractLinter

        validator = ValidatorContractLinter()
        result = validator.validate(Path("contracts/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_contract_linter contracts/

Thread Safety:
    ValidatorContractLinter instances are NOT thread-safe. Create separate
    instances for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - ModelValidatorSubcontract: Contract model for validator configuration
    - scripts/lint_contract.py: Original standalone linting script
"""

import logging
import re
import sys
from pathlib import Path
from typing import ClassVar

import yaml

# Configure logger for this module
logger = logging.getLogger(__name__)

from pydantic import ValidationError

from omnibase_core.contracts import (
    ContractHashRegistry,
    ModelContractFingerprint,
    compute_contract_fingerprint,
)
from omnibase_core.enums import EnumSeverity
from omnibase_core.errors.exception_groups import FILE_IO_ERRORS, VALIDATION_ERRORS
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_base import ValidatorBase

# Rule IDs for contract linting violations
RULE_YAML_SYNTAX = "yaml_syntax"
RULE_REQUIRED_FIELDS = "required_fields"
RULE_RECOMMENDED_FIELDS = "recommended_fields"
RULE_NAMING_CONVENTION = "naming_convention"
RULE_MODEL_PREFIX = "model_prefix"
RULE_FINGERPRINT_FORMAT = "fingerprint_format"
RULE_FINGERPRINT_MATCH = "fingerprint_match"
RULE_SCHEMA_VALIDATION = "schema_validation"
RULE_DEPRECATED_FIELD_NAMES = "deprecated_field_names"

# Contract type to model class mapping
CONTRACT_MODELS: dict[
    str,
    type[
        ModelContractCompute
        | ModelContractEffect
        | ModelContractReducer
        | ModelContractOrchestrator
    ],
] = {
    "effect": ModelContractEffect,
    "compute": ModelContractCompute,
    "reducer": ModelContractReducer,
    "orchestrator": ModelContractOrchestrator,
}

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

# Fingerprint format regex: semver:12-hex
FINGERPRINT_PATTERN = re.compile(r"^\d+\.\d+\.\d+:[a-fA-F0-9]{12}$")

# Naming convention patterns for stricter validation
# PascalCase: Must start with uppercase, at least 2 characters (e.g., "Ab", "NodeCompute")
# Single uppercase letters like "A" are NOT considered valid PascalCase
PASCAL_CASE_PATTERN = re.compile(r"^[A-Z][a-zA-Z0-9]+$")

# snake_case: Must start with lowercase, can contain underscores between segments
# Underscores must be followed by at least one alphanumeric character (no trailing underscores)
# Examples: "a", "node_compute", "my_node_123" are valid; "a_", "_foo" are invalid
SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


def _detect_contract_type(data: dict[str, object]) -> str | None:
    """Detect contract type from YAML data using heuristics.

    Detection Priority (highest to lowest):
        1. node_type field (most reliable)
        2. name field for contract type substrings
        3. Type-specific fields (algorithm, fsm, workflow)

    Args:
        data: Parsed YAML data as a dictionary.

    Returns:
        Contract type string ('effect', 'compute', 'reducer', 'orchestrator'),
        or None if type cannot be determined.
    """
    # Check node_type field (most reliable)
    node_type = data.get("node_type", "")
    if isinstance(node_type, str):
        node_type_lower = node_type.lower()
        # Check exact match first
        if node_type_lower in NODE_TYPE_MAPPING:
            return NODE_TYPE_MAPPING[node_type_lower]
        # Check partial match for flexible naming
        for contract_type in CONTRACT_MODELS:
            if contract_type in node_type_lower:
                return contract_type

    # Check name field for contract type substrings
    name = data.get("name", "")
    if isinstance(name, str):
        name_lower = name.lower()
        for contract_type in CONTRACT_MODELS:
            if contract_type in name_lower:
                return contract_type

    # Default to type-specific fields
    if "algorithm" in data:
        return "compute"
    if "io_configs" in data or "retry_policy" in data:
        return "effect"
    if "fsm" in data or "transitions" in data:
        return "reducer"
    if "workflow" in data or "steps" in data:
        return "orchestrator"

    return None


class ValidatorContractLinter(ValidatorBase):
    """Validator for ONEX contract YAML files.

    This validator checks contract files for ONEX compliance including:
    - Deprecated field names (guardrail: 'version' must be 'contract_version')
    - Required fields (name, contract_version, node_type)
    - Recommended fields (description)
    - Naming conventions (PascalCase/snake_case, Model prefix)
    - Fingerprint format and match
    - Pydantic schema validation

    The validator respects suppression comments defined in the contract.

    Attributes:
        validator_id: Unique identifier for this validator ("contract_linter").
        registry: Optional ContractHashRegistry for baseline fingerprint comparison.

    Usage Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.validator_contract_linter import ValidatorContractLinter
        >>> validator = ValidatorContractLinter()
        >>> result = validator.validate(Path("contracts/"))
        >>> print(f"Valid: {result.is_valid}, Issues: {len(result.issues)}")
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str] = "contract_linter"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        registry: ContractHashRegistry | None = None,
    ) -> None:
        """Initialize the contract linter.

        Args:
            contract: Pre-loaded validator contract. If None, loaded from YAML.
            registry: Optional ContractHashRegistry for baseline fingerprint
                comparison. If None, baseline comparison is skipped.
        """
        super().__init__(contract=contract)
        self.registry = registry

    def _is_contract_file(self, data: dict[str, object]) -> bool:
        """Check if YAML data looks like an ONEX contract.

        A file is considered a contract if it has:
        - 'name' AND 'contract_version' fields at top level, OR
        - 'name' AND deprecated 'version' field (will be rejected by guardrail), OR
        - 'node_type' field, OR
        - Domain-specific fields (fsm, workflow, effect, compute, algorithm)

        Args:
            data: Parsed YAML data as a dictionary.

        Returns:
            True if the data appears to be a contract.
        """
        # Check for standard contract fields
        has_name = "name" in data
        has_contract_version = "contract_version" in data
        has_deprecated_version = (
            "version" in data
        )  # Old field name (OMN-1431) - will be rejected by guardrail
        has_node_type = "node_type" in data

        if has_name and has_contract_version:
            return True

        # Also recognize contracts using deprecated 'version' field so guardrail can reject them
        if has_name and has_deprecated_version:
            return True

        if has_node_type:
            return True

        # Check for domain-specific fields
        domain_fields = {
            "fsm",
            "workflow",
            "steps",
            "effect",
            "compute",
            "algorithm",
            "transitions",
            "io_configs",
            "input_model",
            "output_model",
        }

        return bool(set(data.keys()) & domain_fields)

    def _get_rule_by_id(
        self,
        # ONEX_EXCLUDE: string_id - rule identifier for lookup
        rule_id: str,
        contract: ModelValidatorSubcontract,
    ) -> ModelValidatorRule | None:
        """Get a rule by ID from the contract.

        Args:
            rule_id: The rule ID to look up.
            contract: The validator contract.

        Returns:
            The ModelValidatorRule if found and enabled, None otherwise.
        """
        for rule in contract.rules:
            if rule.rule_id == rule_id and rule.enabled:
                return rule
        return None

    def _get_severity(
        self,
        rule: ModelValidatorRule | None,
        contract: ModelValidatorSubcontract,
        rule_id: str | None = None,
    ) -> EnumSeverity:
        """Get severity for a rule, falling back to default.

        Args:
            rule: The rule (may be None if not found).
            contract: The validator contract.
            rule_id: Optional rule identifier for logging when rule is None.

        Returns:
            The severity to use for issues from this rule.
        """
        if rule is not None:
            return rule.severity
        # Log when falling back to default severity
        effective_rule_id = rule_id or "unknown"
        logger.debug(
            "Rule %s not found in contract, using default severity: %s",
            effective_rule_id,
            contract.severity_default,
        )
        return contract.severity_default

    def _validate_yaml_syntax(
        self,
        path: Path,
        content: str,
    ) -> tuple[dict[str, object] | None, list[ModelValidationIssue]]:
        """Validate YAML syntax and parse content.

        Args:
            path: Path to the contract file.
            content: Raw file content.

        Returns:
            Tuple of (parsed_data, issues). parsed_data is None if parsing failed.
        """
        issues: list[ModelValidationIssue] = []

        try:
            # ONEX_EXCLUDE: manual_yaml - linter checks raw YAML syntax
            data = yaml.safe_load(content)

            if data is None:
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.ERROR,
                        message="Empty YAML content",
                        code=RULE_YAML_SYNTAX,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_YAML_SYNTAX,
                        suggestion="Add contract definition to the file",
                    )
                )
                return None, issues

            if not isinstance(data, dict):
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.ERROR,
                        message=f"Expected YAML dict, got {type(data).__name__}",
                        code=RULE_YAML_SYNTAX,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_YAML_SYNTAX,
                        suggestion="Contract must be a YAML mapping/dict",
                    )
                )
                return None, issues

            return data, issues

        except yaml.YAMLError as e:
            line_num = 1
            if hasattr(e, "problem_mark") and e.problem_mark is not None:
                line_num = e.problem_mark.line + 1

            issues.append(
                ModelValidationIssue(
                    severity=EnumSeverity.ERROR,
                    message=f"YAML syntax error: {e}",
                    code=RULE_YAML_SYNTAX,
                    file_path=path,
                    line_number=line_num,
                    rule_name=RULE_YAML_SYNTAX,
                    suggestion="Fix the YAML syntax error",
                )
            )
            return None, issues

    def _validate_required_fields(
        self,
        data: dict[str, object],
        path: Path,
        rule: ModelValidatorRule | None,
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Check for required contract fields.

        Args:
            data: Parsed YAML data.
            path: Path to the contract file.
            rule: The rule configuration (may be None).
            contract: The validator contract.

        Returns:
            List of validation issues for missing required fields.
        """
        issues: list[ModelValidationIssue] = []
        severity = self._get_severity(rule, contract)

        # Get required fields from rule parameters or use defaults
        required_fields = ["name", "contract_version", "node_type"]
        if rule is not None and rule.parameters is not None:
            fields_param = rule.parameters.get("fields")
            if isinstance(fields_param, list):
                required_fields = [str(f) for f in fields_param]

        for field_name in required_fields:
            if field_name not in data:
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Missing required field: {field_name}",
                        code=RULE_REQUIRED_FIELDS,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_REQUIRED_FIELDS,
                        suggestion=f"Add '{field_name}' field to the contract",
                    )
                )
            elif data[field_name] is None or data[field_name] == "":
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Empty required field: {field_name}",
                        code=RULE_REQUIRED_FIELDS,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_REQUIRED_FIELDS,
                        suggestion=f"Provide a value for '{field_name}'",
                    )
                )

        return issues

    def _validate_deprecated_field_names(
        self,
        data: dict[str, object],
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Guardrail: Reject old field names that have been renamed.

        This prevents regression by failing validation when YAML contracts use
        deprecated field names instead of the current canonical names.

        Currently checks:
        - 'version' → should be 'contract_version' (OMN-1431 migration)

        Args:
            data: Parsed YAML data.
            path: Path to the contract file.
            contract: The validator contract.

        Returns:
            List of validation issues for deprecated field name usage.
        """
        issues: list[ModelValidationIssue] = []

        # Guardrail: Reject old 'version' field name entirely
        # This is always an ERROR regardless of rule configuration - it's a migration guardrail
        # Since v0.9.0 is a breaking change, we don't support transitional dual-field state
        if "version" in data:
            has_contract_version = "contract_version" in data
            if has_contract_version:
                message = (
                    "YAML contracts must not contain deprecated 'version:' field. "
                    "Remove it - 'contract_version:' is already present (OMN-1431)."
                )
                suggestion = (
                    "Remove the deprecated 'version:' field from your YAML contract"
                )
            else:
                message = (
                    "YAML contracts must use 'contract_version:', not 'version:'. "
                    "The 'version' field was renamed to 'contract_version' per ONEX specification (OMN-1431)."
                )
                suggestion = (
                    "Rename 'version:' to 'contract_version:' in your YAML contract"
                )

            issues.append(
                ModelValidationIssue(
                    severity=EnumSeverity.ERROR,
                    message=message,
                    code=RULE_DEPRECATED_FIELD_NAMES,
                    file_path=path,
                    line_number=1,
                    rule_name=RULE_DEPRECATED_FIELD_NAMES,
                    suggestion=suggestion,
                    context={
                        "found_field": "version",
                        "expected_field": "contract_version",
                        "migration_ticket": "OMN-1431",
                    },
                )
            )

        return issues

    def _validate_recommended_fields(
        self,
        data: dict[str, object],
        path: Path,
        rule: ModelValidatorRule | None,
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Check for recommended contract fields.

        Args:
            data: Parsed YAML data.
            path: Path to the contract file.
            rule: The rule configuration (may be None).
            contract: The validator contract.

        Returns:
            List of validation issues for missing recommended fields.
        """
        issues: list[ModelValidationIssue] = []
        severity = self._get_severity(rule, contract)

        # Get recommended fields from rule parameters or use defaults
        recommended_fields = ["description"]
        if rule is not None and rule.parameters is not None:
            fields_param = rule.parameters.get("fields")
            if isinstance(fields_param, list):
                recommended_fields = [str(f) for f in fields_param]

        for field_name in recommended_fields:
            if field_name not in data or not data.get(field_name):
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Missing recommended field: {field_name}",
                        code=RULE_RECOMMENDED_FIELDS,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_RECOMMENDED_FIELDS,
                        suggestion=f"Add a meaningful '{field_name}' to the contract",
                    )
                )

        return issues

    def _validate_naming_convention(
        self,
        data: dict[str, object],
        path: Path,
        rule: ModelValidatorRule | None,
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Validate naming conventions for contract and model names.

        Args:
            data: Parsed YAML data.
            path: Path to the contract file.
            rule: The rule configuration (may be None).
            contract: The validator contract.

        Returns:
            List of validation issues for naming convention violations.
        """
        issues: list[ModelValidationIssue] = []
        severity = self._get_severity(rule, contract)

        # Check contract name follows convention
        name = data.get("name", "")
        if isinstance(name, str) and name:
            # Contract names should be PascalCase or snake_case
            # Use strict regex patterns for validation:
            # - PascalCase: starts with uppercase, at least 2 chars (e.g., "Ab", "NodeCompute")
            # - snake_case: lowercase with underscores between segments (e.g., "a", "node_compute")
            is_pascal = PASCAL_CASE_PATTERN.match(name) is not None
            is_snake = SNAKE_CASE_PATTERN.match(name) is not None
            if not (is_pascal or is_snake):
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Contract name '{name}' does not follow ONEX naming conventions",
                        code=RULE_NAMING_CONVENTION,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_NAMING_CONVENTION,
                        suggestion="Use PascalCase (NodeMyCompute) or snake_case (node_my_compute)",
                    )
                )

        return issues

    def _validate_model_prefix(
        self,
        data: dict[str, object],
        path: Path,
        rule: ModelValidatorRule | None,
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Validate that model class names start with 'Model' prefix.

        Args:
            data: Parsed YAML data.
            path: Path to the contract file.
            rule: The rule configuration (may be None).
            contract: The validator contract.

        Returns:
            List of validation issues for model prefix violations.
        """
        issues: list[ModelValidationIssue] = []
        severity = self._get_severity(rule, contract)

        # Check input_model naming
        input_model = data.get("input_model", "")
        if isinstance(input_model, str) and input_model:
            model_class = (
                input_model.split(".")[-1] if "." in input_model else input_model
            )
            if not model_class.startswith("Model"):
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Input model '{model_class}' should follow Model* naming convention",
                        code=RULE_MODEL_PREFIX,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_MODEL_PREFIX,
                        suggestion="Rename to start with 'Model' (e.g., ModelMyInput)",
                    )
                )

        # Check output_model naming
        output_model = data.get("output_model", "")
        if isinstance(output_model, str) and output_model:
            model_class = (
                output_model.split(".")[-1] if "." in output_model else output_model
            )
            if not model_class.startswith("Model"):
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Output model '{model_class}' should follow Model* naming convention",
                        code=RULE_MODEL_PREFIX,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_MODEL_PREFIX,
                        suggestion="Rename to start with 'Model' (e.g., ModelMyOutput)",
                    )
                )

        return issues

    def _validate_fingerprint_format(
        self,
        data: dict[str, object],
        path: Path,
        rule: ModelValidatorRule | None,
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Validate fingerprint format (semver:12-hex).

        Args:
            data: Parsed YAML data.
            path: Path to the contract file.
            rule: The rule configuration (may be None).
            contract: The validator contract.

        Returns:
            List of validation issues for fingerprint format violations.
        """
        issues: list[ModelValidationIssue] = []
        severity = self._get_severity(rule, contract)

        fingerprint = data.get("fingerprint")

        if fingerprint is None:
            # No fingerprint declared - not an error
            return issues

        if not isinstance(fingerprint, str):
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=f"Fingerprint must be a string, got {type(fingerprint).__name__}",
                    code=RULE_FINGERPRINT_FORMAT,
                    file_path=path,
                    line_number=1,
                    rule_name=RULE_FINGERPRINT_FORMAT,
                    suggestion="Use format '<version>:<hash>' (e.g., '1.0.0:abcdef123456')",
                )
            )
            return issues

        if not FINGERPRINT_PATTERN.match(fingerprint):
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=f"Invalid fingerprint format: '{fingerprint}'",
                    code=RULE_FINGERPRINT_FORMAT,
                    file_path=path,
                    line_number=1,
                    rule_name=RULE_FINGERPRINT_FORMAT,
                    suggestion="Use format 'X.Y.Z:12hex' (e.g., '1.0.0:abcdef123456')",
                )
            )

        return issues

    def _validate_fingerprint_match(
        self,
        data: dict[str, object],
        path: Path,
        rule: ModelValidatorRule | None,
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Validate that declared fingerprint matches computed fingerprint.

        Args:
            data: Parsed YAML data.
            path: Path to the contract file.
            rule: The rule configuration (may be None).
            contract: The validator contract.

        Returns:
            List of validation issues for fingerprint mismatch.
        """
        issues: list[ModelValidationIssue] = []
        severity = self._get_severity(rule, contract)

        declared_fp = data.get("fingerprint")
        if not isinstance(declared_fp, str) or not declared_fp:
            # No fingerprint to validate
            return issues

        # Detect contract type
        contract_type = _detect_contract_type(data)
        if contract_type is None or contract_type not in CONTRACT_MODELS:
            # Can't compute fingerprint without knowing contract type
            return issues

        model_class = CONTRACT_MODELS[contract_type]

        try:
            # Validate against Pydantic model
            contract_model = model_class.model_validate(data)

            # Compute fingerprint
            computed = compute_contract_fingerprint(contract_model)
            computed_fp = str(computed)

            # Parse declared fingerprint
            try:
                declared_parsed = ModelContractFingerprint.from_string(declared_fp)
                if not computed.matches(declared_parsed):
                    issues.append(
                        ModelValidationIssue(
                            severity=severity,
                            message=(
                                f"Fingerprint mismatch: declared '{declared_fp}' "
                                f"does not match computed '{computed_fp}'"
                            ),
                            code=RULE_FINGERPRINT_MATCH,
                            file_path=path,
                            line_number=1,
                            rule_name=RULE_FINGERPRINT_MATCH,
                            suggestion=f"Update fingerprint to '{computed_fp}'",
                        )
                    )
            except ModelOnexError as e:
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Invalid declared fingerprint: {e.message}",
                        code=RULE_FINGERPRINT_MATCH,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_FINGERPRINT_MATCH,
                        suggestion="Use format '<version>:<hash>' (e.g., '1.0.0:abcdef123456')",
                    )
                )

        except VALIDATION_ERRORS:
            # fallback-ok: schema validation failed - can't compute fingerprint
            # This will be reported by schema_validation rule
            pass

        return issues

    def _validate_schema(
        self,
        data: dict[str, object],
        path: Path,
        rule: ModelValidatorRule | None,
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Validate contract against Pydantic schema.

        Args:
            data: Parsed YAML data.
            path: Path to the contract file.
            rule: The rule configuration (may be None).
            contract: The validator contract.

        Returns:
            List of validation issues for schema validation failures.
        """
        issues: list[ModelValidationIssue] = []
        severity = self._get_severity(rule, contract)

        # Detect contract type
        contract_type = _detect_contract_type(data)
        if contract_type is None or contract_type not in CONTRACT_MODELS:
            # Can't validate schema without knowing contract type
            return issues

        model_class = CONTRACT_MODELS[contract_type]

        try:
            model_class.model_validate(data)
        except VALIDATION_ERRORS as e:
            # Handle Pydantic ValidationError with detailed error extraction
            if isinstance(e, ValidationError):
                # Format error details
                error_details = []
                for error in e.errors():
                    loc = ".".join(str(x) for x in error["loc"])
                    msg = error["msg"]
                    error_details.append(f"  - {loc}: {msg}")

                error_list = "\n".join(error_details[:5])
                if len(e.errors()) > 5:
                    error_list += f"\n  ... and {len(e.errors()) - 5} more errors"

                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Contract schema validation failed ({len(e.errors())} errors):\n{error_list}",
                        code=RULE_SCHEMA_VALIDATION,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_SCHEMA_VALIDATION,
                        suggestion="Fix the schema errors listed above",
                    )
                )
            else:
                # Handle TypeError/ValueError with generic message
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Contract validation error: {e}",
                        code=RULE_SCHEMA_VALIDATION,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_SCHEMA_VALIDATION,
                        suggestion="Fix the validation errors in the contract",
                    )
                )

        return issues

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single YAML contract file.

        Performs all validation checks configured in the contract.

        Args:
            path: Path to the YAML file to validate.
            contract: Validator contract with configuration.

        Returns:
            Tuple of ModelValidationIssue instances for violations found.
        """
        issues: list[ModelValidationIssue] = []

        # Read file content
        try:
            content = path.read_text(encoding="utf-8")
        except FILE_IO_ERRORS:
            # fallback-ok: file read error - skip silently
            return ()

        # Parse YAML
        data, syntax_issues = self._validate_yaml_syntax(path, content)
        issues.extend(syntax_issues)

        if data is None:
            return tuple(issues)

        # Skip non-contract files
        if not self._is_contract_file(data):
            return ()

        # Run guardrail checks (always run, not rule-dependent)
        # These prevent regression from field name migrations
        issues.extend(self._validate_deprecated_field_names(data, path, contract))

        # Get rules
        required_rule = self._get_rule_by_id(RULE_REQUIRED_FIELDS, contract)
        recommended_rule = self._get_rule_by_id(RULE_RECOMMENDED_FIELDS, contract)
        naming_rule = self._get_rule_by_id(RULE_NAMING_CONVENTION, contract)
        model_prefix_rule = self._get_rule_by_id(RULE_MODEL_PREFIX, contract)
        fp_format_rule = self._get_rule_by_id(RULE_FINGERPRINT_FORMAT, contract)
        fp_match_rule = self._get_rule_by_id(RULE_FINGERPRINT_MATCH, contract)
        schema_rule = self._get_rule_by_id(RULE_SCHEMA_VALIDATION, contract)

        # Run enabled rules
        if required_rule is not None:
            issues.extend(
                self._validate_required_fields(data, path, required_rule, contract)
            )

        if recommended_rule is not None:
            issues.extend(
                self._validate_recommended_fields(
                    data, path, recommended_rule, contract
                )
            )

        if naming_rule is not None:
            issues.extend(
                self._validate_naming_convention(data, path, naming_rule, contract)
            )

        if model_prefix_rule is not None:
            issues.extend(
                self._validate_model_prefix(data, path, model_prefix_rule, contract)
            )

        if fp_format_rule is not None:
            issues.extend(
                self._validate_fingerprint_format(data, path, fp_format_rule, contract)
            )

        if fp_match_rule is not None:
            issues.extend(
                self._validate_fingerprint_match(data, path, fp_match_rule, contract)
            )

        if schema_rule is not None:
            issues.extend(self._validate_schema(data, path, schema_rule, contract))

        return tuple(issues)


# CLI entry point
if __name__ == "__main__":
    sys.exit(ValidatorContractLinter.main())


__all__ = [
    "CONTRACT_MODELS",
    "NODE_TYPE_MAPPING",
    "PASCAL_CASE_PATTERN",
    "RULE_DEPRECATED_FIELD_NAMES",
    "RULE_FINGERPRINT_FORMAT",
    "RULE_FINGERPRINT_MATCH",
    "RULE_MODEL_PREFIX",
    "RULE_NAMING_CONVENTION",
    "RULE_RECOMMENDED_FIELDS",
    "RULE_REQUIRED_FIELDS",
    "RULE_SCHEMA_VALIDATION",
    "RULE_YAML_SYNTAX",
    "SNAKE_CASE_PATTERN",
    "ValidatorContractLinter",
]
