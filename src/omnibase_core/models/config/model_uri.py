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

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelOnexUri(BaseModel):
    """
    Canonical Pydantic model for ONEX URIs.
    See docs/nodes/node_contracts.md and docs/nodes/structural_conventions.md for spec.
    """

    type: Literal["tool", "validator", "agent", "model", "plugin", "schema", "node"] = (
        Field(
            ...,
            description="ONEX URI type (tool, validator, agent, model, plugin, schema, node)",
        )
    )

    # Entity reference - UUID-based with display name
    namespace_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the namespace entity"
    )
    namespace_display_name: str | None = Field(
        None, description="Human-readable namespace component of the URI"
    )

    version_spec: str = Field(
        ...,
        description="Version specifier (semver or constraint)",
    )
    original: str = Field(..., description="Original URI string as provided")

    @classmethod
    def create_legacy(
        cls,
        type_value: Literal[
            "tool", "validator", "agent", "model", "plugin", "schema", "node"
        ],
        namespace: str,
        version_spec: str,
        original: str,
    ) -> ModelOnexUri:
        """Create URI with legacy namespace string for backward compatibility."""
        import hashlib

        # Generate UUID from namespace
        namespace_hash = hashlib.sha256(namespace.encode()).hexdigest()
        namespace_id = UUID(
            f"{namespace_hash[:8]}-{namespace_hash[8:12]}-{namespace_hash[12:16]}-{namespace_hash[16:20]}-{namespace_hash[20:32]}"
        )

        return cls(
            type=type_value,
            namespace_id=namespace_id,
            namespace_display_name=namespace,
            version_spec=version_spec,
            original=original,
        )

    @property
    def namespace(self) -> str:
        """Legacy property for backward compatibility."""
        return self.namespace_display_name or f"namespace_{str(self.namespace_id)[:8]}"

    @property
    def namespace_name(self) -> str:
        """Backward compatibility property for namespace_name."""
        return self.namespace_display_name or f"namespace_{str(self.namespace_id)[:8]}"

    @namespace_name.setter
    def namespace_name(self, value: str) -> None:
        """Backward compatibility setter for namespace_name."""
        import hashlib

        namespace_hash = hashlib.sha256(value.encode()).hexdigest()
        self.namespace_id = UUID(
            f"{namespace_hash[:8]}-{namespace_hash[8:12]}-{namespace_hash[12:16]}-{namespace_hash[16:20]}-{namespace_hash[20:32]}"
        )
        self.namespace_display_name = value
