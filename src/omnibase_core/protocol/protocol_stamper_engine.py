# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.295679'
# description: Stamped by ToolPython
# entrypoint: python://protocol_stamper_engine
# hash: 5eb7ebbdf4d39d3c3f66ee78b1def44c00a1ebbf6b8c7c6fbab81d09f12c3216
# last_modified_at: '2025-05-29T14:14:00.345867+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_stamper_engine.py
# namespace: python://omnibase.protocol.protocol_stamper_engine
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: e2f209d1-3e49-47e0-9fd5-6732dd51d4e6
# version: 1.0.0
# === /OmniNode:Metadata ===


from pathlib import Path
from typing import List, Optional, Protocol

from omnibase_core.enums.enum_template_type import TemplateTypeEnum
from omnibase_core.model.core.model_onex_message_result import OnexResultModel


class ProtocolStamperEngine(Protocol):
    """
    Protocol for stamping ONEX node metadata files and processing directories.
    All arguments must use Pydantic models and Enums as appropriate.
    No file I/O or CLI dependencies in the protocol.
    """

    def stamp_file(
        self,
        path: Path,
        template: TemplateTypeEnum = TemplateTypeEnum.MINIMAL,
        overwrite: bool = False,
        repair: bool = False,
        force_overwrite: bool = False,
        author: str = "OmniNode Team",
        **kwargs: object,
    ) -> OnexResultModel: ...

    def process_directory(
        self,
        directory: Path,
        template: TemplateTypeEnum = TemplateTypeEnum.MINIMAL,
        recursive: bool = True,
        dry_run: bool = False,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        ignore_file: Optional[Path] = None,
        author: str = "OmniNode Team",
        overwrite: bool = False,
        repair: bool = False,
        force_overwrite: bool = False,
    ) -> OnexResultModel: ...
