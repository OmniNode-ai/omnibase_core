# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.183974'
# description: Stamped by ToolPython
# entrypoint: python://protocol_testable_registry
# hash: 0182ad7c3dc4c9a5debce86600d4650a88ea3be52c8514d932e8a6b65f0b1dac
# last_modified_at: '2025-05-29T14:14:00.367349+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_testable_registry.py
# namespace: python://omnibase.protocol.protocol_testable_registry
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: cea78984-9110-4bb6-8b2d-c208afa539b1
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
ProtocolTestableRegistry: Protocol for all testable ONEX registry interfaces.
Extends ProtocolTestable. Used for registry-driven tests and swappable registry fixtures.
"""

from typing import Any, Protocol, runtime_checkable

from omnibase_core.protocol.protocol_testable import ProtocolTestable


@runtime_checkable
class ProtocolTestableRegistry(ProtocolTestable, Protocol):
    """
    Protocol for testable ONEX registries (mock/real).
    Used for registry-driven tests and fixtures.
    """

    @classmethod
    def load_from_disk(cls) -> "ProtocolTestableRegistry": ...

    @classmethod
    def load_mock(cls) -> "ProtocolTestableRegistry": ...

    def get_node(self, node_id: str) -> dict[str, Any]: ...
