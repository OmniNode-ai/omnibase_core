"""
Enhanced Contract Validator for ONEX Monadic Architecture.

This module provides comprehensive contract validation and type generation
integrated with the monadic NodeResult patterns, Enhanced ModelNodeBase system,
and observable validation workflows.

Author: ONEX Framework Team
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from omnibase_core.core.monadic.model_node_result import (
    ErrorInfo,
    ErrorType,
    Event,
    NodeResult,
)
from omnibase_core.core.monadic.monadic_composition_utils import (
    MonadicComposer,
    monadic_operation,
    with_timeout,
)


@dataclass
class ContractValidationRule:
    """
    Validation rule for contract structure and content.
    """

    rule_id: str
    description: str
    severity: str  # "error", "warning", "info"
    category: str  # "structure", "schema", "dependencies", "security"
    validator_function: str
    required_fields: list[str] = field(default_factory=list)
    pattern_checks: dict[str, str] = field(default_factory=dict)
    custom_logic: str | None = None


@dataclass
class ValidationResult:
    """
    Result of a single validation rule check.
    """

    rule_id: str
    status: str  # "passed", "failed", "skipped"
    message: str
    severity: str
    category: str
    location: str | None = None
    suggested_fix: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TypeGenerationSpec:
    """
    Specification for generating types from contract definitions.
    """

    source_path: Path
    target_path: Path
    generation_mode: str  # "pydantic", "dataclass", "protocol", "enum"
    naming_convention: str  # "snake_case", "camelCase", "PascalCase"
    include_validation: bool = True
    include_documentation: bool = True
    custom_templates: dict[str, str] | None = None


class EnhancedContractValidator:
    """
    Enhanced contract validator with monadic patterns and type generation.

    This validator provides:
    - Comprehensive contract structure validation
    - Schema compliance checking with detailed error reporting
    - Dependency resolution and validation
    - Security validation for contract specifications
    - Automatic type generation from contract definitions
    - Observable validation with NodeResult composition
    - Integration with Enhanced ModelNodeBase patterns
    """

    def __init__(self, correlation_id: str | None = None):
        self.correlation_id = (
            correlation_id or f"contract_validator_{int(datetime.now().timestamp())}"
        )
        self.composer = MonadicComposer(self.correlation_id)

        # Validation rules registry
        self.validation_rules = self._initialize_validation_rules()

        # Type generation templates
        self.type_templates = self._initialize_type_templates()

        # Validation statistics
        self.validation_stats = {
            "contracts_validated": 0,
            "errors_found": 0,
            "warnings_issued": 0,
            "types_generated": 0,
        }

    def _initialize_validation_rules(self) -> list[ContractValidationRule]:
        """Initialize standard validation rules for ONEX contracts."""
        return [
            ContractValidationRule(
                rule_id="contract_version_required",
                description="Contract must have valid contract_version",
                severity="error",
                category="structure",
                validator_function="validate_contract_version",
                required_fields=[
                    "contract_version",
                    "contract_version.major",
                    "contract_version.minor",
                    "contract_version.patch",
                ],
            ),
            ContractValidationRule(
                rule_id="node_name_required",
                description="Contract must have valid node_name",
                severity="error",
                category="structure",
                validator_function="validate_node_name",
                required_fields=["node_name"],
                pattern_checks={"node_name": r"^[a-z][a-z0-9_]*[a-z0-9]$"},
            ),
            ContractValidationRule(
                rule_id="tool_specification_required",
                description="Contract must have valid tool_specification for ModelNodeBase integration",
                severity="error",
                category="structure",
                validator_function="validate_tool_specification",
                required_fields=[
                    "tool_specification",
                    "tool_specification.main_tool_class",
                    "tool_specification.business_logic_pattern",
                ],
            ),
            ContractValidationRule(
                rule_id="dependencies_structure",
                description="Dependencies must follow ONEX dependency injection patterns",
                severity="warning",
                category="dependencies",
                validator_function="validate_dependencies_structure",
            ),
            ContractValidationRule(
                rule_id="security_sensitive_data",
                description="Contract should not contain sensitive information",
                severity="error",
                category="security",
                validator_function="validate_security_sensitive_data",
                pattern_checks={
                    "password": r"(?i)(password|passwd|pwd|secret|private[_-]?key|access[_-]?token)",
                    "credentials": r"(?i)(credential|authorization|api[_-]?key|bearer[_-]?token)",
                },
            ),
            ContractValidationRule(
                rule_id="monadic_compatibility",
                description="Contract should be compatible with monadic ModelNodeBase patterns",
                severity="warning",
                category="structure",
                validator_function="validate_monadic_compatibility",
            ),
        ]

    def _initialize_type_templates(self) -> dict[str, str]:
        """Initialize type generation templates."""
        return {
            "pydantic_model": '''"""
