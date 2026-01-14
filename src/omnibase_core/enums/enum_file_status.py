# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.740068'
# description: Stamped by ToolPython
# entrypoint: python://file_status
# hash: 92f5b1c47003efdae659a3867f9be53987c3b542676876e936e6d399b42bb396
# last_modified_at: '2025-05-29T14:13:58.528704+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: file_status.py
# namespace: python://omnibase.enums.file_status
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: d7aa1be6-3755-48d3-87d2-973f3d9ea174
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Enum for file status values used in metadata blocks.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFileStatus(StrValueHelper, str, Enum):
    EMPTY = "empty"  # File has no content
    UNVALIDATED = "unvalidated"  # Not schema-validated
    VALIDATED = "validated"  # Schema-validated
    DEPRECATED = "deprecated"  # Marked for removal
    INCOMPLETE = "incomplete"  # Missing required fields
    SYNTHETIC = "synthetic"  # Generated, not user-authored
    # Add more statuses as protocol evolves


__all__ = ["EnumFileStatus"]
