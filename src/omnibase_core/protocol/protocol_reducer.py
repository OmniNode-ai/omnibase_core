# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.265467'
# description: Stamped by ToolPython
# entrypoint: python://protocol_reducer
# hash: 7ff603ab91d1133ad6d436a666a68896cf286019e69b8e61508ead16f411626f
# last_modified_at: '2025-05-29T14:14:00.317784+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_reducer.py
# namespace: python://omnibase.protocol.protocol_reducer
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: d98cbd0f-43e9-455c-9706-a0b804aee580
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Protocol

from omnibase_core.models.core.model_reducer import ActionModel, ModelState


class ProtocolReducer(Protocol):
    """
    Protocol for ONEX reducers (state transition logic).

    Example:
        class MyReducer:
            def initial_state(self) -> ModelState:
                ...
            def dispatch(self, state: ModelState, action: ActionModel) -> ModelState:
                ...
    """

    def initial_state(self) -> ModelState: ...

    def dispatch(self, state: ModelState, action: ActionModel) -> ModelState: ...
