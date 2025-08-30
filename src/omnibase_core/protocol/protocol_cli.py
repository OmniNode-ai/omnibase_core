# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.122722'
# description: Stamped by ToolPython
# entrypoint: python://protocol_cli
# hash: d1ed8d5010052c5eb8c2189bb4780e6b8e8f54ef9efcdd98e65ddc6c92d7876e
# last_modified_at: '2025-05-29T14:14:00.206328+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_cli.py
# namespace: python://omnibase.protocol.protocol_cli
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: c1263cdb-9416-4a80-9e34-e7082521932b
# version: 1.0.0
# === /OmniNode:Metadata ===


import argparse
from typing import List, Optional, Protocol

from pydantic import BaseModel

from omnibase_core.model.core.model_result_cli import ModelResultCLI


class CLIFlagDescriptionModel(BaseModel):
    name: str
    type: str
    default: Optional[str] = None
    help: Optional[str] = None
    required: bool = False
    # Add more fields as needed


class ProtocolLogger(Protocol):
    def info(self, msg: str, *args, **kwargs): ...

    def warning(self, msg: str, *args, **kwargs): ...

    def error(self, msg: str, *args, **kwargs): ...

    def debug(self, msg: str, *args, **kwargs): ...

    def critical(self, msg: str, *args, **kwargs): ...


class ProtocolCLI(Protocol):
    """
    Protocol for all CLI entrypoints. Provides shared CLI logic: argument parsing, logging setup, exit codes, metadata enforcement.
    Does NOT handle --apply or dry-run; those are handled in subclasses/protocols.

    Example:
        class MyCLI(ProtocolCLI):
            def get_parser(self) -> argparse.ArgumentParser:
                ...
            def main(self, argv: Optional[List[str]] = None) -> ModelResultCLI:
                ...
            def run(self, args: List[str]) -> ModelResultCLI:
                ...
            def describe_flags(self, format: str = "json") -> Any:
                ...
    """

    description: str
    logger: ProtocolLogger

    def get_parser(self) -> argparse.ArgumentParser: ...

    def main(self, argv: Optional[List[str]] = None) -> ModelResultCLI: ...

    def run(self, args: List[str]) -> ModelResultCLI: ...

    def describe_flags(self, format: str = "json") -> List[CLIFlagDescriptionModel]:
        """
        Return a structured description of all CLI flags (name, type, default, help, etc.).
        Args:
            format: Output format ('json' or 'yaml').
        Returns:
            List of CLIFlagDescriptionModel describing all CLI flags and their metadata.
        """
        ...
