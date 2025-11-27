# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.895826'
# description: Stamped by ToolPython
# entrypoint: python://model_context
# hash: 03dc8ca4c1f3c307d0f5182c59e9b9822af409c5cfdc63dc503b4173bdf8879e
# last_modified_at: '2025-05-29T14:13:58.757080+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_context.py
# namespace: python://omnibase.model.model_context
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 05a4c4aa-084e-4619-9048-18161ea7cd48
# version: 1.0.0
# === /OmniNode:Metadata ===


from pydantic import BaseModel, Field


class ModelContext(BaseModel):
    data: dict[str, str] = Field(default_factory=dict)
