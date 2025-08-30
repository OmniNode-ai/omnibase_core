# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.097025'
# description: Stamped by ToolPython
# entrypoint: python://protocol_cli_dir_fixture_case
# hash: 717af0e50c30d20c7934065cf7707bf171d0c9cf49630d3a280cf84d2cffa76b
# last_modified_at: '2025-05-29T14:14:00.192806+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_cli_dir_fixture_case.py
# namespace: python://omnibase.protocol.protocol_cli_dir_fixture_case
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 78e37258-29cf-420f-aafd-7af0523cd1b6
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import List, Optional, Protocol

from pydantic import BaseModel


class FileEntryModel(BaseModel):
    relative_path: str
    content: str


class SubdirEntryModel(BaseModel):
    subdir: str
    files: List[FileEntryModel]


class ProtocolCLIDirFixtureCase(Protocol):
    id: str
    files: List[FileEntryModel]
    subdirs: Optional[List[SubdirEntryModel]]
