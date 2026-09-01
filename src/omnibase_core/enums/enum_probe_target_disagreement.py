# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Probe-target disagreement enum (OMN-17312).

Why a stamped runtime identity failed to satisfy a target's declared identity.

:attr:`UNKNOWN` is deliberately a *disagreement*, not a third neutral state.
In all four of the 2026-08-2x stale-surface incidents the honest answer was "I
cannot tell", and every surface rendered it as "fine". A probe that cannot
answer whether it ran against its declared target has not proven anything, so
it fails on the same terms as one that provably ran somewhere else.
"""

from enum import StrEnum, unique


@unique
class EnumProbeTargetDisagreement(StrEnum):
    """The kind of disagreement between a stamp and a declaration."""

    MISMATCH = "mismatch"
    """Both sides named the field and the values differ. The probe provably ran
    somewhere other than its declared target."""

    UNKNOWN = "unknown"
    """The declaration names the field and the stamp cannot answer it. Fails
    closed — indistinguishable in consequence from MISMATCH, distinct only in
    the message so the operator knows which repair applies."""

    EMPTY_DECLARATION = "empty_declaration"
    """The declaration asserted nothing, so an assertion against it would
    compare zero fields. A vacuous check that reports PASS is the OMN-14531
    failure class; this makes it a refusal."""


__all__: list[str] = ["EnumProbeTargetDisagreement"]
