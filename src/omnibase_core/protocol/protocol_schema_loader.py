# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.142263'
# description: Stamped by ToolPython
# entrypoint: python://protocol_schema_loader
# hash: 54d22bb99ec2490ef26d82ee55400b98fa3774a1cf59e9e600ee05023501e133
# last_modified_at: '2025-05-29T14:14:00.338636+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_schema_loader.py
# namespace: python://omnibase.protocol.protocol_schema_loader
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 5563978b-75f9-4c23-bca7-70ba09837d66
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
ProtocolSchemaLoader: Protocol for all ONEX schema loader implementations.
Defines the canonical loader interface for node metadata and JSON schema files.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from omnibase_core.model.core.model_node_metadata import NodeMetadataBlock

from omnibase_core.model.validation.model_schema import SchemaModel


class ProtocolSchemaLoader(Protocol):
    """
    Protocol for ONEX schema loaders.
    All methods use Path objects and return strongly-typed models as appropriate.
    """

    def load_onex_yaml(self, path: Path) -> "NodeMetadataBlock": ...

    def load_json_schema(self, path: Path) -> SchemaModel: ...

    def load_schema_for_node(self, node: "NodeMetadataBlock") -> SchemaModel: ...
