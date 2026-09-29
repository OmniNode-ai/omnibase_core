# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Settings declared for one host network interface."""

from pydantic import BaseModel, ConfigDict, Field


class ModelHostNetworkInterfaceSetting(BaseModel):
    """A named interface and its declared setting values."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    interface: str = Field(
        ..., min_length=1, pattern=r"\S", description="Network interface name."
    )
    settings: dict[str, str] = Field(..., description="Interface settings by name.")


__all__ = ["ModelHostNetworkInterfaceSetting"]
