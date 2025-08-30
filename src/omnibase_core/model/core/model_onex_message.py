# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.000948'
# description: Stamped by ToolPython
# entrypoint: python://model_onex_message
# hash: 3ca4999af493922e956b0664c3b80df99b34d8c488bc50f119b1238f31c79062
# last_modified_at: '2025-05-29T14:13:58.869245+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_onex_message.py
# namespace: python://omnibase.model.model_onex_message
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 9acab5df-2004-4ed4-9f4f-e5c02c6b7de9
# version: 1.0.0
# === /OmniNode:Metadata ===


from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from omnibase.enums.enum_log_level import LogLevelEnum, SeverityLevelEnum
from pydantic import BaseModel, Field

from .model_onex_message_context import ModelOnexMessageContext

__all__ = ["LogLevelEnum", "SeverityLevelEnum", "ModelOnexMessage"]


class ModelOnexMessage(BaseModel):
    """
    Human-facing message for CLI, UI, or agent presentation.
    Supports linking to files, lines, context, and rich rendering.
    """

    summary: str = Field(..., description="Short summary of the message.")
    suggestions: Optional[List[str]] = None
    remediation: Optional[str] = None
    rendered_markdown: Optional[str] = None
    doc_link: Optional[str] = None
    level: LogLevelEnum = Field(
        LogLevelEnum.INFO, description="Message level: info, warning, error, etc."
    )
    file: Optional[str] = Field(None, description="File path related to the message.")
    line: Optional[int] = Field(
        None, description="Line number in the file, if applicable."
    )
    column: Optional[int] = None
    details: Optional[str] = Field(None, description="Detailed message or context.")
    severity: Optional[SeverityLevelEnum] = None
    code: Optional[str] = Field(None, description="Error or warning code, if any.")
    context: Optional[ModelOnexMessageContext] = Field(
        None, description="Additional context for the message."
    )
    timestamp: Optional[datetime] = Field(None, description="Timestamp of the message.")
    fixable: Optional[bool] = None
    origin: Optional[str] = None
    example: Optional[str] = None
    localized_text: Optional[Dict[str, str]] = None
    type: Optional[str] = Field(
        None, description="Type of message (error, warning, note, etc.)"
    )
