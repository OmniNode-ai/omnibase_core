# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.930335'
# description: Stamped by ToolPython
# entrypoint: python://model_file_reference
# hash: 45e3a6e89d1c86eac33beb44addcce07acfcfe4f2ed2ddcb9fb034b259341fb4
# last_modified_at: '2025-05-29T14:13:58.777429+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_file_reference.py
# namespace: python://omnibase.model.model_file_reference
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: a6123e65-a025-4a18-a21b-1d5675103033
# version: 1.0.0
# === /OmniNode:Metadata ===


from pydantic import BaseModel


class ModelFileReference(BaseModel):
    path: str  # Use str for now; can be changed to Path if needed
    description: str | None = None
