# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One protocol bound by the lane overlay to an implementation (OMN-21595)."""

from pydantic import BaseModel, ConfigDict, Field


class ModelDependencyBinding(BaseModel):
    """What the overlay binds a protocol to.

    Attributes:
        protocol: The protocol identifier a contract lists under ``handler_dependencies``.
        implementation: The name a dependency factory is registered under.
        config: The configuration handed to that factory and to nothing else.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    protocol: str = Field(min_length=1)
    implementation: str = Field(min_length=1)
    config: dict[str, str] = Field(default_factory=dict)
