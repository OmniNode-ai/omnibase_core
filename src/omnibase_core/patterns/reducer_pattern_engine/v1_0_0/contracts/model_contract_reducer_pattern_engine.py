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

    version: str = Field(
        default="1.0.0",
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
        """Convert complex dependency objects to simple string list."""
        if isinstance(v, list):
            result = []
            for dep in v:
                if isinstance(dep, dict):
                    # Extract class_name from dependency object
                    class_name = dep.get("class_name", dep.get("name", str(dep)))
                    result.append(class_name)
                elif isinstance(dep, str):
                    result.append(dep)
                else:
                    result.append(str(dep))
            return result
        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
        str_strip_whitespace = True
