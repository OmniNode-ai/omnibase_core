# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.193906'
# description: Stamped by ToolPython
# entrypoint: python://protocol_tool
# hash: 544c8e092f824a48bf5f1f6219080eed3abe7ac5c4702d03f55a9c9790a5865c
# last_modified_at: '2025-05-29T14:14:00.381214+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_tool.py
# namespace: python://omnibase.protocol.protocol_tool
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: e8651074-b687-485a-a38e-233f05375ce0
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Protocol

from omnibase_core.models.core.model_result_cli import ModelResultCLI
from omnibase_core.protocol.models.model_tool_arguments import ModelToolArguments
from omnibase_core.protocol.models.model_tool_input_data import ModelToolInputData


class ProtocolTool(Protocol):
    """
    Protocol for CLI scripts that can modify files. Adds --apply flag, defaults to dry-run, and enforces safety messaging.
    All file-modifying logic must be gated behind --apply. Dry-run is always the default.

    Example:
        class MyTool(ProtocolTool):
            def dry_run_main(self, args) -> ModelResultCLI:
                ...
            def apply_main(self, args) -> ModelResultCLI:
                ...
            def execute(self, input_data: dict) -> ModelResultCLI:
                ...
    """

    def dry_run_main(self, args: ModelToolArguments) -> ModelResultCLI: ...

    def apply_main(self, args: ModelToolArguments) -> ModelResultCLI: ...

    def execute(self, input_data: ModelToolInputData) -> ModelResultCLI: ...
