from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_log_level import EnumLogLevel

from .model_onex_message_context import ModelOnexMessageContext

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


__all__ = ["ModelOnexMessage"]


class ModelOnexMessage(BaseModel):
    """
    Human-facing message for CLI, UI, or agent presentation.
    Supports linking to files, lines, context, and rich rendering.
    """

    summary: str = Field(default=..., description="Short summary of the message.")
    suggestions: list[str] | None = None
    remediation: str | None = None
    rendered_markdown: str | None = None
    doc_link: str | None = None
    level: EnumLogLevel = Field(
        default=EnumLogLevel.INFO,
        description="Message level: info, warning, error, etc.",
    )
    file: str | None = Field(
        default=None, description="File path related to the message."
    )
    line: int | None = Field(
        default=None,
        description="Line number in the file, if applicable.",
    )
    column: int | None = None
    details: str | None = Field(
        default=None, description="Detailed message or context."
    )
    severity: EnumLogLevel | None = None
    code: str | None = Field(default=None, description="Error or warning code, if any.")
    context: ModelOnexMessageContext | None = Field(
        default=None,
        description="Additional context for the message.",
    )
    timestamp: datetime | None = Field(
        default=None, description="Timestamp of the message."
    )
    fixable: bool | None = None
    origin: str | None = None
    example: str | None = None
    localized_text: dict[str, str] | None = None
    type: str | None = Field(
        default=None,
        description="Type of message (error, warning, note, etc.)",
    )

    @property
    def error_code(self) -> str | None:
        """Alias for code field to match expected API."""
        return self.code
