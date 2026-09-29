# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The access sources declared for one broker principal."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.config_overlay.model_broker_extra_grant import (
    ModelBrokerExtraGrant,
)


class ModelBrokerPrincipalDeclaration(BaseModel):
    """A principal's contract-derived, profile-derived and additional grants."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    principal: str = Field(
        ..., min_length=1, pattern=r"\S", description="Broker principal name."
    )
    broker_id: str = Field(  # string-id-ok: deployment-chosen broker name, not a UUID
        ...,
        min_length=1,
        pattern=r"\S",
        description="Broker on which access is declared.",
    )
    contract_set: tuple[str, ...] = Field(
        ...,
        description="Contracts from which to derive access; may be empty with a profile.",
    )
    client_profile: str | None = Field(
        ...,
        min_length=1,
        pattern=r"\S",
        description="Client access profile, or null for contract-only access.",
    )
    extra_grants: tuple[ModelBrokerExtraGrant, ...] = Field(
        ..., description="Explicit additional grants; may be empty."
    )

    @field_validator("principal", "broker_id")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        """Reject identifiers containing only whitespace."""
        if not value.strip():
            raise ValueError(
                "principal and broker_id must not be blank"
            )  # error-ok: Pydantic validation
        return value

    @field_validator("contract_set")
    @classmethod
    def _contracts_non_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Reject contract names containing only whitespace."""
        if any(not name.strip() for name in value):
            raise ValueError(
                "contract_set entries must not be blank"
            )  # error-ok: Pydantic validation
        return value

    @model_validator(mode="after")
    def _access_source(self) -> Self:
        """Require a contract set or a named client profile."""
        if not self.contract_set and not (
            self.client_profile and self.client_profile.strip()
        ):
            raise ValueError(
                "contract_set or client_profile must supply access"
            )  # error-ok: Pydantic validation
        return self


__all__ = ["ModelBrokerPrincipalDeclaration"]
