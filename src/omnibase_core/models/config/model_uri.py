from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from omnibase_core.primitives.model_semver import ModelSemVer


class ModelOnexUri(BaseModel):
    """
    Canonical Pydantic model for ONEX URIs.
    See docs/nodes/node_contracts.md and docs/nodes/structural_conventions.md for spec.
    Implements omnibase_spi protocols:
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
    version_spec: ModelSemVer = Field(
        default=..., description="Version specifier (semver or constraint)"
    )
    original: str = Field(default=..., description="Original URI string as provided")

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
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
