# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-06-28T00:00:00.000000'
# description: Log Context Model
# entrypoint: python://model_log_context
# hash: generated
# last_modified_at: '2025-06-28T00:00:00.000000+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_log_context.py
# namespace: python://omnibase.model.core.model_log_context
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: generated
# version: 1.0.0
# === /OmniNode:Metadata ===


from uuid import UUID

from pydantic import BaseModel


class ModelLogContext(BaseModel):
    """
    Strongly typed context for ONEX structured log events.
    """

    calling_module: str
    calling_function: str
    calling_line: int
    timestamp: str
    node_id: UUID | None = None
    correlation_id: UUID | None = None
