from enum import Enum

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.752321'
# description: Stamped by ToolPython
# entrypoint: python://file_type
# hash: 05e5f00f0b354491d4a4e500bfe3303ab7cab7615a1f6dce0ace34d5a38af91a
# last_modified_at: '2025-05-29T14:13:58.535810+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: file_type.py
# namespace: python://omnibase.enums.file_type
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 7d4d495f-6e13-4d42-9af5-801983ee1c00
# version: 1.0.0
# === /OmniNode:Metadata ===


class EnumFileType(str, Enum):
    PYTHON = "python"
    YAML = "yaml"
    MARKDOWN = "markdown"
    JSON = "json"
    IGNORE = "ignore"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value
