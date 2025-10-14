"""
Contract Validation API for Autonomous Code Generation.

Provides programmatic contract validation against ONEX standards with:
- YAML contract validation against locked-down models
- Model code compliance checking
- Scoring based on completeness and correctness
- Actionable error messages for code generation

VERSION: 1.0.0 - Interface locked for autonomous code generation
"""

import ast
import re
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, Field, ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.metadata.model_semver import ModelSemVer


class ProtocolContractValidationResult(BaseModel):
    """
    Validation result with scoring and actionable feedback.

    Attributes:
        is_valid: Whether the contract passes all validation checks
        score: Validation score from 0.0 to 1.0
        violations: Critical errors that prevent validation
        warnings: Non-critical issues that should be addressed
        suggestions: Recommendations for improvement
        contract_type: Type of contract validated (effect, compute, etc.)
        interface_version: INTERFACE_VERSION used for validation
    """

    is_valid: bool = Field(
        ...,
        description="Whether the contract passes all validation checks",
    )

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Validation score from 0.0 to 1.0",
    )

    violations: list[str] = Field(
        default_factory=list,
        description="Critical errors that prevent validation",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Non-critical issues that should be addressed",
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="Recommendations for improvement",
    )

    contract_type: str | None = Field(
        default=None,
        description="Type of contract validated",
    )

    interface_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="INTERFACE_VERSION used for validation",
    )


