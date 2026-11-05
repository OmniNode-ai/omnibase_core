# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Where a public-repository job that selects the lab goes when it leaves (OMN-19998)."""

from __future__ import annotations

from enum import StrEnum, unique

__all__ = ["EnumPublicLabRouteKind"]


@unique
class EnumPublicLabRouteKind(StrEnum):
    """The destination class of one typed public lab route.

    A route is not an excuse for a job. It says what replaces the job, so every
    entry is work outstanding and the list can only shrink.

    Attributes:
        LAB_JOB_NODE: The job moves to the named node on the bus and leaves the workflow.
        RETIRES_WITH_RUNNERS: The job tests the runner fleet itself and leaves with it.
        MOVES_TO_HOSTED: The job needs nothing from the lab and moves to a hosted label.
    """

    LAB_JOB_NODE = "lab_job_node"
    RETIRES_WITH_RUNNERS = "retires_with_runners"
    MOVES_TO_HOSTED = "moves_to_hosted"
