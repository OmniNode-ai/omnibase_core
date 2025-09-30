# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai  # noqa: ERA001
# created_at: '2025-05-28T13:24:07.772489'  # noqa: ERA001
# description: Severity levels for validation and generation results
# entrypoint: python://severity_level
# hash: 1fda8bf538c4432877895fbc1c58c62713ba884ce851d63771d09d7bfab6397c
# last_modified_at: '2025-08-30T20:30:00.000000+00:00'  # noqa: ERA001
# lifecycle: active  # noqa: ERA001
# meta_type: tool  # noqa: ERA001
# metadata_version: 0.1.0
# name: severity_level.py  # noqa: ERA001
# namespace: python://omnibase.enums.severity_level
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11  # noqa: ERA001
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}  # noqa: ERA001
# uuid: 56bbeb2e-89f8-4bde-a006-09a645eb73e0
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Log levels and severity levels for ONEX.

EnumLogLevel: Based on SPI LogLevel Literal type for consistency
EnumLogLevel: For validation and generation result classification
"""

from enum import Enum


class EnumLogLevel(str, Enum):
    """Log levels enum for SPI LogLevel Literal type and validation."""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"
    SUCCESS = "success"
    UNKNOWN = "unknown"
