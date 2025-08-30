# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.772489'
# description: Severity levels for validation and generation results
# entrypoint: python://severity_level
# hash: 1fda8bf538c4432877895fbc1c58c62713ba884ce851d63771d09d7bfab6397c
# last_modified_at: '2025-08-30T20:30:00.000000+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: severity_level.py
# namespace: python://omnibase.enums.severity_level
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 56bbeb2e-89f8-4bde-a006-09a645eb73e0
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Severity levels for validation and generation results.
Note: For logging levels, use LogLevel from omnibase.protocols.types instead.
"""

from enum import Enum


class SeverityLevelEnum(str, Enum):
    """Severity levels for validation and generation result classification."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    CRITICAL = "critical"
    SUCCESS = "success"
    UNKNOWN = "unknown"
