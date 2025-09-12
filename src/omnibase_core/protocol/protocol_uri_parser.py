# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.203337'
# description: Stamped by ToolPython
# entrypoint: python://protocol_uri_parser
# hash: c24737fb15bc7f2f8c57ee3d7a3dc96f16424f7a3fc0e8b179a974c398a1959d
# last_modified_at: '2025-05-29T14:14:00.388288+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_uri_parser.py
# namespace: python://omnibase.protocol.protocol_uri_parser
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: b9a2444a-2347-44e1-853b-35ff2037b9b3
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Protocol

from omnibase_core.models.core.model_uri import ModelOnexUri


class ProtocolUriParser(Protocol):
    """
    Protocol for ONEX URI parser utilities.
    All implementations must provide a parse method that returns an ModelOnexUri.

    Example:
        class MyUriParser(ProtocolUriParser):
            def parse(self, uri_string: str) -> ModelOnexUri:
                ...
    """

    def parse(self, uri_string: str) -> ModelOnexUri:
        """Parse a canonical ONEX URI string and return an ModelOnexUri."""
        ...
