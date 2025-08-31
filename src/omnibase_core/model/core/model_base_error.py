# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.861191'
# description: Stamped by ToolPython
# entrypoint: python://model_base_error
# hash: b28a21c05057363545eff1b6cb4199981b3d181dbda3948f9ea68c3a8a8471e0
# last_modified_at: '2025-05-29T14:13:58.733989+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_base_error.py
# namespace: python://omnibase.model.model_base_error
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 5e943eab-c472-4cbf-a60b-d241b744b017
# version: 1.0.0
# === /OmniNode:Metadata ===


from pydantic import BaseModel


class ModelBaseError(BaseModel):
    message: str
    code: str = "unknown"
    details: str = ""
