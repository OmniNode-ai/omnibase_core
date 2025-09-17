# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.212774'
# description: Stamped by ToolPython
# entrypoint: python://protocol_node_cli_adapter
# hash: 7be0d74a66e027be62d464bfa5414f629bc5419a431d39a2c29843002c3f00aa
# last_modified_at: '2025-05-29T14:14:00.283432+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_node_cli_adapter.py
# namespace: python://omnibase.protocol.protocol_node_cli_adapter
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: e1f3e769-a996-476e-a659-34ec8a77dee2
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Any, Protocol


class ProtocolNodeCliAdapter(Protocol):
    """
    Protocol for ONEX node CLI adapters. Converts CLI args to node input state.
    Implementations must provide a method to parse CLI args (list[str] or argparse.Namespace)
    and return the node's input state (e.g., StamperInputState).
    """

    def parse_cli_args(self, cli_args: list[str]) -> Any: ...
