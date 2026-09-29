# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""An explicitly justified broker grant beyond contract-derived access."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_broker_grant_operation import EnumBrokerGrantOperation
from omnibase_core.enums.enum_broker_grant_resource_type import (
    EnumBrokerGrantResourceType,
)


class ModelBrokerExtraGrant(BaseModel):
    """Additional access a deployment grants to a broker principal."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    resource_type: EnumBrokerGrantResourceType = Field(
        ..., description="Kind of broker resource."
    )
    resource_name: str = Field(
        ..., min_length=1, pattern=r"\S", description="Broker resource name."
    )
    operation: EnumBrokerGrantOperation = Field(..., description="Permitted operation.")
    reason: str = Field(
        ..., min_length=1, pattern=r"\S", description="Why this extra access is needed."
    )


__all__ = ["ModelBrokerExtraGrant"]
