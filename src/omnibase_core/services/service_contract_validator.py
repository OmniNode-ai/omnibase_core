"""
Contract Validation API.

Provides programmatic contract validation against ONEX standards with:
- YAML contract validation against locked-down models
- Model code compliance checking
- Scoring based on completeness and correctness
- Actionable error messages for validation
"""

import ast
import re
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import ValidationError

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_contract_validation_result import (
    ModelContractValidationResult,
)
from omnibase_core.protocols import (
    ProtocolArchitectureCompliance,
    ProtocolComplianceReport,
    ProtocolComplianceRule,
    ProtocolComplianceViolation,
    ProtocolONEXStandards,
    ProtocolValidationResult,
)
from omnibase_core.types import (
    TypedDictContractData,
    TypedDictModelClassInfo,
    TypedDictModelFieldInfo,
)

# Validation constants
MAX_YAML_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit for YAML files
MAX_CODE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB limit for model code
MIN_DESCRIPTION_LENGTH = 10  # Minimum characters for description
VIOLATION_SCORE_PENALTY = 0.2  # Score reduction per violation
WARNING_SCORE_PENALTY = 0.05  # Score reduction per warning
MINOR_VIOLATION_PENALTY = 0.1  # Small penalty for minor issues
MODEL_NOT_FOUND_PENALTY = 0.2  # Penalty for missing models
NO_MODEL_CLASSES_PENALTY = 0.3  # Penalty for no model classes
VIOLATION_PENALTY_MODEL_COMPLIANCE = 0.15  # Model compliance violation penalty
WARNING_PENALTY_MODEL_COMPLIANCE = 0.05  # Model compliance warning penalty


