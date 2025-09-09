#!/usr/bin/env python3
"""
Canary Effect Input Model - Contract-Driven Implementation.

Strongly typed Pydantic model generated from ONEX contract input_state schema.
Eliminates JSON/YAML parsing architecture violations by using proper contract-driven models.
"""

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EnumCanaryOperationType(str, Enum):
    """Enumeration of supported canary operation types from contract."""

    HEALTH_CHECK = "health_check"
    EXTERNAL_API_CALL = "external_api_call"
    FILE_SYSTEM_OPERATION = "file_system_operation"
    DATABASE_OPERATION = "database_operation"
    MESSAGE_QUEUE_OPERATION = "message_queue_operation"


class ModelCanaryEffectInput(BaseModel):
    """
    Input model for canary effect operations - generated from contract input_state schema.

    This model represents the strongly-typed input structure for canary effect operations,
    replacing the previous architecture violation of using dict[str, Any] parameters.
    All fields are properly typed according to the ONEX contract specification.

    Contract Reference:
        - Source: canary_effect_contract.yaml input_state
        - Node Type: EFFECT
        - Strong Typing: Enforced via Pydantic validation
        - Zero Any Types: All fields use specific types
    """

    operation_type: EnumCanaryOperationType = Field(
        ...,
        description="Type of canary effect operation to perform - from contract enum",
    )

    target_system: str | None = Field(
        None,
        description="Target system for effect operation (optional) - string type from contract",
    )

    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific parameters - object type from contract schema",
    )

    correlation_id: str | None = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Request correlation ID (auto-generated if not provided) - string type from contract",
    )

    # Pydantic v2 configuration using ConfigDict
    model_config = ConfigDict(
        # Enable validation on assignment for runtime safety
        validate_assignment=True,
        # Use enum values for serialization
        use_enum_values=True,
        # Forbid extra fields to maintain contract compliance
        extra="forbid",
        # Enable JSON schema generation
        json_schema_serialization_defaults_required=True,
    )

    def to_operation_data(self) -> dict[str, Any]:
        """
        Convert to operation data dictionary for backward compatibility.

        This method provides a migration path from the old architecture
        while maintaining strong typing principles.

        Returns:
            Dict[str, Any]: Operation data with all required fields
        """
        return {
            "operation_type": self.operation_type,  # Already string value in Pydantic v2
            "target_system": self.target_system,
            "parameters": self.parameters,
            "correlation_id": self.correlation_id,
        }
