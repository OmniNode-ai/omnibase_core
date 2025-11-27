# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.688102'
# description: Stamped by ToolPython
# entrypoint: python://model_onex_version
# hash: 6a1dc6da39a12c17cd5f4ebcd9c57c9b00b3531dfda19183c16f298c32e23b2d
# last_modified_at: '2025-05-29T14:13:58.876387+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_onex_version.py
# namespace: python://omnibase.model.model_onex_version
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: ec6d12ec-f21d-4dd0-934f-31c62882f282
# version: 1.0.0
# === /OmniNode:Metadata ===


from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelOnexVersionInfo(BaseModel):
    """
    Canonical Pydantic model for ONEX version information.
    Fields:
        metadata_version (ModelSemVer): The metadata schema version.
        protocol_version (ModelSemVer): The protocol version.
        schema_version (ModelSemVer): The schema version.
    """

    metadata_version: ModelSemVer
    protocol_version: ModelSemVer
    schema_version: ModelSemVer
