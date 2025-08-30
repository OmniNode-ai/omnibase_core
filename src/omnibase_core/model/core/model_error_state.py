"""
Error state model for defining error responses in ONEX contracts.
"""

from pydantic import BaseModel, Field

from .model_generic_properties import ModelGenericProperties


class ModelErrorState(BaseModel):
    """
    Model for error state definitions in contracts.

    Defines the structure of error responses from nodes.
    """

    type: str = Field(
        default="object",
        description="Type of the error state",
        json_schema_extra={"example": "object"},
    )

    properties: ModelGenericProperties | None = Field(
        default=None,
        description="Properties of the error state",
        json_schema_extra={
            "example": {
                "error_code": {
                    "type": "string",
                    "enum": ["INVALID_INPUT", "EXECUTION_FAILED"],
                },
                "error_message": {"type": "string"},
                "details": {"type": "object"},
            },
        },
    )
