# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.174119'
# description: Stamped by ToolPython
# entrypoint: python://protocol_testable_cli
# hash: d2c868106db8b10731f4f29dffa3252e28d5eeb9f3fd81e15ad2a50586b3a595
# last_modified_at: '2025-05-29T14:14:00.360192+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_testable_cli.py
# namespace: python://omnibase.protocol.protocol_testable_cli
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 890bf413-c5aa-4a85-89b2-3a53892d7830
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
ProtocolTestableCLI: Protocol for all testable CLI entrypoints. Requires main(argv) -> ModelResultCLI.
"""

from typing import Protocol

from omnibase_core.models.core.model_result_cli import ModelResultCLI


class ProtocolTestableCLI(Protocol):
    """
    Protocol for all testable CLI entrypoints. Requires main(argv) -> ModelResultCLI.

    Example:
        class MyTestableCLI(ProtocolTestableCLI):
            def main(self, argv: List[str]) -> ModelResultCLI:
                ...
    """

    def main(self, argv: list[str]) -> ModelResultCLI: ...
