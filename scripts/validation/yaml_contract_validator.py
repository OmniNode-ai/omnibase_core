#!/usr/bin/env python3
"""
Standalone YAML Contract Validator.

Simple Pydantic model for validating YAML contract files without circular dependencies.
This model is designed specifically for the validation script to avoid import issues.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class SimpleNodeType:
    """Simple node type values for validation.

    Uses uppercase values aligned with EnumNodeType in omnibase_core.enums.enum_node_type.
    No legacy/deprecated lowercase values - clean break for v0.4.0+.
    """

    VALID_TYPES = {
        # Generic node types (one per EnumNodeKind)
        "COMPUTE_GENERIC",
        "EFFECT_GENERIC",
        "REDUCER_GENERIC",
        "ORCHESTRATOR_GENERIC",
        "RUNTIME_HOST_GENERIC",
        # Specific node implementation types
        "GATEWAY",
        "VALIDATOR",
        "TRANSFORMER",
        "AGGREGATOR",
        "FUNCTION",
        "TOOL",
        "AGENT",
        "MODEL",
        "PLUGIN",
        "SCHEMA",
        "NODE",
        "WORKFLOW",
        "SERVICE",
        "UNKNOWN",
    }


class SimpleContractVersion(BaseModel):
    """Simple contract version model."""

    major: int = Field(..., ge=0)
    minor: int = Field(..., ge=0)
    patch: int = Field(..., ge=0)


class SimpleYamlContract(BaseModel):
    """
    Simple YAML contract validation model without circular dependencies.

    This model provides validation for the minimum required fields in a YAML contract:
    - contract_version: Semantic version information
    - node_type: Node type classification
    """

    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for flexible contract formats
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Required fields for contract validation
    contract_version: SimpleContractVersion = Field(
        ...,
        description="Contract semantic version specification",
    )

    node_type: str = Field(
        ...,
        description="Node type classification",
    )

    # Optional fields commonly found in contracts
    description: str | None = Field(
        default=None,
        description="Human-readable contract description",
    )

    @field_validator("contract_version", mode="before")
    @classmethod
    def validate_contract_version(cls, value):
        """Accept both string and dict formats for contract_version."""
        if isinstance(value, str):
            # Try to parse semantic version string like "1.0.0"
            parts = value.split(".")
            if len(parts) == 3:
                try:
                    major, minor, patch = map(int, parts)
                    return {"major": major, "minor": minor, "patch": patch}
                except ValueError:
                    pass
            # If not a valid semver string, return a default
            return {"major": 1, "minor": 0, "patch": 0}
        return value

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, value: str) -> str:
        """Validate node_type field with simple validation.

        Validates against uppercase EnumNodeType values. No legacy lowercase
        values are accepted - this is a clean break for v0.4.0+.
        """
        if not isinstance(value, str):
            raise ValueError("node_type must be a string")

        value_upper = value.upper()
        if value_upper in SimpleNodeType.VALID_TYPES:
            return value_upper

        raise ValueError(
            f"Invalid node_type '{value}'. Must be one of: {', '.join(sorted(SimpleNodeType.VALID_TYPES))}"
        )

    @classmethod
    def validate_yaml_content(cls, yaml_data: dict[str, Any]) -> "SimpleYamlContract":
        """
        Validate YAML content using Pydantic model validation.

        Args:
            yaml_data: Dictionary loaded from YAML file

        Returns:
            SimpleYamlContract: Validated contract instance

        Raises:
            ValidationError: If validation fails
        """
        return cls.model_validate(yaml_data)
