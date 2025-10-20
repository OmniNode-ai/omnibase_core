# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-06-28T00:00:00.000000'
# description: Skipped File Reason Model
# entrypoint: python://model_skipped_file_reason
# hash: generated
# last_modified_at: '2025-06-28T00:00:00.000000+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_skipped_file_reason.py
# namespace: python://omnibase.model.core.model_skipped_file_reason
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: generated
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Model for tracking skipped files and their reasons.
"""

from pathlib import Path

from pydantic import BaseModel


class ModelSkippedFileReason(BaseModel):
    """Model for tracking skipped files and their reasons."""

    file: Path
    reason: str
