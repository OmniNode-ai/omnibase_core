# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.803420'
# description: Stamped by ToolPython
# entrypoint: python://enum_output_format
# hash: b9ffcbcd82fac8a8b806ae6e4464f8d4724c2602468ee1a2d8fe1e5e72396c34
# last_modified_at: '2025-05-29T14:13:58.571814+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: enum_output_format.py
# namespace: python://omnibase.enums.enum_output_format
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 6315dd94-5965-431a-b63e-d3a3764fa72c
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Enums for output formats of CLI tools.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOutputFormat(StrValueHelper, str, Enum):
    """
    Canonical output formats for CLI tools.
    """

    TEXT = "text"  # Human-readable text format
    JSON = "json"  # JSON format for machine consumption
    YAML = "yaml"  # YAML format for machine consumption
    MARKDOWN = "markdown"  # Markdown format for documentation
    TABLE = "table"  # Tabular format for terminal display
    CSV = "csv"  # CSV format for tabular data
    DETAILED = "detailed"  # Detailed format for comprehensive output
    COMPACT = "compact"  # Compact format for minimal output
    RAW = "raw"  # Raw format for unprocessed output


__all__ = ["EnumOutputFormat"]