class ServiceContractValidator:
    """
    Programmatic contract validation API.

    Validates YAML contracts and model code against ONEX standards:
    - Uses locked-down contract models (INTERFACE_VERSION 1.0.0)
    - Checks required fields, types, and naming conventions
    - Provides actionable error messages
    - Scores based on completeness and correctness

    Implements ProtocolComplianceValidator for SPI compatibility.

    Thread Safety:
        This class is NOT thread-safe. It maintains mutable instance state
        including custom_rules list, onex_standards, and architecture_rules
        that can be modified via add_custom_rule() and configure_onex_standards().
        Concurrent modifications from multiple threads could cause data races.
        For thread-safe usage, create separate instances per thread, or ensure
        all configuration is complete before sharing an instance (read-only mode).
        See docs/guides/THREADING.md for more details.

    Example:
        >>> from omnibase_core.services import ServiceContractValidator
        >>> validator = ServiceContractValidator()
        >>> result = validator.validate_contract_yaml(yaml_content, "compute")
        >>> print(f"Valid: {result.is_valid}, Score: {result.score}")

    .. note::
        Previously named ``ProtocolContractValidator``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Protocol``
        prefix is reserved for typing.Protocol interfaces; ``Service``
        prefix indicates a stateful service class.
    """

    # Contract type mapping to model classes
    CONTRACT_MODELS = {
        "effect": ModelContractEffect,
        "compute": ModelContractCompute,
        "reducer": ModelContractReducer,
        "orchestrator": ModelContractOrchestrator,
    }

    # ONEX naming patterns
    CLASS_PATTERN = re.compile(
        r"^Node[A-Z][a-zA-Z0-9]*(Effect|Compute|Reducer|Orchestrator)$"
    )
    FILE_PATTERN = re.compile(
        r"^node_[a-z][a-z0-9_]*_(effect|compute|reducer|orchestrator)\.py$"
    )
    MODEL_PATTERN = re.compile(r"^Model[A-Z][a-zA-Z0-9]*$")

    def __init__(
        self,
        onex_standards: ProtocolONEXStandards | None = None,
        architecture_rules: ProtocolArchitectureCompliance | None = None,
        strict_mode: bool = False,
    ) -> None:
        """
        Initialize the contract validator.

        Args:
            onex_standards: Optional ONEX standards implementation
            architecture_rules: Optional architecture compliance rules
            strict_mode: Enable strict validation mode
        """
        self.interface_version = ModelSemVer(major=1, minor=0, patch=0)

        # Protocol compliance attributes
        self.onex_standards = onex_standards
        self.architecture_rules = architecture_rules
        self.custom_rules: list[ProtocolComplianceRule] = []
        self.strict_mode = strict_mode

    @standard_error_handling("Contract YAML validation")
    def validate_contract_yaml(
        self,
        contract_content: str,
        contract_type: Literal[
            "effect", "compute", "reducer", "orchestrator"
        ] = "effect",
    ) -> ModelContractValidationResult:
        """
        Validate a YAML contract against ONEX standards.

        Args:
            contract_content: YAML contract content as string
            contract_type: Type of contract to validate against

        Returns:
            ModelContractValidationResult with validation details and scoring

        Raises:
            OnexError: If content size exceeds limits
        """
        violations: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []
        score = 1.0

        # Step 0: Validate size limits
        content_size = len(contract_content.encode("utf-8"))
        if content_size > MAX_YAML_SIZE_BYTES:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"YAML content too large: {content_size} bytes exceeds {MAX_YAML_SIZE_BYTES} byte limit",
            )

        # Step 1: Parse YAML content
        try:
            yaml_data = yaml.safe_load(
                contract_content
            )  # yaml-ok: Contract validation requires raw YAML parsing for flexible schema checking
            if yaml_data is None:
                return ModelContractValidationResult(
                    is_valid=False,
                    score=0.0,
                    violations=["Empty YAML content"],
                    contract_type=contract_type,
                    interface_version=self.interface_version,
                )

            # Note: node_type preprocessing removed - Pydantic model validators
            # now handle lowercase architecture type strings directly
            #
            # Note: version preprocessing removed - YAML contracts now use
            # 'contract_version' field, and Pydantic v2 handles dict-to-ModelSemVer
            # conversion automatically during model_validate()

        except yaml.YAMLError as e:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"YAML parsing error: {e}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )

        # Step 2: Validate against contract schema
        contract_model = self.CONTRACT_MODELS.get(contract_type)
        if not contract_model:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Unknown contract type: {contract_type}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )

        try:
            # NOTE(OMN-1302): Duck-typed Pydantic model from registry. Safe because models validated at registration.
            contract_instance = contract_model.model_validate(yaml_data)  # type: ignore[attr-defined]

            # Step 3: Check ONEX compliance
            self._check_onex_compliance(
                contract_instance,
                violations,
                warnings,
                suggestions,
            )

            # Step 4: Calculate score
            score = self._calculate_score(violations, warnings)

        except ValidationError as e:
            # Extract validation errors
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                violations.append(f"{field}: {message}")
                score -= MINOR_VIOLATION_PENALTY

            # Add suggestions based on common errors
            self._add_suggestions_for_errors(e, suggestions)

        except ModelOnexError as e:
            violations.append(f"ONEX validation error: {e.message}")
            score -= VIOLATION_SCORE_PENALTY

        except ValueError as e:
            violations.append(f"Value error in contract: {e}")
            score -= VIOLATION_SCORE_PENALTY

        except TypeError as e:
            violations.append(f"Type error in contract: {e}")
            score -= VIOLATION_SCORE_PENALTY

        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))

        return ModelContractValidationResult(
            is_valid=len(violations) == 0,
            score=score,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions,
            contract_type=contract_type,
            interface_version=self.interface_version,
        )

    def validate_model_compliance(
        self,
        model_code: str,
        contract_yaml: str,
    ) -> ModelContractValidationResult:
        """
        Validate Pydantic model code against a contract.

        Args:
            model_code: Python code containing Pydantic model definition
            contract_yaml: YAML contract content as string

        Returns:
            ModelContractValidationResult with compliance details

        Raises:
            OnexError: If content size exceeds limits
        """
        violations: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []
        score = 1.0

        # Step 0: Validate size limits
        code_size = len(model_code.encode("utf-8"))
        if code_size > MAX_CODE_SIZE_BYTES:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Model code too large: {code_size} bytes exceeds {MAX_CODE_SIZE_BYTES} byte limit",
            )

        yaml_size = len(contract_yaml.encode("utf-8"))
        if yaml_size > MAX_YAML_SIZE_BYTES:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Contract YAML too large: {yaml_size} bytes exceeds {MAX_YAML_SIZE_BYTES} byte limit",
            )

        # Step 1: Parse YAML contract
        try:
            yaml_data = yaml.safe_load(
                contract_yaml
            )  # yaml-ok: Contract validation requires raw YAML parsing for flexible schema checking
            if yaml_data is None:
                return ModelContractValidationResult(
                    is_valid=False,
                    score=0.0,
                    violations=["Empty contract YAML"],
                    interface_version=self.interface_version,
                )
        except yaml.YAMLError as e:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Contract YAML parsing error: {e}"],
                interface_version=self.interface_version,
            )

        # Step 2: Parse model code using AST
        try:
            tree = ast.parse(model_code)
        except SyntaxError as e:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Python syntax error: {e}"],
                interface_version=self.interface_version,
            )
        except RecursionError as e:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Code too deeply nested: {e}"],
                interface_version=self.interface_version,
            )

        # Step 3: Extract model definitions
        model_classes = self._extract_model_classes(tree)
        if not model_classes:
            violations.append("No Pydantic model classes found in code")
            score -= NO_MODEL_CLASSES_PENALTY

        # Step 4: Validate model against contract
        _contract_name = yaml_data.get("name", "")
        input_model = yaml_data.get("input_model", "")
        output_model = yaml_data.get("output_model", "")

        # Check input/output models exist
        if input_model:
            model_name = input_model.split(".")[-1]
            if not any(cls["name"] == model_name for cls in model_classes):
                violations.append(f"Input model '{model_name}' not found in code")
                score -= MODEL_NOT_FOUND_PENALTY
            else:
                suggestions.append(
                    f"Input model '{model_name}' found - verify fields match contract"
                )

        if output_model:
            model_name = output_model.split(".")[-1]
            if not any(cls["name"] == model_name for cls in model_classes):
                violations.append(f"Output model '{model_name}' not found in code")
                score -= MODEL_NOT_FOUND_PENALTY
            else:
                suggestions.append(
                    f"Output model '{model_name}' found - verify fields match contract"
                )

        # Step 5: Check field definitions
        for model_class in model_classes:
            self._validate_model_fields(
                model_class,
                yaml_data,
                violations,
                warnings,
                suggestions,
            )

        # Step 6: Check ONEX naming conventions
        self._check_model_naming(model_classes, violations, warnings)

        # Calculate final score
        score = max(
            0.0,
            min(
                1.0,
                score
                - (len(violations) * VIOLATION_PENALTY_MODEL_COMPLIANCE)
                - (len(warnings) * WARNING_PENALTY_MODEL_COMPLIANCE),
            ),
        )

        return ModelContractValidationResult(
            is_valid=len(violations) == 0,
            score=score,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions,
            interface_version=self.interface_version,
        )

    def _check_onex_compliance(
        self,
        contract: ModelContractBase,
        violations: list[str],
        warnings: list[str],
        suggestions: list[str],
    ) -> None:
        """Check ONEX compliance for contract."""
        # Check contract version against validator version
        if contract.contract_version != self.interface_version:
            warnings.append(
                f"Contract version mismatch: expected {self.interface_version}, "
                f"got {contract.contract_version}"
            )

        # Check naming conventions
        if not contract.name:
            violations.append("Contract must have a non-empty name")
        else:
            # Suggest ONEX naming pattern
            node_type = (
                contract.node_type.value.lower()
                if isinstance(contract.node_type, EnumNodeType)
                else str(contract.node_type).lower()
            )
            expected_suffix = node_type.capitalize()
            if not contract.name.endswith(expected_suffix):
                suggestions.append(
                    f"Consider naming contract with '{expected_suffix}' suffix "
                    f"(e.g., '{contract.name}{expected_suffix}')"
                )

        # Check description
        if not contract.description:
            warnings.append("Contract should have a meaningful description")
        elif len(contract.description) < MIN_DESCRIPTION_LENGTH:
            warnings.append(
                f"Contract description is too short (minimum {MIN_DESCRIPTION_LENGTH} characters recommended)"
            )

        # Check input/output models
        if not contract.input_model:
            violations.append("Contract must specify input_model")
        elif not contract.input_model.startswith("Model"):
            warnings.append(
                f"Input model '{contract.input_model}' should follow ONEX naming (Model*)"
            )

        if not contract.output_model:
            violations.append("Contract must specify output_model")
        elif not contract.output_model.startswith("Model"):
            warnings.append(
                f"Output model '{contract.output_model}' should follow ONEX naming (Model*)"
            )

        # Check dependencies
        if contract.dependencies:
            for dep in contract.dependencies:
                if dep.module and not self._is_valid_module_path(dep.module):
                    warnings.append(
                        f"Dependency module '{dep.module}' may not be a valid Python path"
                    )

    def _calculate_score(self, violations: list[str], warnings: list[str]) -> float:
        """Calculate validation score based on issues found."""
        base_score = 1.0

        # Each violation reduces score significantly
        violation_penalty = len(violations) * VIOLATION_SCORE_PENALTY

        # Each warning reduces score slightly
        warning_penalty = len(warnings) * WARNING_SCORE_PENALTY

        final_score = base_score - violation_penalty - warning_penalty

        # Ensure score is between 0.0 and 1.0
        return max(0.0, min(1.0, final_score))

    def _add_suggestions_for_errors(
        self,
        validation_error: ValidationError,
        suggestions: list[str],
    ) -> None:
        """Add helpful suggestions based on validation errors."""
        for error in validation_error.errors():
            error_type = error.get("type", "")
            field = ".".join(str(loc) for loc in error["loc"])

            if "missing" in error_type:
                suggestions.append(f"Add required field: {field}")
            elif "type_error" in error_type:
                suggestions.append(f"Check type for field: {field}")
            elif "value_error" in error_type:
                suggestions.append(f"Check value constraints for field: {field}")

    def _extract_model_classes(self, tree: ast.AST) -> list[TypedDictModelClassInfo]:
        """Extract Pydantic model class definitions from AST."""
        model_classes: list[TypedDictModelClassInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a BaseModel subclass
                for base in node.bases:
                    if isinstance(base, ast.Name) and "BaseModel" in base.id:
                        # Extract fields
                        fields: list[TypedDictModelFieldInfo] = []
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(
                                item.target, ast.Name
                            ):
                                field_name = item.target.id
                                field_type = (
                                    ast.unparse(item.annotation)
                                    if item.annotation
                                    else "Any"
                                )
                                field_info: TypedDictModelFieldInfo = {
                                    "name": field_name,
                                    "type": field_type,
                                }
                                fields.append(field_info)

                        model_info: TypedDictModelClassInfo = {
                            "name": node.name,
                            "fields": fields,
                            "bases": [ast.unparse(b) for b in node.bases],
                        }
                        model_classes.append(model_info)
                        break

        return model_classes

    def _validate_model_fields(
        self,
        model_class: TypedDictModelClassInfo,
        contract_data: TypedDictContractData,
        violations: list[str],
        warnings: list[str],
        suggestions: list[str],
    ) -> None:
        """Validate model fields against contract specifications."""
        model_name = model_class["name"]
        fields: list[TypedDictModelFieldInfo] = model_class.get("fields", [])

        # Check if this is the input or output model
        input_model = contract_data.get("input_model", "")
        output_model = contract_data.get("output_model", "")

        if model_name in input_model or model_name in output_model:
            # Verify it has fields
            if not fields:
                warnings.append(f"Model '{model_name}' has no fields defined")
            else:
                suggestions.append(
                    f"Model '{model_name}' has {len(fields)} fields - "
                    "verify they match contract requirements"
                )

            # Check for proper type annotations
            for field in fields:
                field_name = field.get("name", "")
                field_type = field.get("type", "Any")

                if field_type == "Any":
                    warnings.append(
                        f"Model '{model_name}' field '{field_name}' uses 'Any' type - "
                        "ONEX standards require strong typing"
                    )

    def _check_model_naming(
        self,
        model_classes: list[TypedDictModelClassInfo],
        violations: list[str],
        warnings: list[str],
    ) -> None:
        """Check ONEX naming conventions for models."""
        for model_class in model_classes:
            name = model_class["name"]

            # Check Model prefix
            if not name.startswith("Model"):
                warnings.append(
                    f"Model class '{name}' should follow ONEX naming convention "
                    f"(start with 'Model')"
                )

            # Check PascalCase
            if not name[0].isupper():
                violations.append(f"Model class '{name}' must use PascalCase")

    def _is_valid_module_path(self, module: str) -> bool:
        """Check if a module path follows Python conventions."""
        # Basic validation for Python module paths
        parts = module.split(".")
        return all(part.isidentifier() for part in parts)

    def _validate_safe_path(self, path: Path, base_dir: Path | None = None) -> bool:
        """
        Validate that path is safe and doesn't escape expected directories.

        Args:
            path: Path to validate
            base_dir: Base directory to constrain path within (optional)

        Returns:
            True if path is safe, False otherwise
        """
        try:
            resolved_path = path.resolve()

            # Check if file is a regular file (not directory, symlink, etc.)
            if resolved_path.exists() and not resolved_path.is_file():
                return False

            # If base_dir specified, ensure path is within it
            if base_dir is not None:
                try:
                    resolved_path.relative_to(base_dir.resolve())
                except ValueError:
                    # Path escapes base directory
                    return False

            return True

        except (OSError, RuntimeError):
            return False

    # ProtocolComplianceValidator interface methods

    async def validate_file_compliance(
        self, file_path: str, content: str | None = None
    ) -> ProtocolComplianceReport:
        """
        Validate file compliance with ONEX standards.

        Args:
            file_path: Path to file to validate
            content: Optional file content (reads from file if not provided)

        Returns:
            Compliance report with violations and recommendations

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_file_compliance() protocol method not yet implemented. "
            "Use validate_contract_yaml() or validate_model_compliance() instead."
        )

    async def validate_repository_compliance(
        self, repository_path: str, file_patterns: list[str] | None = None
    ) -> list[ProtocolComplianceReport]:
        """
        Validate entire repository compliance.

        Args:
            repository_path: Path to repository root
            file_patterns: Optional file patterns to validate

        Returns:
            List of compliance reports for each file

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_repository_compliance() protocol method not yet implemented"
        )

    async def validate_onex_naming(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolComplianceViolation]:
        """
        Validate ONEX naming conventions.

        Args:
            file_path: Path to file to validate
            content: Optional file content

        Returns:
            List of naming convention violations

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_onex_naming() protocol method not yet implemented"
        )

    async def validate_architecture_compliance(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolComplianceViolation]:
        """
        Validate architecture compliance.

        Args:
            file_path: Path to file to validate
            content: Optional file content

        Returns:
            List of architecture violations

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_architecture_compliance() protocol method not yet implemented"
        )

    async def validate_directory_structure(
        self, repository_path: str
    ) -> list[ProtocolComplianceViolation]:
        """
        Validate repository directory structure.

        Args:
            repository_path: Path to repository root

        Returns:
            List of directory structure violations

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_directory_structure() protocol method not yet implemented"
        )

    async def validate_dependency_compliance(
        self, file_path: str, imports: list[str]
    ) -> list[ProtocolComplianceViolation]:
        """
        Validate dependency compliance.

        Args:
            file_path: Path to file
            imports: List of import statements

        Returns:
            List of dependency violations

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_dependency_compliance() protocol method not yet implemented"
        )

    async def aggregate_compliance_results(
        self, reports: list[ProtocolComplianceReport]
    ) -> ProtocolValidationResult:
        """
        Aggregate compliance results into validation result.

        Args:
            reports: List of compliance reports

        Returns:
            Aggregated validation result

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "aggregate_compliance_results() protocol method not yet implemented"
        )

    def add_custom_rule(self, rule: ProtocolComplianceRule) -> None:
        """
        Add custom compliance rule.

        Args:
            rule: Custom compliance rule to add
        """
        self.custom_rules.append(rule)

    def configure_onex_standards(self, standards: ProtocolONEXStandards) -> None:
        """
        Configure ONEX standards.

        Args:
            standards: ONEX standards configuration
        """
        self.onex_standards = standards

    async def get_compliance_summary(
        self, reports: list[ProtocolComplianceReport]
    ) -> str:
        """
        Get compliance summary from reports.

        Args:
            reports: List of compliance reports

        Returns:
            Human-readable compliance summary

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "get_compliance_summary() protocol method not yet implemented"
        )

    def validate_contract_file(
        self,
        file_path: str | Path,
        contract_type: Literal[
            "effect", "compute", "reducer", "orchestrator"
        ] = "effect",
        base_dir: Path | None = None,
    ) -> ModelContractValidationResult:
        """
        Validate a YAML contract file.

        Args:
            file_path: Path to YAML contract file
            contract_type: Type of contract to validate against
            base_dir: Optional base directory to constrain file path within

        Returns:
            ModelContractValidationResult with validation details

        Raises:
            OnexError: If path validation fails or file size exceeds limits
        """
        path = Path(file_path)

        # Validate path safety
        if not self._validate_safe_path(path, base_dir):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid or unsafe file path: {file_path}",
            )

        if not path.exists():
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Contract file not found: {file_path}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )

        # Check file size before reading
        try:
            file_size = path.stat().st_size
            if file_size > MAX_YAML_SIZE_BYTES:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Contract file too large: {file_size} bytes exceeds {MAX_YAML_SIZE_BYTES} byte limit",
                )
        except OSError as e:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Error accessing contract file: {e}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )

        # Read and validate file content
        try:
            content = path.read_text(encoding="utf-8")
            # NOTE(OMN-1494): Cast needed because @standard_error_handling decorator erases return type.
            return cast(
                ModelContractValidationResult,
                self.validate_contract_yaml(content, contract_type),
            )
        except UnicodeDecodeError as e:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Contract file encoding error: {e}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )
        except PermissionError as e:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Permission denied reading contract file: {e}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )
        except OSError as e:
            return ModelContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"OS error reading contract file: {e}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )


__all__ = [
    "ServiceContractValidator",
    "ModelContractValidationResult",
]
