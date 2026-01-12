# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.762056'
# description: Stamped by ToolPython
# entrypoint: python://ignore_pattern_source
# hash: a224d944abb3aaf927f7e182dfe89dd3163abe288aeef63c01ff550f13cdcdc6
# last_modified_at: '2025-05-29T14:13:58.542812+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: ignore_pattern_source.py
# namespace: python://omnibase.enums.ignore_pattern_source
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 1e3a136b-d95f-4fb4-8d79-5a81d0cd9878
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Enums for file traversal and ignore pattern handling.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumIgnorePatternSource(StrValueHelper, str, Enum):
    """
    Canonical sources for ignore patterns when traversing directories.

    This enum defines the possible sources for ignore patterns when
    filtering files during directory traversal operations.
    """

    FILE = "file"  # Patterns from an ignore file (e.g., .onexignore)
    DIRECTORY = "directory"  # Default directory patterns to ignore (e.g., .git)
    USER = "user"  # User-provided patterns via CLI or API
    DEFAULT = "default"  # Built-in default patterns from the application
    NONE = "none"  # No ignore patterns (process all files)


@unique
class EnumTraversalMode(StrValueHelper, str, Enum):
    """
    Canonical modes for directory traversal.

    This enum defines the possible modes for traversing directories when
    processing files.
    """

    RECURSIVE = "recursive"  # Recursively traverse all subdirectories
    FLAT = "flat"  # Only process files in the specified directory
    SHALLOW = "shallow"  # Process files in the specified directory and immediate subdirectories
    CUSTOM = "custom"  # Custom traversal based on specific rules
