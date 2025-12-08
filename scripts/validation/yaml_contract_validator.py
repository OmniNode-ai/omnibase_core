#!/usr/bin/env python3
"""
Standalone YAML Contract Validator.

Simple Pydantic model for validating YAML contract files without circular dependencies.
This model is designed specifically for the validation script to avoid import issues.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class SimpleNodeType:
    """Valid node_type values for YAML contract validation.

    Mirrors EnumNodeType uppercase values. Input is case-insensitive (v0.4.0+).
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
    """Semantic version model for contract_version field (major.minor.patch)."""

    major: int = Field(..., ge=0)
    minor: int = Field(..., ge=0)
    patch: int = Field(..., ge=0)


class SimpleYamlContract(BaseModel):
    """Pydantic model for validating YAML contracts without circular imports.

    Validates required fields: contract_version and node_type.
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
        """Validate node_type field with case-insensitive normalization.

        Accepts both uppercase and lowercase input, normalizes to uppercase
        for v0.4.0+ compliance with EnumNodeType values.
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
        """Validate YAML dict and return validated contract. Raises ValidationError on failure."""
        return cls.model_validate(yaml_data)
