# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed waiver document for the Pydantic extra-forbid ratchet."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.validation.model_extra_forbid_waiver import (
    ModelExtraForbidWaiver,
)


class ModelExtraForbidWaiverDocument(BaseModel):
    """A strict document containing zero or more expiring extra-forbid waivers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    waivers: list[ModelExtraForbidWaiver] = Field(default_factory=list)

    @field_validator("waivers", mode="before")
    @classmethod
    def normalize_null_waivers(cls, value: object) -> object:
        """Preserve the established ``waivers: null`` meaning of no waivers."""
        return [] if value is None else value


__all__ = ["ModelExtraForbidWaiverDocument"]
