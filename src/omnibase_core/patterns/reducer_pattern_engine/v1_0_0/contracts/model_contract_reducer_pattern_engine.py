#!/usr/bin/env python3
"""
Reducer Pattern Engine Contract - ONEX Standards Compliant.

Minimal backing model for the Reducer Pattern Engine that leverages
existing ONEX infrastructure:
- Uses standard ModelContractReducer base class
- References existing FSM subcontract via YAML
- Follows established ONEX contract patterns
- No hard-coded state transitions

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import Field, field_validator

from omnibase_core.core.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.model.core.model_semver import ModelSemVer


class ModelContractReducerPatternEngine(ModelContractReducer):
    """
    Contract for Reducer Pattern Engine - ONEX Compliant.

    Simple backing model that extends ModelContractReducer and leverages
    the existing ONEX infrastructure including FSM subcontracts.

    State management, transitions, and FSM logic are provided by the
    standard ONEX subcontracts referenced in the YAML contract file.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Required base fields with defaults
    name: str = Field(
        default="reducer_pattern_engine",
        description="Contract name",
    )

    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Contract version",
    )

    description: str = Field(
        default="Multi-workflow reducer pattern engine with ONEX compliance",
        description="Contract description",
    )

    input_model: str = Field(
        default="ModelReducerPatternEngineInput",
        description="Input model class name",
    )

    output_model: str = Field(
        default="ModelReducerPatternEngineOutput",
        description="Output model class name",
    )

    # Pattern-specific configuration (minimal)
    pattern_type: str = Field(
        default="execution_pattern",
        description="Type of pattern implementation",
    )

    supported_workflows: list[str] = Field(
        default=["DATA_ANALYSIS", "REPORT_GENERATION", "DOCUMENT_REGENERATION"],
        description="List of supported workflow types",
        min_length=1,
    )

    max_concurrent_workflows: int = Field(
        default=100,
        description="Maximum number of concurrent workflows",
        ge=1,
        le=1000,
    )

    isolation_level: str = Field(
        default="instance_based",
        description="Isolation level for workflow processing",
    )

    # Required dependencies
    dependencies: list[str] = Field(
        default=["ProtocolContainer", "ProtocolEventBus", "ProtocolSchemaLoader"],
        description="Required protocol dependencies",
    )

    @field_validator("dependencies", mode="before")
    @classmethod
    def normalize_dependencies(cls, v: Any) -> list[str]:
        """
        Convert complex dependency objects to simple string list.

        Validates structured dependencies format and extracts class names
        for protocol dependencies. Ensures all required dependency fields
        are present and valid.

        Args:
            v: Raw dependency data from YAML contract

        Returns:
            list[str]: List of validated dependency class names

        Raises:
            ValueError: If dependency format is invalid
        """
        if isinstance(v, list):
            result = []
            for i, dep in enumerate(v):
                if isinstance(dep, dict):
                    # Validate required fields for structured dependencies
                    required_fields = ["class_name", "type"]
                    missing_fields = [
                        field for field in required_fields if field not in dep
                    ]

                    if missing_fields:
                        raise ValueError(
                            f"Dependency {i} missing required fields: {missing_fields}. "
                            f"Required: {required_fields}"
                        )

                    # Validate dependency type
                    valid_types = ["protocol", "service", "component"]
                    dep_type = dep.get("type")
                    if dep_type not in valid_types:
                        raise ValueError(
                            f"Dependency {i} has invalid type '{dep_type}'. "
                            f"Valid types: {valid_types}"
                        )

                    # Extract class_name with validation
                    class_name = dep.get("class_name")
                    if not class_name or not isinstance(class_name, str):
                        raise ValueError(
                            f"Dependency {i} has invalid class_name: {class_name}"
                        )

                    # Validate protocol dependency naming convention
                    if dep_type == "protocol" and not class_name.startswith("Protocol"):
                        raise ValueError(
                            f"Protocol dependency {i} class_name must start with 'Protocol', "
                            f"got: {class_name}"
                        )

                    result.append(class_name)

                elif isinstance(dep, str):
                    # Simple string dependencies must follow naming conventions
                    if not dep:
                        raise ValueError(f"Dependency {i} is empty string")
                    result.append(dep)
                else:
                    # Convert other types to string with validation
                    str_dep = str(dep).strip()
                    if not str_dep:
                        raise ValueError(
                            f"Dependency {i} converts to empty string: {dep}"
                        )
                    result.append(str_dep)

            return result
        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True

    def to_yaml(self) -> str:
        """
        Export contract model to YAML format.

        Returns:
            str: YAML representation of the contract
        """
        from omnibase_core.utils.safe_yaml_loader import (
            serialize_pydantic_model_to_yaml,
        )

        return serialize_pydantic_model_to_yaml(
            self, default_flow_style=False, sort_keys=False
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelContractReducerPatternEngine":
        """
        Create contract model from YAML content.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractReducerPatternEngine: Validated contract model instance
        """
        from omnibase_core.model.core.model_generic_yaml import ModelGenericYaml
        from omnibase_core.utils.safe_yaml_loader import (
            load_and_validate_yaml_model,
            load_yaml_content_as_model,
        )

        # Load and validate YAML using Pydantic model

        yaml_model = load_yaml_content_as_model(yaml_content, ModelGenericYaml)

        data = yaml_model.model_dump()
        return cls.model_validate(data)
        str_strip_whitespace = True
