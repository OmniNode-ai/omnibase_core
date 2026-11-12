# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Event provenance model.

Attribution only -- a claim the producer made, never proof of authority.
Every value comes from the runtime's lane overlay, never a code default.
"""

from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.enums.enum_provenance_install_source import (
    EnumProvenanceInstallSource,
)
from omnibase_core.enums.enum_provenance_lane import EnumProvenanceLane
from omnibase_core.enums.enum_provenance_lane_kind import EnumProvenanceLaneKind


class ModelEventProvenance(BaseModel):
    """Provenance stamp attributing an event to the lane that produced it.

    Attribution only -- a claim the producer made, never proof of authority.
    Every value comes from the runtime's lane overlay, never a code default:
    a producer that cannot read its overlay omits the fields instead of
    inventing one.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    lane: EnumProvenanceLane = Field(
        ...,
        description="Runtime lane the emitter runs in.",
    )

    lane_kind: EnumProvenanceLaneKind | None = Field(
        default=None,
        description="Kind of emitter; set only when lane is OTHER.",
    )

    host: str | None = Field(
        default=None,
        description="Host the emitter ran on, recorded at write time.",
    )

    install_source: EnumProvenanceInstallSource | None = Field(
        default=None,
        description="How the emitter's code was installed, recorded at write time.",
    )

    revision: str | None = Field(
        default=None,
        description="Source revision the emitter was built from, recorded at write time.",
    )

    @field_validator("host")
    @classmethod
    def _host_is_recorded_or_absent(cls, value: str | None) -> str | None:
        """Reject a blank host: it reads as recorded but locates nothing.

        ``""`` and ``"   "`` are the shape that looks like attribution to a
        writer and is indistinguishable from none to a reader. A producer with
        no host must say so by omitting the field.
        """
        if value is None:
            return None
        if not value.strip():
            raise ValueError(
                "host must be a real host name or omitted entirely; "
                "a blank value records an attribution that attributes nothing"
            )
        return value

    @field_validator("revision")
    @classmethod
    def _revision_is_recorded_or_absent(cls, value: str | None) -> str | None:
        """Reject a blank revision: it reads as recorded but names nothing."""
        if value is None:
            return None
        if not value.strip():
            raise ValueError(
                "revision must be a real revision or omitted entirely; "
                "a blank value records an attribution that attributes nothing"
            )
        return value

    @model_validator(mode="after")
    def _overlay_matches_lane(self) -> ModelEventProvenance:
        """Enforce the lane overlay's shape: what each lane may and must say.

        A stamped lane (DEV, STABILITY, OTHER) carries its full overlay --
        lane_kind only for OTHER, and host/install_source/revision for every
        stamped lane -- while UNKNOWN carries nothing at all, because an
        event with no provenance must not grow half-invented facts.
        """
        if self.lane == EnumProvenanceLane.UNKNOWN:
            for field_name in (
                "lane_kind",
                "host",
                "install_source",
                "revision",
            ):
                if getattr(self, field_name) is not None:
                    raise ValueError(
                        f"{field_name} must be None when lane is 'unknown'; an "
                        "unknown-lane event carries no provenance and cannot "
                        "carry half of one"
                    )
            return self

        if self.lane in (EnumProvenanceLane.DEV, EnumProvenanceLane.STABILITY):
            if self.lane_kind is not None:
                raise ValueError(
                    "lane_kind must be None when lane is 'dev' or 'stability'; "
                    "lane_kind describes an OTHER emitter and dev/stability "
                    "emitters are what they are"
                )
        elif self.lane_kind is None:
            raise ValueError(
                "lane_kind is required when lane is 'other'; an OTHER lane "
                "must say what kind of emitter it is"
            )

        for required_field in ("host", "install_source", "revision"):
            if getattr(self, required_field) is None:
                raise ValueError(
                    f"{required_field} is required when lane is "
                    f"'{self.lane.value}'; a stamped lane records its full "
                    "overlay or none of it"
                )
        return self


__all__ = ["ModelEventProvenance"]
