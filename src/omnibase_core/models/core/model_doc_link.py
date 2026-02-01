# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.906782'
# description: Stamped by ToolPython
# entrypoint: python://model_doc_link
# hash: 14e201c9f287e098e737aebab2b83a47e9f0bb3c124754f6aa17411309dfbd77
# last_modified_at: '2025-05-29T14:13:58.763604+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_doc_link.py
# namespace: python://omnibase.model.model_doc_link
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 2143088c-92c9-4de5-bc43-4d7628509dcb
# version: 1.0.0
# === /OmniNode:Metadata ===


from pydantic import BaseModel, ConfigDict


class ModelDocLink(BaseModel):
    """Immutable documentation link reference.

    This model is frozen and hashable, suitable for use as dict keys or in sets.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    url: str
    title: str | None = None
    description: str | None = None
