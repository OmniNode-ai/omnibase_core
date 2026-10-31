# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Approval state of an experiment card (OMN-21627)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentApprovalState(UtilStrValueHelper, str, Enum):
    """Whether a proposed experiment has the authority to run. A recommendation never grants itself authority.

    Attributes:
        PROPOSED: Generated, not approved.
        APPROVED: Approved under its contract.
        DECLINED: Declined by the decision owner.
    """

    PROPOSED = "proposed"
    APPROVED = "approved"
    DECLINED = "declined"
