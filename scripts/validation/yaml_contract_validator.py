#!/usr/bin/env python3
"""
Standalone YAML Contract Validator.

Minimal Pydantic model for validating YAML contract files without circular dependencies.
This model is designed specifically for the validation script to avoid import issues.

Normalization Behavior
----------------------
This validator applies several normalizations to ensure consistent contract validation:

**node_type Normalization (Case-Insensitive)**:
    Input values are normalized to UPPERCASE for v0.4.0+ EnumNodeType compliance.
    Both "compute_generic" and "COMPUTE_GENERIC" are accepted and stored as "COMPUTE_GENERIC".

    Examples:
        "compute_generic" -> "COMPUTE_GENERIC"
        "Reducer_Generic" -> "REDUCER_GENERIC"
        "EFFECT"          -> "EFFECT" (shorthand accepted)

**contract_version Parsing**:
    Accepts both inline dict format and string format for flexibility.

    Dict format (preferred in YAML):
        contract_version: {major: 1, minor: 0, patch: 0}

    String format (also accepted):
        contract_version: "1.0.0"
        (Parsed to {"major": 1, "minor": 0, "patch": 0})

Supported node_type Values
--------------------------
**Shorthand types** (v0.4.0+ convenience aliases):
    COMPUTE, EFFECT, REDUCER, ORCHESTRATOR, RUNTIME_HOST

**Generic types** (canonical EnumNodeType values):
    COMPUTE_GENERIC, EFFECT_GENERIC, REDUCER_GENERIC,
    ORCHESTRATOR_GENERIC, RUNTIME_HOST_GENERIC

**Specific implementation types**:
    GATEWAY, VALIDATOR, TRANSFORMER, AGGREGATOR,
    FUNCTION, TOOL, AGENT, MODEL, PLUGIN, SCHEMA,
    NODE, WORKFLOW, SERVICE, UNKNOWN

Usage Example
-------------
    from yaml_contract_validator import MinimalYamlContract

    yaml_data = {
        "node_type": "compute_generic",  # Lowercase input
        "contract_version": {"major": 1, "minor": 0, "patch": 0}
    }

    contract = MinimalYamlContract.validate_yaml_content(yaml_data)
    print(contract.node_type)  # "COMPUTE_GENERIC" (normalized to uppercase)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MinimalNodeType:
    """Valid node_type values for YAML contract validation.

    Mirrors EnumNodeType uppercase values. Input is case-insensitive (v0.4.0+).

    Supports two forms of node type specification:
    1. Shorthand values: COMPUTE, EFFECT, REDUCER, ORCHESTRATOR, RUNTIME_HOST
       These are convenience shortcuts that map to the corresponding *_GENERIC variants.
    2. Full values: COMPUTE_GENERIC, EFFECT_GENERIC, etc.
       These are the canonical EnumNodeType values.

    Both forms are normalized to uppercase during validation.
    """

    VALID_TYPES = {
        # Shorthand node types (v0.4.0+ convenience aliases)
        # These map conceptually to the *_GENERIC variants
        "COMPUTE",
        "EFFECT",
        "REDUCER",
        "ORCHESTRATOR",
        "RUNTIME_HOST",
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


class MinimalContractVersion(BaseModel):
    """Semantic version model for contract_version field (major.minor.patch)."""

    major: int = Field(..., ge=0)
    minor: int = Field(..., ge=0)
    patch: int = Field(..., ge=0)


class MinimalYamlContract(BaseModel):
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
    contract_version: MinimalContractVersion = Field(
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
    def validate_contract_version(cls, value: Any) -> dict[str, int] | Any:
        """Accept both string and dict formats for contract_version.

        Normalization behavior:
            - Dict input: {major: 1, minor: 0, patch: 0} -> passed through
            - String input: "1.0.0" -> {"major": 1, "minor": 0, "patch": 0}
            - Invalid string: defaults to {"major": 1, "minor": 0, "patch": 0}

        Args:
            value: Either a dict with major/minor/patch keys, or a semver string.

        Returns:
            Dict with major, minor, patch integer keys.
        """
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

        Normalization behavior:
            - Lowercase input: "compute_generic" -> "COMPUTE_GENERIC"
            - Mixed case input: "Reducer_Generic" -> "REDUCER_GENERIC"
            - Uppercase input: "EFFECT_GENERIC" -> "EFFECT_GENERIC" (unchanged)
            - Shorthand aliases: "compute" -> "COMPUTE" (accepted as-is)

        This normalization ensures v0.4.0+ compliance with EnumNodeType values,
        which are defined as UPPERCASE constants.

        Args:
            value: The node_type string (any case accepted).

        Returns:
            The normalized UPPERCASE node_type string.

        Raises:
            ValueError: If node_type is not a string or not a valid type.
        """
        if not isinstance(value, str):
            raise ValueError("node_type must be a string")

        value_upper = value.upper()
        if value_upper in MinimalNodeType.VALID_TYPES:
            return value_upper

        raise ValueError(
            f"Invalid node_type '{value}'. Must be one of: {', '.join(sorted(MinimalNodeType.VALID_TYPES))}"
        )

    @classmethod
    def validate_yaml_content(cls, yaml_data: dict[str, Any]) -> "MinimalYamlContract":
        """Validate YAML dict and return validated contract.

        This method applies all normalization rules:
            - node_type: Normalized to UPPERCASE
            - contract_version: String format parsed to dict

        Args:
            yaml_data: Dictionary loaded from YAML file.

        Returns:
            Validated MinimalYamlContract with normalized values.

        Raises:
            ValidationError: If required fields are missing or invalid.
        """
        return cls.model_validate(yaml_data)
