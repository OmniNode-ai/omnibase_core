from pydantic import Field

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T08:55:22.046606'
# description: Stamped by ToolPython
# entrypoint: python://model_handler_config
# hash: 18868ce5b9318bc50c8e357aecd5fcf71e15a179313e162ae554be7f19cd2d53
# last_modified_at: '2025-05-29T14:13:58.791522+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_handler_config.py
# namespace: python://omnibase.model.model_handler_config
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: c6cae84d-f423-4d9b-a85c-12377cc25bcc
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Pydantic model for file type handler configuration.

This module provides structured configuration for file type handlers,
including processing categories, patterns, and priority settings.
"""

from pydantic import BaseModel, ConfigDict


class ModelHandlerConfig(BaseModel):
    """
    Configuration model for file type handlers.

    This model defines the configuration structure for file type handlers,
    including their processing capabilities, supported patterns, and priority.
    """

    handler_name: str = Field(description="Unique name identifier for the handler")
    processing_category: str = Field(
        description="Category of processing this handler performs",
    )
    force_processing_patterns: list[str] = Field(
        default_factory=list,
        description="File patterns this handler should process despite ignore rules",
    )
    supported_extensions: list[str] = Field(
        default_factory=list,
        description="File extensions this handler can process",
    )
    supported_filenames: list[str] = Field(
        default_factory=list,
        description="Specific filenames this handler can process",
    )
    priority: int = Field(
        default=50,
        description="Handler priority for conflict resolution (higher wins)",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "handler_name": "node_contract_handler",
                "processing_category": "contract_processing",
                "force_processing_patterns": ["node.onex.yaml", "*_contract.yaml"],
                "supported_extensions": [".yaml"],
                "supported_filenames": ["node.onex.yaml"],
                "priority": 75,
            },
        },
    )
