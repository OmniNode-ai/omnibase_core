# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Secret reference contract model — raw values explicitly forbidden."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelDelegationSecretRef(BaseModel):
    """Reference to a secret by name — raw values are explicitly forbidden."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ref_name: str = Field(
        ..., description="Name of the secret reference (env var or Infisical key)"
    )
    raw_value: str | None = Field(
        default=None,
        description="Must remain None; raw secrets must never be embedded in contracts",
    )

    @model_validator(mode="after")
    def reject_raw_value(self) -> ModelDelegationSecretRef:
        if self.raw_value is not None:
            raise ValueError(
                "raw_value must not be set on ModelDelegationSecretRef — "
                "use ref_name to reference the secret by name"
            )
        return self
