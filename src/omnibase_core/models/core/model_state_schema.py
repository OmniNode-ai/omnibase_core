"""
State schema model for input/output state definitions in ONEX contracts.
"""

from pydantic import BaseModel, Field

from .model_generic_properties import ModelGenericProperties


class ModelStateSchema(BaseModel):
    """
    Model for input/output state schema definitions.

    This defines the structure of input_state and output_state sections
    in the contract file.
    """

    type: str = Field(
        default=...,
        description="Type name of the state model (e.g., 'CLIInputState')",
        json_schema_extra={"example": "CLIInputState"},
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of this state",
        json_schema_extra={"example": "Input state for CLI command execution"},
    )

    required_fields: list[str] | None = Field(
        default=None,
        description="List of required field names",
        json_schema_extra={"example": ["version", "command"]},
    )

    optional_fields: list[str] | None = Field(
        default=None,
        description="List of optional field names",
        json_schema_extra={"example": ["target_node", "args"]},
    )

    properties: ModelGenericProperties | None = Field(
        default=None,
        description="JSON Schema properties definition",
        json_schema_extra={
            "example": {
                "version": {"type": "string", "description": "Schema version"},
                "command": {"type": "string", "description": "Command to execute"},
            },
        },
    )

    required: list[str] | None = Field(
        default=None,
        description="JSON Schema required fields (alternative to required_fields)",
        json_schema_extra={"example": ["version", "command"]},
    )
