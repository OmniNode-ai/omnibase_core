#!/usr/bin/env python3
"""
Standalone YAML Contract Validator.

Simple Pydantic model for validating YAML contract files without circular dependencies.
This model is designed specifically for the validation script to avoid import issues.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class SimpleNodeType:
    """Simple node type values for validation."""

    VALID_TYPES = {
        "compute",
        "gateway",
        "orchestrator",
        "reducer",
        "effect",
        "validator",
        "transformer",
        "aggregator",
        "function",
        "tool",
        "agent",
        "model",
        "plugin",
        "schema",
        "node",
        "workflow",
        "service",
        "compute_generic",
        "unknown",
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
        """Validate node_type field with simple validation."""
        if not isinstance(value, str):
            raise ValueError("node_type must be a string")

        value_lower = value.lower()
        if value_lower in SimpleNodeType.VALID_TYPES:
            return value_lower

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
