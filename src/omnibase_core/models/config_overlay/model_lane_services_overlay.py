# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The body of a ``lane.services`` overlay document."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.config_overlay.model_lane_one_shot_job import (
    ModelLaneOneShotJob,
)
from omnibase_core.models.config_overlay.model_lane_service_declaration import (
    ModelLaneServiceDeclaration,
)


class ModelLaneServicesOverlay(BaseModel):
    """Services and preparation jobs declared for a runtime lane."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["lane_services.v1"] = (
        Field(  # string-version-ok: schema discriminator, not SemVer
            ..., description="Schema version tag."
        )
    )
    lane_id: str = Field(  # string-id-ok: deployment-chosen lane slug and store path segment, not a UUID
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
        description="Runtime lane whose services are declared.",
    )
    services: tuple[ModelLaneServiceDeclaration, ...] = Field(
        ..., min_length=1, description="Services declared for this lane."
    )
    one_shot_jobs: tuple[ModelLaneOneShotJob, ...] = Field(
        ..., description="Jobs preparing declared services; may be empty."
    )

    @model_validator(mode="after")
    def _declared_services(self) -> Self:
        """Require every preparation job to reference a declared service."""
        service_names = {service.service_name for service in self.services}
        for job in self.one_shot_jobs:
            if job.prepares_service not in service_names:
                raise ValueError(  # error-ok: Pydantic validation
                    f"prepares_service {job.prepares_service!r} must name a declared service"
                )
        return self


__all__ = ["ModelLaneServicesOverlay"]
