# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deployment-declared operating system settings for a host."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.config_overlay.model_host_network_interface_setting import (
    ModelHostNetworkInterfaceSetting,
)
from omnibase_core.models.config_overlay.model_host_systemd_unit import (
    ModelHostSystemdUnit,
)


class ModelHostDeclaration(BaseModel):
    """Kernel, unit, network and power settings declared for one host."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    host_id: str = Field(  # string-id-ok: deployment-chosen host name, not a UUID
        ...,
        min_length=1,
        pattern=r"\S",
        description="Host whose settings are declared.",
    )
    kernel_parameters: dict[str, str] = Field(
        ..., description="Kernel parameter values by name."
    )
    systemd_units: tuple[ModelHostSystemdUnit, ...] = Field(
        ..., description="Declared systemd units; may be empty."
    )
    network_interfaces: tuple[ModelHostNetworkInterfaceSetting, ...] = Field(
        ..., description="Declared network interface settings; may be empty."
    )
    power_settings: dict[str, str] = Field(..., description="Power settings by name.")

    @field_validator("host_id")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        """Reject a host identifier containing only whitespace."""
        if not value.strip():
            raise ValueError(
                "host_id must not be blank"
            )  # error-ok: Pydantic validation
        return value


__all__ = ["ModelHostDeclaration"]
