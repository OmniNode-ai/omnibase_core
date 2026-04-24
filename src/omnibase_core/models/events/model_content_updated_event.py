# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pydantic import ConfigDict, Field

from omnibase_core.enums.enum_content_kind import EnumContentKind
from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_json import JsonType

__all__ = ["ModelContentPayload"]


class ModelContentPayload(ModelEventPayloadBase):
    model_config = ConfigDict(frozen=True, extra="forbid")
    content_kind: EnumContentKind = Field(
        ..., description="Section discriminator — one of the 9 EnumContentKind values."
    )
    schema_version: ModelSemVer = Field(
        ..., description="Payload schema version (ModelSemVer, not str)."
    )
    data: dict[str, JsonType] = Field(
        ..., description="Section YAML deserialized to dict."
    )
