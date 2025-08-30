# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.223369'
# description: Stamped by ToolPython
# entrypoint: python://protocol_node_runner
# hash: 02bfe2970d781cfdf2e19d5b4d350f851a92d1ad8306dcefac0e00c6f3b4559a
# last_modified_at: '2025-05-29T14:14:00.290273+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_node_runner.py
# namespace: python://omnibase.protocol.protocol_node_runner
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 8ac235b7-27e0-4431-9cae-789ee1996d0d
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Any, Protocol


class ProtocolNodeRunner(Protocol):
    """
    Canonical protocol for ONEX node runners (runtime/ placement).
    Requires a run(*args, **kwargs) -> Any method for node execution and event emission.
    All node runner implementations must conform to this interface.
    """

    def run(self, *args: Any, **kwargs: Any) -> Any: ...
