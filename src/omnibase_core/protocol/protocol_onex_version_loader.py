# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.233485'
# description: Stamped by ToolPython
# entrypoint: python://protocol_onex_version_loader
# hash: aa2965c3b98d0fe65f94d58efe743b4115f7f17f24985952e8bc125f0b776de7
# last_modified_at: '2025-05-29T14:14:00.297034+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_onex_version_loader.py
# namespace: python://omnibase.protocol.protocol_onex_version_loader
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 517b7eb6-e9ad-4683-924f-cae0ac93a64f
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Protocol

from omnibase_core.models.core.model_onex_version import ModelOnexVersionInfo


class ProtocolToolToolOnexVersionLoader(Protocol):
    """
    Protocol for loading ONEX version information from .onexversion files.
    """

    def get_onex_versions(self) -> ModelOnexVersionInfo: ...
