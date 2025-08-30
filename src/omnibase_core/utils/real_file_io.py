# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.803241'
# description: Stamped by ToolPython
# entrypoint: python://real_file_io
# hash: 2fed0704cb0264abd53ec77b8e94d64d782b1862fcf622ceab0b77f5cdf233eb
# last_modified_at: '2025-05-29T14:14:00.975218+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: real_file_io.py
# namespace: python://omnibase.utils.real_file_io
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 8645b6ef-583f-4f0f-8bc4-b3a7b9fe8366
# version: 1.0.0
# === /OmniNode:Metadata ===


import builtins
import json
from pathlib import Path

import yaml

from omnibase_core.protocol.protocol_file_io import ProtocolFileIO


class RealFileIO(ProtocolFileIO):
    def read_yaml(self, path: str | Path) -> object:
        with builtins.open(path) as f:
            return yaml.safe_load(f)

    def read_json(self, path: str | Path) -> object:
        with builtins.open(path) as f:
            return json.load(f)

    def write_yaml(self, path: str | Path, data: object) -> None:
        with builtins.open(path, "w") as f:
            yaml.safe_dump(data, f)

    def write_json(self, path: str | Path, data: object) -> None:
        with builtins.open(path, "w") as f:
            json.dump(data, f, sort_keys=True)

    def exists(self, path: str | Path) -> bool:
        return Path(path).exists()

    def is_file(self, path: str | Path) -> bool:
        return Path(path).is_file()

    def list_files(
        self,
        directory: str | Path,
        pattern: str | None = None,
    ) -> list[Path]:
        p = Path(directory)
        if pattern:
            return list(p.glob(pattern))
        return list(p.iterdir())

    def read_text(self, path: str | Path) -> str:
        """Read plain text content from a file path."""
        with builtins.open(path, encoding="utf-8") as f:
            return f.read()

    def write_text(self, path: str | Path, data: str) -> None:
        """Write plain text content to a file path."""
        with builtins.open(path, "w", encoding="utf-8") as f:
            f.write(data)

    def read_bytes(self, path: str | Path) -> bytes:
        """Read binary content from a file path."""
        with builtins.open(path, "rb") as f:
            return f.read()

    def write_bytes(self, path: str | Path, data: bytes) -> None:
        """Write binary content to a file path."""
        with builtins.open(path, "wb") as f:
            f.write(data)
