# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.153817'
# description: Stamped by ToolPython
# entrypoint: python://protocol_stamper
# hash: 03d05f8af913336b06a9f083bcd45d5dc63dbb479b534d62047908932cbbf0ab
# last_modified_at: '2025-05-29T14:14:00.352908+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_stamper.py
# namespace: python://omnibase.protocol.protocol_stamper
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 4b93002d-dee8-4272-a3b6-d17d4ce909d7
# version: 1.0.0
# === /OmniNode:Metadata ===


from pathlib import Path
from typing import Protocol

from omnibase_core.enums.enum_template_type import TemplateTypeEnum
from omnibase_core.models.core.model_onex_message_result import OnexResultModel


class ProtocolStamper(Protocol):
    """
    Protocol for stamping ONEX node metadata with hashes, signatures, or trace data.

    Example:
        class MyStamper:
            def stamp(self, path: str) -> OnexResultModel:
                ...
    """

    def stamp(self, path: str) -> OnexResultModel:
        """Stamp an ONEX metadata file at the given path."""
        ...

    def stamp_file(
        self,
        path: Path,
        template: TemplateTypeEnum = TemplateTypeEnum.MINIMAL,
        overwrite: bool = False,
        repair: bool = False,
        force_overwrite: bool = False,
        author: str = "OmniNode Team",
        **kwargs: object,
    ) -> OnexResultModel:
        """
        Stamp the file with a metadata block, replacing any existing block.
        :return: OnexResultModel describing the operation result.
        """
        ...
