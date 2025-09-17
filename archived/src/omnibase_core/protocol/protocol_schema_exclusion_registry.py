# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.285867'
# description: Stamped by ToolPython
# entrypoint: python://protocol_schema_exclusion_registry
# hash: 6de00a870345f5bd5613164dd62faf762951cc9d78c202e738edf4853a81eac0
# last_modified_at: '2025-05-29T14:14:00.331701+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_schema_exclusion_registry.py
# namespace: python://omnibase.protocol.protocol_schema_exclusion_registry
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 86967029-e106-4d65-9bd8-3f6e3614de44
# version: 1.0.0
# === /OmniNode:Metadata ===


from pathlib import Path
from typing import Protocol


class ProtocolSchemaExclusionRegistry(Protocol):
    """
    Canonical protocol for schema exclusion registries shared across nodes.
    Placed in runtime/ per OmniNode Runtime Structure Guidelines: use runtime/ for execution-layer components reused by multiple nodes.
    All schema exclusion logic must conform to this interface.
    """

    def is_schema_file(self, path: Path) -> bool:
        """Return True if the given path is a schema file to be excluded, else False."""
        ...
