# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, durable provenance for a delegation request and its terminal."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_delegation_traffic_class import (
    EnumDelegationTrafficClass,
)


class ModelDelegationProvenance(BaseModel):
    """Canonical provenance carried unchanged from request to terminal.

    This model is the single classification surface. Consumers classify
    synthetic traffic from ``traffic_class`` and may use ``source_surface`` and
    ``requested_by`` for attribution; they must not infer provenance from prompt
    text or treat an absent model as synthetic.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: Literal["claude-code", "codex", "external-client"] = Field(
        ...,
        description="Registered adapter source at delegation ingress.",
    )
    traffic_class: EnumDelegationTrafficClass = Field(
        default=EnumDelegationTrafficClass.UNCLASSIFIED,
        description=(
            "Authoritative traffic classification. Unclassified is unknown, not "
            "synthetic or organic."
        ),
    )
    source_surface: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description="Named producer surface, when one was declared at ingress.",
    )
    requested_by: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description="Named request initiator, when one was declared at ingress.",
    )

    @field_validator("source_surface", "requested_by")
    @classmethod
    def validate_optional_identifier(cls, value: str | None) -> str | None:
        """Reject blank or padded identifiers so stored values are query-stable."""
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("provenance identifiers must be nonblank and unpadded")
        return value

    @model_validator(mode="after")
    def validate_synthetic_surface(self) -> Self:
        """Require synthetic claims to name the producer surface that made them."""
        if (
            self.traffic_class is EnumDelegationTrafficClass.SYNTHETIC
            and self.source_surface is None
        ):
            raise ValueError("synthetic delegation provenance requires source_surface")
        return self


__all__ = ["EnumDelegationTrafficClass", "ModelDelegationProvenance"]
