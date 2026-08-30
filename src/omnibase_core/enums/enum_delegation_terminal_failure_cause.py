# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed terminal failure causes for delegation wire results."""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumDelegationTerminalFailureCause(str, Enum):
    """Machine-readable cause of a terminal delegation failure.

    Members name the failure class the provider actually reported, never an
    inference drawn from it. The distinction is load-bearing: the over-quota
    refusal metric is measured from this field, so an authentication failure
    recorded as a quota event overstates capacity pressure that never happened
    (OMN-16998).
    """

    PROVIDER_QUOTA_EXHAUSTED = "provider_quota_exhausted"
    """The provider refused on capacity: HTTP 429 with a recognised quota body."""

    AUTH_FAILED = "auth_failed"
    """The provider rejected the credential: HTTP 401 or 403. Never capacity."""

    PROVIDER_ERROR = "provider_error"
    """Any other provider-side failure, once one has been observed.

    Distinct from a null cause, which means no classification was attempted --
    an unobserved failure and an unrecognised one are not the same fact.
    """


__all__: list[str] = ["EnumDelegationTerminalFailureCause"]
