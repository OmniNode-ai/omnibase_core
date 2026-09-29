# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The declared content and drop-ins of a systemd unit."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.config_overlay.model_host_systemd_drop_in import (
    ModelHostSystemdDropIn,
)


class ModelHostSystemdUnit(BaseModel):
    """A host's systemd unit and its declared drop-in files."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    unit_name: str = Field(
        ..., min_length=1, pattern=r"\S", description="Systemd unit name."
    )
    content_sha256: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="Lowercase SHA-256 digest of unit content.",
    )
    drop_ins: tuple[ModelHostSystemdDropIn, ...] = Field(
        ..., description="Declared drop-in files; may be empty."
    )


__all__ = ["ModelHostSystemdUnit"]
