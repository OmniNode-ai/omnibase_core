# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.975262'
# description: Stamped by ToolPython
# entrypoint: python://model_naming_convention
# hash: 2380ec00b3b6aecd0b647124d46ce06f40652cb46e77b561d9a7f7f9aef83177
# last_modified_at: '2025-05-29T14:13:58.819013+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_naming_convention.py
# namespace: python://omnibase.model.model_naming_convention
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: b3e9593b-73d2-4fa8-bd77-f8faf952fd07
# version: 1.0.0
# === /OmniNode:Metadata ===


from pydantic import BaseModel


class ModelNamingConventionResult(BaseModel):
    valid: bool
    reason: str = ""
