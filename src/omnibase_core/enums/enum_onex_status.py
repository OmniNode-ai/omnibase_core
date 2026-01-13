# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.792634'
# description: Stamped by ToolPython
# entrypoint: python://onex_status
# hash: b54f8ff667839e7ac873eda2daced72b6230477e5f3c46e28c5e29556ab06a43
# last_modified_at: '2025-05-29T14:13:58.564675+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: onex_status.py
# namespace: python://omnibase.enums.onex_status
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 071d0cf7-cba8-404c-b30c-00d52b6d3c1a
# version: 1.0.0
# === /OmniNode:Metadata ===


from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOnexStatus(StrValueHelper, str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"
    FIXED = "fixed"
    PARTIAL = "partial"
    INFO = "info"
    UNKNOWN = "unknown"
