from pydantic import Field

from omnibase_core.enums.enum_tree_sync_status import EnumTreeSyncStatus

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.079159'
# description: Stamped by ToolPython
# entrypoint: python://model_tree_sync_result
# hash: 8f5cdddc023665761d7b18793cf669a510b0e0130ceadee21d51080d357e2ae2
# last_modified_at: '2025-05-29T14:13:58.948948+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_tree_sync_result.py
# namespace: python://omnibase.model.model_tree_sync_result
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: f8e726da-f556-48ef-8b60-37be6cf292ee
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Model for .tree and filesystem sync validation results.
"""

from pathlib import Path

from pydantic import BaseModel

from omnibase_core.models.results.model_onex_message import ModelOnexMessage


class ModelTreeSyncResult(BaseModel):
    """
    Result model for validating .tree and filesystem sync.
    """

    extra_files_on_disk: set[Path] = Field(
        default_factory=set,
        description="Files present on disk but not in .tree",
    )
    missing_files_in_tree: set[Path] = Field(
        default_factory=set,
        description="Files listed in .tree but missing on disk",
    )
    status: EnumTreeSyncStatus = Field(
        default=...,
        description="Sync status: ok, drift, or error",
    )
    messages: list[ModelOnexMessage] = Field(
        default_factory=list,
        description="Validation messages and errors",
    )
