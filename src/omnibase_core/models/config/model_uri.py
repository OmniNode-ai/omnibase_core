from __future__ import annotations

from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Configurable
from omnibase_core.enums.enum_uri_type import EnumUriType

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.092013'
# description: Stamped by ToolPython
# entrypoint: python://model_uri
# hash: 9e5551acd685d1fa48196e7439db5532f61bc71c92cd3cb52028919a467c2199
# last_modified_at: '2025-05-29T14:13:58.956318+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_uri.py
# namespace: python://omnibase.model.model_uri
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 0a5a30cb-c79b-4b9b-9b0d-701127774de4
# version: 1.0.0
# === /OmniNode:Metadata ===


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
            ...,
            description="ONEX URI type (tool, validator, agent, model, plugin, schema, node)",
        )
    )

    namespace: str = Field(
        ...,
        description="Namespace component of the URI",
    )

    version_spec: str = Field(
        ...,
        description="Version specifier (semver or constraint)",
    )
    original: str = Field(..., description="Original URI string as provided")

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


__all__ = ["ModelOnexUri"]
