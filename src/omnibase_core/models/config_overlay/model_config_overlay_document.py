# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One overlay document as a source returns it (OMN-19391).

The I/O type of plan task B3's ``ProtocolConfigOverlaySource.get_document``.
``content`` is the raw JSON object; the reader validates it into the schema
that ``key.schema_ref`` names, which may live above core (rule 7).
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_config_overlay_key import EnumConfigOverlayKey
from omnibase_core.enums.enum_config_overlay_source import EnumConfigOverlaySource
from omnibase_core.types.type_json import JsonType


class ModelConfigOverlayDocument(BaseModel):
    """A config overlay document with the provenance a replay needs."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    key: EnumConfigOverlayKey = Field(..., description="The overlay key.")
    schema_ref: str = Field(
        ...,
        min_length=1,
        description="Owning repository and schema name; must equal key.schema_ref.",
    )
    schema_version: str = Field(  # string-version-ok: overlay schema discriminator such as llm_catalog.v1, not SemVer
        ...,
        min_length=1,
        max_length=64,
        description="Version tag of the schema the content obeys.",
    )
    source: EnumConfigOverlaySource = Field(
        ..., description="The source the document was read from."
    )
    sha256: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="Lowercase hex sha256 of the document bytes as read.",
    )
    content: dict[str, JsonType] = Field(
        ..., description="The document body, validated by the key's schema."
    )

    @model_validator(mode="after")
    def _schema_ref_matches_key(self) -> Self:
        if self.schema_ref != self.key.schema_ref:
            raise ValueError(
                f"overlay key {self.key.value!r} is validated by schema "
                f"{self.key.schema_ref!r}, got schema_ref {self.schema_ref!r}"
            )
        return self


__all__ = ["ModelConfigOverlayDocument"]
