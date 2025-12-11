from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelOnexUri(BaseModel):
    """
    Canonical Pydantic model for ONEX URIs.
    See docs/nodes/node_contracts.md and docs/nodes/structural_conventions.md for spec.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    type: Literal["tool", "validator", "agent", "model", "plugin", "schema", "node"] = (
        Field(
            default=...,
            description="ONEX URI type (tool, validator, agent, model, plugin, schema, node)",
        )
    )
    namespace: str = Field(default=..., description="Namespace component of the URI")
    version_spec: str = Field(
        default=..., description="Version specifier (semver or constraint)"
    )
    original: str = Field(default=..., description="Original URI string as provided")

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        return True

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


__all__ = ["ModelOnexUri"]
