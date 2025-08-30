# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.169382'
# description: Stamped by ToolPython
# entrypoint: python://protocol_file_type_handler
# hash: f865199088b42907bcfd03147a6071a4ec1c21659e83436e8b30537c67f30d6c
# last_modified_at: '2025-05-29T14:14:00.255085+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_file_type_handler.py
# namespace: python://omnibase.protocol.protocol_file_type_handler
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 4e1063a3-c759-42a8-8a3f-2d05489e0ea4
# version: 1.0.0
# === /OmniNode:Metadata ===


from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from omnibase_core.model.configuration.model_can_handle_result import \
        ModelCanHandleResult
    from omnibase_core.model.configuration.model_handler_protocol import \
        ModelHandlerMetadata
    from omnibase_core.model.configuration.model_serialized_block import \
        ModelSerializedBlock
    from omnibase_core.model.core.model_extracted_block import \
        ModelExtractedBlock
    from omnibase_core.model.core.model_onex_message_result import \
        OnexResultModel


class ProtocolFileTypeHandler(Protocol):
    """
    Protocol for file type handlers in the ONEX stamper engine.
    All methods and metadata must use canonical result models per typing_and_protocols rule.
    """

    @property
    def metadata(self) -> ModelHandlerMetadata: ...

    @property
    def handler_name(self) -> str: ...

    @property
    def handler_version(self) -> str: ...

    @property
    def handler_author(self) -> str: ...

    @property
    def handler_description(self) -> str: ...

    @property
    def supported_extensions(self) -> list[str]: ...

    @property
    def supported_filenames(self) -> list[str]: ...

    @property
    def handler_priority(self) -> int: ...

    @property
    def requires_content_analysis(self) -> bool: ...

    def can_handle(self, path: Path, content: str) -> ModelCanHandleResult: ...

    def extract_block(self, path: Path, content: str) -> ModelExtractedBlock: ...

    def serialize_block(self, meta: ModelExtractedBlock) -> ModelSerializedBlock: ...

    def normalize_rest(self, rest: str) -> str: ...

    def stamp(self, path: Path, content: str, **kwargs: object) -> OnexResultModel: ...

    def pre_validate(
        self, path: Path, content: str, **kwargs: object
    ) -> Optional[OnexResultModel]: ...

    def post_validate(
        self, path: Path, content: str, **kwargs: object
    ) -> Optional[OnexResultModel]: ...

    def validate(
        self, path: Path, content: str, **kwargs: object
    ) -> OnexResultModel: ...
