"""
Request-Response Configuration Model.

Top-level configuration model for request-response communication patterns
within the ONEX event bus. Contains a list of request-response instance
definitions that specify individual request-response pattern configurations.

This model will be composed into ModelEventBusSubcontract to enable
declarative request-response pattern configuration in node contracts.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

__all__ = ["ModelRequestResponseConfig"]

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.contracts.subcontracts.model_request_response_instance import (
    ModelRequestResponseInstance,
)


class ModelRequestResponseConfig(BaseModel):
    """
    Top-level configuration for request-response patterns.

    Wraps a list of ModelRequestResponseInstance definitions that each specify
    a complete request-response pattern configuration including request topic,
    reply topics, timeout settings, and other pattern-specific options.

    The instances list must contain at least one instance - empty configurations
    are rejected to prevent silent no-op behavior.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    instances: list[ModelRequestResponseInstance] = Field(
        ...,
        description="List of request-response pattern definitions (must not be empty)",
    )

    @model_validator(mode="after")
    def validate_non_empty_instances(self) -> ModelRequestResponseConfig:
        """Validate that instances list is not empty."""
        if not self.instances:
            raise ValueError(
                "request_response.instances must contain at least one instance"
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts for forward compatibility
        frozen=True,
        from_attributes=True,
    )
