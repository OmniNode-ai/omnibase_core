# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.964684'
# description: Stamped by ToolPython
# entrypoint: python://model_metadata_config
# hash: e2dbdf5b66ae5224d0cd218e12cb2c82af74853fee74eaecf2802a07e2a14374
# last_modified_at: '2025-05-29T14:13:58.805359+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_metadata_config.py
# namespace: python://omnibase.model.model_metadata_config
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 10b37be5-2b4b-475a-8dda-1cd381072138
# version: 1.0.0
# === /OmniNode:Metadata ===


from pydantic import BaseModel, ConfigDict

from omnibase_core.models.core.model_examples import ModelCustomSettings


class ModelMetadataConfig(BaseModel):
    # Example config fields; add more as needed
    timeout: int | None = None
    retries: int | None = None
    enable_cache: bool | None = None
    custom_settings: ModelCustomSettings | None = None  # Arbitrary settings, extensible
    # Arbitrary extra fields allowed for extensibility
    model_config = ConfigDict(extra="allow")