class ProtocolContractValidator:
    """
    Programmatic contract validation for autonomous code generation.

    Validates YAML contracts and model code against ONEX standards:
    - Uses locked-down contract models (INTERFACE_VERSION 1.0.0)
    - Checks required fields, types, and naming conventions
    - Provides actionable error messages
    - Scores based on completeness and correctness
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

    def __init__(self) -> None:
        """Initialize the contract validator."""
        self.interface_version = ModelSemVer(major=1, minor=0, patch=0)

    def validate_contract_yaml(
        self,
        contract_content: str,
        contract_type: Literal[
            "effect", "compute", "reducer", "orchestrator"
        ] = "effect",
    ) -> ProtocolContractValidationResult:
        """
        Validate a YAML contract against ONEX standards.

        Args:
            contract_content: YAML contract content as string
            contract_type: Type of contract to validate against

        Returns:
            ProtocolContractValidationResult with validation details and scoring
        """
        violations: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []
        score = 1.0

        # Step 1: Parse YAML content
        try:
            yaml_data = yaml.safe_load(
                contract_content
            )  # yaml-ok: Contract validation requires raw YAML parsing for flexible schema checking
            if yaml_data is None:
                return ProtocolContractValidationResult(
                    is_valid=False,
                    score=0.0,
                    violations=["Empty YAML content"],
                    contract_type=contract_type,
                    interface_version=self.interface_version,
                )

            # Pre-process node_type to ensure proper enum conversion
            # yaml-ok: Contract validation requires manual YAML preprocessing for enum conversion
            if "node_type" in yaml_data and isinstance(
                yaml_data["node_type"], str
            ):  # yaml-ok: manual field check required for preprocessing
                try:
                    # Convert string to EnumNodeType for proper validation
                    node_type_str = yaml_data[
                        "node_type"
                    ].upper()  # yaml-ok: field access for enum conversion
                    yaml_data["node_type"] = EnumNodeType[
                        node_type_str
                    ]  # yaml-ok: field mutation for validation
                except (KeyError, AttributeError):
                    # Keep as string if conversion fails - let Pydantic validation handle it
                    yaml_data["node_type"] = yaml_data[
                        "node_type"
                    ].upper()  # yaml-ok: fallback field mutation

            # Pre-process version field to ensure ModelSemVer conversion
            if "version" in yaml_data and isinstance(yaml_data["version"], dict):
                try:
                    yaml_data["version"] = ModelSemVer(**yaml_data["version"])
                except Exception:
                    # Keep as dict if conversion fails - let Pydantic validation handle it
                    pass

        except yaml.YAMLError as e:
            return ProtocolContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"YAML parsing error: {e}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )

        # Step 2: Validate against contract schema
        contract_model = self.CONTRACT_MODELS.get(contract_type)
        if not contract_model:
            return ProtocolContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Unknown contract type: {contract_type}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )

        try:
            # Validate using Pydantic model
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
                score -= 0.1

            # Add suggestions based on common errors
            self._add_suggestions_for_errors(e, suggestions)

        except OnexError as e:
            violations.append(f"ONEX validation error: {e.message}")
            score -= 0.2

        except Exception as e:
            violations.append(f"Unexpected validation error: {e}")
            score = 0.0

        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))

        return ProtocolContractValidationResult(
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
    ) -> ProtocolContractValidationResult:
        """
        Validate Pydantic model code against a contract.

        Args:
            model_code: Python code containing Pydantic model definition
            contract_yaml: YAML contract content as string

        Returns:
            ProtocolContractValidationResult with compliance details
        """
        violations: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []
        score = 1.0

        # Step 1: Parse YAML contract
        try:
            yaml_data = yaml.safe_load(
                contract_yaml
            )  # yaml-ok: Contract validation requires raw YAML parsing for flexible schema checking
            if yaml_data is None:
                return ProtocolContractValidationResult(
                    is_valid=False,
                    score=0.0,
                    violations=["Empty contract YAML"],
                    interface_version=self.interface_version,
                )
        except yaml.YAMLError as e:
            return ProtocolContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Contract YAML parsing error: {e}"],
                interface_version=self.interface_version,
            )

        # Step 2: Parse model code using AST
        try:
            tree = ast.parse(model_code)
        except SyntaxError as e:
            return ProtocolContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Python syntax error: {e}"],
                interface_version=self.interface_version,
            )

        # Step 3: Extract model definitions
        model_classes = self._extract_model_classes(tree)
        if not model_classes:
            violations.append("No Pydantic model classes found in code")
            score -= 0.3

        # Step 4: Validate model against contract
        contract_name = yaml_data.get("name", "")
        input_model = yaml_data.get("input_model", "")
        output_model = yaml_data.get("output_model", "")

        # Check input/output models exist
        if input_model:
            model_name = input_model.split(".")[-1]
            if not any(cls["name"] == model_name for cls in model_classes):
                violations.append(f"Input model '{model_name}' not found in code")
                score -= 0.2
            else:
                suggestions.append(
                    f"Input model '{model_name}' found - verify fields match contract"
                )

        if output_model:
            model_name = output_model.split(".")[-1]
            if not any(cls["name"] == model_name for cls in model_classes):
                violations.append(f"Output model '{model_name}' not found in code")
                score -= 0.2
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
            0.0, min(1.0, score - (len(violations) * 0.15) - (len(warnings) * 0.05))
        )

        return ProtocolContractValidationResult(
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
        # Check interface version
        if contract.INTERFACE_VERSION != self.interface_version:
            warnings.append(
                f"Interface version mismatch: expected {self.interface_version}, "
                f"got {contract.INTERFACE_VERSION}"
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
        elif len(contract.description) < 10:
            warnings.append(
                "Contract description is too short (minimum 10 characters recommended)"
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
        violation_penalty = len(violations) * 0.2

        # Each warning reduces score slightly
        warning_penalty = len(warnings) * 0.05

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

    def _extract_model_classes(self, tree: ast.AST) -> list[dict[str, Any]]:
        """Extract Pydantic model class definitions from AST."""
        model_classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a BaseModel subclass
                for base in node.bases:
                    if isinstance(base, ast.Name) and "BaseModel" in base.id:
                        # Extract fields
                        fields = []
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
                                fields.append({"name": field_name, "type": field_type})

                        model_classes.append(
                            {
                                "name": node.name,
                                "fields": fields,
                                "bases": [ast.unparse(b) for b in node.bases],
                            }
                        )
                        break

        return model_classes

    def _validate_model_fields(
        self,
        model_class: dict[str, Any],
        contract_data: dict[str, Any],
        violations: list[str],
        warnings: list[str],
        suggestions: list[str],
    ) -> None:
        """Validate model fields against contract specifications."""
        model_name = model_class["name"]
        fields = cast(list[dict[str, Any]], model_class.get("fields", []))

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
        model_classes: list[dict[str, Any]],
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

    def validate_contract_file(
        self,
        file_path: str | Path,
        contract_type: Literal[
            "effect", "compute", "reducer", "orchestrator"
        ] = "effect",
    ) -> ProtocolContractValidationResult:
        """
        Validate a YAML contract file.

        Args:
            file_path: Path to YAML contract file
            contract_type: Type of contract to validate against

        Returns:
            ProtocolContractValidationResult with validation details
        """
        path = Path(file_path)

        if not path.exists():
            return ProtocolContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Contract file not found: {file_path}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )

        try:
            content = path.read_text()
            return self.validate_contract_yaml(content, contract_type)
        except (
            Exception
        ) as e:  # fallback-ok: Contract validation collects errors for batch reporting instead of failing fast
            return ProtocolContractValidationResult(
                is_valid=False,
                score=0.0,
                violations=[f"Error reading contract file: {e}"],
                contract_type=contract_type,
                interface_version=self.interface_version,
            )


__all__ = [
    "ProtocolContractValidator",
    "ProtocolContractValidationResult",
]
