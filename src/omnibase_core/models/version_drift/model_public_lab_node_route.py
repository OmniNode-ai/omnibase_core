# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One typed route of a public-repository job off the lab runners (OMN-19998)."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_public_lab_route_kind import EnumPublicLabRouteKind

__all__ = ["ModelPublicLabNodeRoute"]

_NODE_PREFIX = "node_"


class ModelPublicLabNodeRoute(BaseModel):
    """A job that still selects the lab, and exactly what replaces it.

    Attributes:
        repository: The public repository the job is in.
        workflow: Repository-relative path of the workflow file.
        job: The job id in that workflow.
        kind: The destination class.
        destination: The node that takes the job, for ``lab_job_node``; otherwise
            the short name of what ends it.
        plan_step: The runner-order step the move belongs to.
        reason: Why the job cannot run on a GitHub-hosted runner today.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str = Field(min_length=1)
    workflow: str = Field(pattern=r"^\.github/workflows/[^/]+\.ya?ml$")
    job: str = Field(min_length=1)
    kind: EnumPublicLabRouteKind
    destination: str = Field(min_length=1)
    plan_step: str = Field(pattern=r"^R[2-6]$")
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def _node_route_names_a_node(self) -> Self:
        if self.kind is EnumPublicLabRouteKind.LAB_JOB_NODE and not (
            self.destination.startswith(_NODE_PREFIX)
        ):
            raise ValueError(
                f"{self.key}: a lab_job_node route must name a node, "
                f"got {self.destination!r}"
            )
        return self

    @property
    def key(self) -> tuple[str, str, str]:
        """The identity of the job this route covers."""
        return (self.repository, self.workflow, self.job)