Generated Pydantic model from ONEX contract: {contract_name}

This model was automatically generated from the contract specification
and includes validation rules and type safety for ONEX architecture.

Generated at: {timestamp}
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class {class_name}(BaseModel):
    """
    {description}

    Generated from contract: {contract_path}
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        frozen=False
    )

{fields}
''',
            "protocol": '''"""
Generated Protocol from ONEX contract: {contract_name}

This protocol was automatically generated from the contract specification
for duck typing and dependency injection in ONEX architecture.

Generated at: {timestamp}
"""

from typing import Any, Dict, List, Optional, Union, Protocol, runtime_checkable
from abc import abstractmethod


@runtime_checkable
class {class_name}(Protocol):
    """
    {description}

    Generated from contract: {contract_path}
    """

{methods}
''',
            "enum": '''"""
Generated Enum from ONEX contract: {contract_name}

This enum was automatically generated from the contract specification
for type-safe enumeration values in ONEX architecture.

Generated at: {timestamp}
"""

from enum import Enum, auto
from typing import Union


class {class_name}(Enum):
    """
    {description}

    Generated from contract: {contract_path}
    """

{values}

    @classmethod
    def from_string(cls, value: str) -> '{class_name}':
        """Convert string value to enum member."""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid {cls.__name__} value: {{value}}")
''',
        }

    # === VALIDATION METHODS ===

    @with_timeout(30.0)  # 30 second timeout for validation
    async def validate_contract(
        self,
        contract_path: Path,
        custom_rules: list[ContractValidationRule] | None = None,
        fail_fast: bool = False,
    ) -> NodeResult[list[ValidationResult]]:
        """
        Validate a contract file with comprehensive rule checking.

        Args:
            contract_path: Path to the contract YAML file
            custom_rules: Optional additional validation rules
            fail_fast: Stop on first error if True

        Returns:
            NodeResult[List[ValidationResult]]: Validation results with context
        """
        start_time = datetime.now()

        # Load contract
        load_result = await self._load_contract(contract_path)
        if load_result.is_failure:
            return NodeResult.failure(
                error=load_result.error,
                provenance=[f"validate_contract.{self.correlation_id}.load_failed"],
                correlation_id=self.correlation_id,
            )

        contract_data = load_result.value

        # Combine default rules with custom rules
        all_rules = self.validation_rules.copy()
        if custom_rules:
            all_rules.extend(custom_rules)

        # Create validation operations
        validation_operations = [
            self._create_validation_operation(rule, contract_data, contract_path)
            for rule in all_rules
        ]

        # Execute validations with appropriate strategy
        if fail_fast:
            results = await self.composer.sequence(
                validation_operations,
                initial_value=None,
                fail_fast=True,
            )
        else:
            results = await self.composer.parallel(
                validation_operations,
                input_values=[None] * len(validation_operations),
                max_concurrency=5,  # Reasonable concurrency for validation
                fail_fast=False,
            )

        if results.is_failure:
            return results  # Propagate validation failure

        # Flatten and analyze validation results
        validation_results = results.value
        flattened_results = []
        error_count = 0
        warning_count = 0

        for result in validation_results:
            if isinstance(result, list):
                flattened_results.extend(result)
            else:
                flattened_results.append(result)

        # Count errors and warnings
        for result in flattened_results:
            if result.severity == "error" and result.status == "failed":
                error_count += 1
            elif result.severity == "warning" and result.status == "failed":
                warning_count += 1

        # Update statistics
        self.validation_stats["contracts_validated"] += 1
        self.validation_stats["errors_found"] += error_count
        self.validation_stats["warnings_issued"] += warning_count

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return NodeResult.success(
            value=flattened_results,
            provenance=[f"validate_contract.{self.correlation_id}.completed"],
            trust_score=0.95,  # High confidence in validation results
            metadata={
                "contract_path": str(contract_path),
                "rules_applied": len(all_rules),
                "errors_found": error_count,
                "warnings_issued": warning_count,
                "validation_duration_ms": duration_ms,
                "fail_fast": fail_fast,
            },
            events=[
                Event(
                    type="contract.validation.completed",
                    payload={
                        "contract_path": str(contract_path),
                        "validation_summary": {
                            "total_rules": len(all_rules),
                            "errors": error_count,
                            "warnings": warning_count,
                            "duration_ms": duration_ms,
                        },
                    },
                    timestamp=end_time,
                    correlation_id=self.correlation_id,
                ),
            ],
            correlation_id=self.correlation_id,
        )

    def _create_validation_operation(
        self,
        rule: ContractValidationRule,
        contract_data: dict[str, Any],
        contract_path: Path,
    ):
        """Create a validation operation for a specific rule."""

        @monadic_operation(f"validation_rule_{rule.rule_id}")
        async def validate_rule(_: Any) -> list[ValidationResult]:
            """Execute a single validation rule."""
            try:
                # Get validator function
                validator = getattr(self, rule.validator_function, None)
                if not validator:
                    return [
                        ValidationResult(
                            rule_id=rule.rule_id,
                            status="failed",
                            message=f"Validator function {rule.validator_function} not found",
                            severity="error",
                            category="internal",
                            location=str(contract_path),
                        ),
                    ]

                # Execute validation
                return await validator(rule, contract_data, contract_path)

            except Exception as e:
                return [
                    ValidationResult(
                        rule_id=rule.rule_id,
                        status="failed",
                        message=f"Validation rule execution failed: {e!s}",
                        severity="error",
                        category="internal",
                        location=str(contract_path),
                        metadata={"exception": str(e)},
                    ),
                ]

        return validate_rule

    async def _load_contract(self, contract_path: Path) -> NodeResult[dict[str, Any]]:
        """Load and parse contract YAML file."""
        try:
            if not contract_path.exists():
                error_info = ErrorInfo(
                    error_type=ErrorType.VALIDATION,
                    message=f"Contract file not found: {contract_path}",
                    correlation_id=self.correlation_id,
                    retryable=False,
                )
                return NodeResult.failure(
                    error=error_info,
                    provenance=[f"load_contract.{self.correlation_id}.file_not_found"],
                )

            with open(contract_path, encoding="utf-8") as file:
                contract_data = yaml.safe_load(file)

            if not isinstance(contract_data, dict):
                error_info = ErrorInfo(
                    error_type=ErrorType.VALIDATION,
                    message="Contract file must contain a YAML dictionary",
                    correlation_id=self.correlation_id,
                    retryable=False,
                )
                return NodeResult.failure(
                    error=error_info,
                    provenance=[f"load_contract.{self.correlation_id}.invalid_format"],
                )

            return NodeResult.success(
                value=contract_data,
                provenance=[f"load_contract.{self.correlation_id}"],
                trust_score=1.0,
                metadata={"file_size": contract_path.stat().st_size},
                correlation_id=self.correlation_id,
            )

        except yaml.YAMLError as e:
            error_info = ErrorInfo(
                error_type=ErrorType.VALIDATION,
                message=f"YAML parsing error: {e!s}",
                trace=str(e),
                correlation_id=self.correlation_id,
                retryable=False,
            )
            return NodeResult.failure(
                error=error_info,
                provenance=[f"load_contract.{self.correlation_id}.yaml_error"],
            )
        except Exception as e:
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=f"Failed to load contract: {e!s}",
                trace=str(e),
                correlation_id=self.correlation_id,
                retryable=False,
            )
            return NodeResult.failure(
                error=error_info,
                provenance=[f"load_contract.{self.correlation_id}.exception"],
            )

    # === VALIDATION RULE IMPLEMENTATIONS ===

    async def validate_contract_version(
        self,
        rule: ContractValidationRule,
        contract_data: dict[str, Any],
        contract_path: Path,
    ) -> list[ValidationResult]:
        """Validate contract version structure."""
        results = []

        # Check if contract_version exists
        if "contract_version" not in contract_data:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="failed",
                    message="Missing required field: contract_version",
                    severity=rule.severity,
                    category=rule.category,
                    location="root.contract_version",
                    suggested_fix="Add contract_version: { major: 1, minor: 0, patch: 0 }",
                ),
            )
            return results

        version = contract_data["contract_version"]

        # Validate version structure
        required_version_fields = ["major", "minor", "patch"]
        for version_field in required_version_fields:
            if version_field not in version:
                results.append(
                    ValidationResult(
                        rule_id=rule.rule_id,
                        status="failed",
                        message=f"Missing version field: {version_field}",
                        severity=rule.severity,
                        category=rule.category,
                        location=f"contract_version.{version_field}",
                        suggested_fix=f"Add {version_field}: 0 to contract_version",
                    ),
                )
            elif (
                not isinstance(version[version_field], int)
                or version[version_field] < 0
            ):
                results.append(
                    ValidationResult(
                        rule_id=rule.rule_id,
                        status="failed",
                        message=f"Invalid version field {version_field}: must be non-negative integer",
                        severity=rule.severity,
                        category=rule.category,
                        location=f"contract_version.{version_field}",
                        suggested_fix=f"Set {version_field} to a non-negative integer (e.g., 0, 1, 2)",
                    ),
                )

        if not results:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    message="Contract version is valid",
                    severity=rule.severity,
                    category=rule.category,
                    location="contract_version",
                    metadata={"version": version},
                ),
            )

        return results

    async def validate_node_name(
        self,
        rule: ContractValidationRule,
        contract_data: dict[str, Any],
        contract_path: Path,
    ) -> list[ValidationResult]:
        """Validate node name format and conventions."""
        results = []

        if "node_name" not in contract_data:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="failed",
                    message="Missing required field: node_name",
                    severity=rule.severity,
                    category=rule.category,
                    location="root.node_name",
                    suggested_fix="Add node_name: 'your_node_name'",
                ),
            )
            return results

        node_name = contract_data["node_name"]

        if not isinstance(node_name, str):
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="failed",
                    message="node_name must be a string",
                    severity=rule.severity,
                    category=rule.category,
                    location="node_name",
                ),
            )
            return results

        # Validate naming pattern
        import re

        pattern = rule.pattern_checks.get("node_name", r"^[a-z][a-z0-9_]*[a-z0-9]$")
        if not re.match(pattern, node_name):
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="failed",
                    message=f"node_name '{node_name}' doesn't match required pattern: {pattern}",
                    severity=rule.severity,
                    category=rule.category,
                    location="node_name",
                    suggested_fix="Use snake_case format: lowercase letters, numbers, underscores only",
                ),
            )
        else:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    message=f"node_name '{node_name}' is valid",
                    severity=rule.severity,
                    category=rule.category,
                    location="node_name",
                    metadata={"node_name": node_name},
                ),
            )

        return results

    async def validate_tool_specification(
        self,
        rule: ContractValidationRule,
        contract_data: dict[str, Any],
        contract_path: Path,
    ) -> list[ValidationResult]:
        """Validate tool specification for ModelNodeBase integration."""
        results = []

        if "tool_specification" not in contract_data:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="failed",
                    message="Missing required field: tool_specification (required for ModelNodeBase integration)",
                    severity=rule.severity,
                    category=rule.category,
                    location="root.tool_specification",
                    suggested_fix="Add tool_specification with main_tool_class and business_logic_pattern",
                ),
            )
            return results

        tool_spec = contract_data["tool_specification"]

        # Check required fields
        required_fields = ["main_tool_class", "business_logic_pattern"]
        for spec_field in required_fields:
            if spec_field not in tool_spec:
                results.append(
                    ValidationResult(
                        rule_id=rule.rule_id,
                        status="failed",
                        message=f"Missing tool_specification field: {spec_field}",
                        severity=rule.severity,
                        category=rule.category,
                        location=f"tool_specification.{spec_field}",
                        suggested_fix=f"Add {spec_field} to tool_specification",
                    ),
                )

        # Validate business logic pattern
        valid_patterns = ["pure_functional", "stateful", "coordination", "workflow"]
        if "business_logic_pattern" in tool_spec:
            pattern = tool_spec["business_logic_pattern"]
            if pattern not in valid_patterns:
                results.append(
                    ValidationResult(
                        rule_id=rule.rule_id,
                        status="failed",
                        message=f"Invalid business_logic_pattern: {pattern}. Must be one of: {valid_patterns}",
                        severity=rule.severity,
                        category=rule.category,
                        location="tool_specification.business_logic_pattern",
                        suggested_fix=f"Use one of: {', '.join(valid_patterns)}",
                    ),
                )

        if not any(result.status == "failed" for result in results):
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    message="tool_specification is valid for ModelNodeBase integration",
                    severity=rule.severity,
                    category=rule.category,
                    location="tool_specification",
                    metadata={"tool_specification": tool_spec},
                ),
            )

        return results

    async def validate_dependencies_structure(
        self,
        rule: ContractValidationRule,
        contract_data: dict[str, Any],
        contract_path: Path,
    ) -> list[ValidationResult]:
        """Validate dependencies structure for DI container."""
        results = []

        if "dependencies" not in contract_data:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    message="No dependencies specified (optional)",
                    severity="info",
                    category=rule.category,
                    location="root.dependencies",
                ),
            )
            return results

        dependencies = contract_data["dependencies"]

        if not isinstance(dependencies, list):
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="failed",
                    message="dependencies must be a list",
                    severity=rule.severity,
                    category=rule.category,
                    location="dependencies",
                ),
            )
            return results

        # Validate each dependency
        for i, dep in enumerate(dependencies):
            required_dep_fields = ["name", "type", "class", "module"]
            for dep_field in required_dep_fields:
                if dep_field not in dep:
                    results.append(
                        ValidationResult(
                            rule_id=rule.rule_id,
                            status="failed",
                            message=f"Dependency {i} missing required field: {dep_field}",
                            severity=rule.severity,
                            category=rule.category,
                            location=f"dependencies[{i}].{dep_field}",
                            suggested_fix=f"Add {dep_field} to dependency specification",
                        ),
                    )

        if not any(result.status == "failed" for result in results):
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    message=f"Dependencies structure is valid ({len(dependencies)} dependencies)",
                    severity="info",
                    category=rule.category,
                    location="dependencies",
                    metadata={"dependency_count": len(dependencies)},
                ),
            )

        return results

    async def validate_security_sensitive_data(
        self,
        rule: ContractValidationRule,
        contract_data: dict[str, Any],
        contract_path: Path,
    ) -> list[ValidationResult]:
        """Validate contract doesn't contain sensitive information."""
        import re

        results = []

        def check_dict_for_sensitive_data(data: dict[str, Any], path: str = "root"):
            """Recursively check dictionary for sensitive patterns."""
            for key, value in data.items():
                current_path = f"{path}.{key}"

                # Check key names
                for pattern_name, pattern in rule.pattern_checks.items():
                    if re.search(pattern, key):
                        results.append(
                            ValidationResult(
                                rule_id=rule.rule_id,
                                status="failed",
                                message=f"Potentially sensitive key detected: '{key}' (matches {pattern_name} pattern)",
                                severity=rule.severity,
                                category=rule.category,
                                location=current_path,
                                suggested_fix="Remove sensitive information or use environment variables",
                            ),
                        )

                # Check string values
                if isinstance(value, str):
                    for pattern_name, pattern in rule.pattern_checks.items():
                        if re.search(pattern, value):
                            results.append(
                                ValidationResult(
                                    rule_id=rule.rule_id,
                                    status="failed",
                                    message=f"Potentially sensitive value detected in '{key}' (matches {pattern_name} pattern)",
                                    severity=rule.severity,
                                    category=rule.category,
                                    location=current_path,
                                    suggested_fix="Remove sensitive information or use environment variables",
                                ),
                            )

                # Recursively check nested dictionaries
                elif isinstance(value, dict):
                    check_dict_for_sensitive_data(value, current_path)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            check_dict_for_sensitive_data(item, f"{current_path}[{i}]")

        check_dict_for_sensitive_data(contract_data)

        if not results:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    message="No sensitive information detected in contract",
                    severity="info",
                    category=rule.category,
                    location="contract",
                ),
            )

        return results

    async def validate_monadic_compatibility(
        self,
        rule: ContractValidationRule,
        contract_data: dict[str, Any],
        contract_path: Path,
    ) -> list[ValidationResult]:
        """Validate compatibility with monadic ModelNodeBase patterns."""
        results = []

        # Check for monadic-friendly patterns
        compatibility_score = 0
        checks = []

        # Check tool specification
        if "tool_specification" in contract_data:
            tool_spec = contract_data["tool_specification"]
            if tool_spec.get("business_logic_pattern") in [
                "pure_functional",
                "workflow",
            ]:
                compatibility_score += 2
                checks.append("Business logic pattern supports monadic composition")
            else:
                checks.append(
                    "Business logic pattern may need adaptation for monadic patterns",
                )

        # Check dependencies structure
        if "dependencies" in contract_data:
            compatibility_score += 1
            checks.append("Dependencies structure supports DI container integration")

        # Check for input/output state definitions
        if "input_state" in contract_data and "output_state" in contract_data:
            compatibility_score += 2
            checks.append("Input/output state definitions support NodeResult patterns")

        # Determine overall compatibility
        if compatibility_score >= 4:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    message="Contract is highly compatible with monadic ModelNodeBase patterns",
                    severity="info",
                    category=rule.category,
                    location="contract",
                    metadata={
                        "compatibility_score": compatibility_score,
                        "checks_passed": checks,
                    },
                ),
            )
        elif compatibility_score >= 2:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    message="Contract is compatible with monadic patterns with minor adaptations",
                    severity="warning",
                    category=rule.category,
                    location="contract",
                    suggested_fix="Consider adding input_state and output_state definitions",
                    metadata={
                        "compatibility_score": compatibility_score,
                        "checks_passed": checks,
                    },
                ),
            )
        else:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    status="failed",
                    message="Contract may need significant adaptation for monadic patterns",
                    severity="warning",
                    category=rule.category,
                    location="contract",
                    suggested_fix="Add tool_specification, dependencies, and state definitions",
                    metadata={
                        "compatibility_score": compatibility_score,
                        "checks_passed": checks,
                    },
                ),
            )

        return results

    # === TYPE GENERATION METHODS ===

    @with_timeout(60.0)  # 60 second timeout for type generation
    async def generate_types_from_contract(
        self,
        contract_path: Path,
        output_directory: Path,
        generation_specs: list[TypeGenerationSpec] | None = None,
    ) -> NodeResult[list[Path]]:
        """
        Generate type definitions from contract specifications.

        Args:
            contract_path: Path to the contract file
            output_directory: Directory for generated type files
            generation_specs: Optional custom generation specifications

        Returns:
            NodeResult[List[Path]]: Paths to generated type files
        """
        start_time = datetime.now()

        # Load and validate contract first
        validation_result = await self.validate_contract(contract_path)
        if validation_result.is_failure:
            return NodeResult.failure(
                error=validation_result.error,
                provenance=[f"generate_types.{self.correlation_id}.validation_failed"],
                correlation_id=self.correlation_id,
            )

        # Check for validation errors that would prevent type generation
        error_results = [
            r
            for r in validation_result.value
            if r.severity == "error" and r.status == "failed"
        ]
        if error_results:
            error_messages = [r.message for r in error_results[:3]]  # First 3 errors
            error_info = ErrorInfo(
                error_type=ErrorType.VALIDATION,
                message=f"Cannot generate types due to contract validation errors: {'; '.join(error_messages)}",
                context={"validation_errors": len(error_results)},
                correlation_id=self.correlation_id,
                retryable=False,
            )
            return NodeResult.failure(
                error=error_info,
                provenance=[f"generate_types.{self.correlation_id}.validation_errors"],
                correlation_id=self.correlation_id,
            )

        # Load contract data
        load_result = await self._load_contract(contract_path)
        if load_result.is_failure:
            return load_result

        contract_data = load_result.value

        # Ensure output directory exists
        output_directory.mkdir(parents=True, exist_ok=True)

        # Generate default specs if not provided
        if not generation_specs:
            generation_specs = self._create_default_generation_specs(
                contract_data,
                contract_path,
                output_directory,
            )

        # Create type generation operations
        generation_operations = [
            self._create_type_generation_operation(spec, contract_data)
            for spec in generation_specs
        ]

        # Execute type generation in parallel
        results = await self.composer.parallel(
            generation_operations,
            input_values=[None] * len(generation_operations),
            max_concurrency=3,  # Reasonable concurrency for file I/O
            fail_fast=False,
        )

        if results.is_failure:
            return results

        # Collect generated file paths
        generated_files = []
        for result in results.value:
            if isinstance(result, Path):
                generated_files.append(result)
            elif isinstance(result, list):
                generated_files.extend(result)

        # Update statistics
        self.validation_stats["types_generated"] += len(generated_files)

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return NodeResult.success(
            value=generated_files,
            provenance=[f"generate_types.{self.correlation_id}.completed"],
            trust_score=0.9,  # High confidence in type generation
            metadata={
                "contract_path": str(contract_path),
                "output_directory": str(output_directory),
                "files_generated": len(generated_files),
                "generation_specs": len(generation_specs),
                "generation_duration_ms": duration_ms,
            },
            events=[
                Event(
                    type="contract.types.generated",
                    payload={
                        "contract_path": str(contract_path),
                        "files_generated": len(generated_files),
                        "duration_ms": duration_ms,
                    },
                    timestamp=end_time,
                    correlation_id=self.correlation_id,
                ),
            ],
            correlation_id=self.correlation_id,
        )

    def _create_default_generation_specs(
        self,
        contract_data: dict[str, Any],
        contract_path: Path,
        output_directory: Path,
    ) -> list[TypeGenerationSpec]:
        """Create default type generation specifications."""
        specs = []
        node_name = contract_data.get("node_name", "unknown_node")

        # Generate input/output state models if defined
        if "input_state" in contract_data:
            specs.append(
                TypeGenerationSpec(
                    source_path=contract_path,
                    target_path=output_directory / f"model_{node_name}_input_state.py",
                    generation_mode="pydantic",
                    naming_convention="snake_case",
                ),
            )

        if "output_state" in contract_data:
            specs.append(
                TypeGenerationSpec(
                    source_path=contract_path,
                    target_path=output_directory / f"model_{node_name}_output_state.py",
                    generation_mode="pydantic",
                    naming_convention="snake_case",
                ),
            )

        # Generate protocol if tool specification exists
        if "tool_specification" in contract_data:
            specs.append(
                TypeGenerationSpec(
                    source_path=contract_path,
                    target_path=output_directory / f"protocol_{node_name}.py",
                    generation_mode="protocol",
                    naming_convention="PascalCase",
                ),
            )

        return specs

    def _create_type_generation_operation(
        self,
        spec: TypeGenerationSpec,
        contract_data: dict[str, Any],
    ):
        """Create a type generation operation."""

        @monadic_operation(f"generate_type_{spec.generation_mode}")
        async def generate_type(_: Any) -> Path:
            """Generate a type file from specification."""

            if spec.generation_mode == "pydantic":
                content = self._generate_pydantic_model(contract_data, spec)
            elif spec.generation_mode == "protocol":
                content = self._generate_protocol(contract_data, spec)
            elif spec.generation_mode == "enum":
                content = self._generate_enum(contract_data, spec)
            else:
                msg = f"Unsupported generation mode: {spec.generation_mode}"
                raise ValueError(msg)

            # Write generated content to file
            with open(spec.target_path, "w", encoding="utf-8") as f:
                f.write(content)

            return spec.target_path

        return generate_type

    def _generate_pydantic_model(
        self,
        contract_data: dict[str, Any],
        spec: TypeGenerationSpec,
    ) -> str:
        """Generate Pydantic model from contract data."""
        node_name = contract_data.get("node_name", "unknown")
        class_name = self._format_class_name(
            f"Model{node_name}InputState",
            spec.naming_convention,
        )

        # Generate field definitions (simplified for example)
        fields = "    # TODO: Generate actual fields from contract schema"

        return self.type_templates["pydantic_model"].format(
            contract_name=contract_data.get("contract_name", "unknown"),
            class_name=class_name,
            description=contract_data.get("description", "Generated model"),
            contract_path=str(spec.source_path),
            timestamp=datetime.now().isoformat(),
            fields=fields,
        )

    def _generate_protocol(
        self,
        contract_data: dict[str, Any],
        spec: TypeGenerationSpec,
    ) -> str:
        """Generate Protocol from contract data."""
        node_name = contract_data.get("node_name", "unknown")
        class_name = self._format_class_name(
            f"Protocol{node_name}",
            spec.naming_convention,
        )

        # Generate method definitions (simplified for example)
        methods = "    # TODO: Generate actual methods from contract specification"

        return self.type_templates["protocol"].format(
            contract_name=contract_data.get("contract_name", "unknown"),
            class_name=class_name,
            description=contract_data.get("description", "Generated protocol"),
            contract_path=str(spec.source_path),
            timestamp=datetime.now().isoformat(),
            methods=methods,
        )

    def _generate_enum(
        self,
        contract_data: dict[str, Any],
        spec: TypeGenerationSpec,
    ) -> str:
        """Generate Enum from contract data."""
        node_name = contract_data.get("node_name", "unknown")
        class_name = self._format_class_name(f"Enum{node_name}", spec.naming_convention)

        # Generate enum values (simplified for example)
        values = "    # TODO: Generate actual values from contract enumeration"

        return self.type_templates["enum"].format(
            contract_name=contract_data.get("contract_name", "unknown"),
            class_name=class_name,
            description=contract_data.get("description", "Generated enum"),
            contract_path=str(spec.source_path),
            timestamp=datetime.now().isoformat(),
            values=values,
        )

    def _format_class_name(self, name: str, convention: str) -> str:
        """Format class name according to naming convention."""
        if convention == "PascalCase":
            return "".join(word.capitalize() for word in name.split("_"))
        if convention == "camelCase":
            words = name.split("_")
            return words[0].lower() + "".join(word.capitalize() for word in words[1:])
        # snake_case
        return name.lower()

    # === UTILITY METHODS ===

    def get_validation_statistics(self) -> dict[str, Any]:
        """Get current validation statistics."""
        return self.validation_stats.copy()

    def reset_statistics(self) -> None:
        """Reset validation statistics."""
        self.validation_stats = {
            "contracts_validated": 0,
            "errors_found": 0,
            "warnings_issued": 0,
            "types_generated": 0,
        }

    def add_custom_validation_rule(self, rule: ContractValidationRule) -> None:
        """Add a custom validation rule."""
        self.validation_rules.append(rule)

    def remove_validation_rule(self, rule_id: str) -> bool:
        """Remove a validation rule by ID."""
        original_count = len(self.validation_rules)
        self.validation_rules = [
            r for r in self.validation_rules if r.rule_id != rule_id
        ]
        return len(self.validation_rules) < original_count
