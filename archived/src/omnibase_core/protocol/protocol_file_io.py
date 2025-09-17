# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.159379'
# description: Stamped by ToolPython
# entrypoint: python://protocol_file_io
# hash: 45357327b4f02f0e42126fbeedf7188006ba3a0966d0de7460aa7a8dc09c532b
# last_modified_at: '2025-05-29T14:14:00.241346+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_file_io.py
# namespace: python://omnibase.protocol.protocol_file_io
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 64d0d493-7733-41cc-8abd-2b0be47e0e10
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Protocol for file I/O operations (read/write YAML/JSON, list files, check existence).
Enables in-memory/mock implementations for protocol-first stamping tests.
"""

from pathlib import Path
from typing import Any, Protocol


class ProtocolFileIO(Protocol):
    """
    Protocol for file I/O operations (YAML/JSON/text) for stamping/validation tools.
    """

    def read_yaml(self, path: str | Path) -> Any:
        """Read YAML content from a file path."""
        ...

    def read_json(self, path: str | Path) -> Any:
        """Read JSON content from a file path."""
        ...

    def write_yaml(self, path: str | Path, data: Any) -> None:
        """Write YAML content to a file path."""
        ...

    def write_json(self, path: str | Path, data: Any) -> None:
        """Write JSON content to a file path."""
        ...

    def exists(self, path: str | Path) -> bool:
        """Check if a file exists."""
        ...

    def is_file(self, path: str | Path) -> bool:
        """Check if a path is a file."""
        ...

    def list_files(
        self,
        directory: str | Path,
        pattern: str | None = None,
    ) -> list[Path]:
        """List files in a directory, optionally filtered by pattern."""
        ...

    def read_text(self, path: str | Path) -> str:
        """Read plain text content from a file path."""
        ...

    def write_text(self, path: str | Path, data: str) -> None:
        """Write plain text content to a file path."""
        ...

    def read_bytes(self, path: str | Path) -> bytes:
        """Read binary content from a file path."""
        ...

    def write_bytes(self, path: str | Path, data: bytes) -> None:
        """Write binary content to a file path."""
        ...
