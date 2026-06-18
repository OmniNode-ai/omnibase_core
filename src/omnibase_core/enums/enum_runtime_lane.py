# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime Lane Enum.

Canonical runtime lane targeted by a deployment request or proof. Graduated from
``omnibase_compat.contracts.runtime_deployment.wire.types`` (OMN-13209 / A2) now
that >=2 repos import it. Values match the OCC-owned wire schema enum and the live
``.201`` runtime lanes.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumRuntimeLane(UtilStrValueHelper, str, Enum):
    """Runtime lane targeted by a deployment request or proof.

    Values match the OCC wire schema enum and the live ``.201`` runtime lanes:
    dev (8085/8086, omnibase-infra), stability-test (18085/18086,
    omnibase-infra-stability-test), prod (28085/28086, omnibase-infra-prod).
    """

    DEV = "dev"
    STABILITY_TEST = "stability-test"
    PROD = "prod"


__all__: list[str] = ["EnumRuntimeLane"]
