# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed terminal failure causes for delegation wire results."""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumDelegationTerminalFailureCause(str, Enum):
    """Machine-readable cause of a terminal delegation failure.

    Members name the event that actually DECIDED the run, never an inference
    drawn from it. The distinction is load-bearing: the over-quota refusal
    metric is measured from this field, so an authentication failure recorded
    as a quota event overstates capacity pressure that never happened
    (OMN-16998).

    OMN-19004 widened the vocabulary past the provider. Until then every member
    named a provider-side cause, so a run the QUALITY GATE decided had nowhere
    truthful to land and was recorded against the least-wrong provider member.
    A cause is not a report of the last thing that went wrong on the ladder; it
    is a report of what decided the outcome, and those coincide often enough
    that the field looks right until it matters.
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

    QUALITY_GATE_REFUSED = "quality_gate_refused"
    """The ladder exhausted because the QUALITY GATE refused every rung.

    The first member that is not a provider fault (OMN-19004). Every rung
    answered, the provider did its job, and the run still failed because no
    answer satisfied the gate. Measured on correlation
    ``73aba966-970c-4f29-987e-d85246152b2d``: five rungs, all answered, all
    refused, terminal cause ``provider_error``. A reader triaging that goes to
    the provider, the credential or the endpoint and finds nothing wrong there,
    because nothing was wrong there.

    Deliberately NOT a provider member, and deliberately not ``None``. Folding
    it into ``PROVIDER_ERROR`` would send every such reader to the wrong
    subsystem, and folding it into the quota member would enter a gate refusal
    into the over-quota metric as capacity pressure that never happened.
    ``None`` means no classification was attempted, which is a different fact
    from a classification that succeeded and named the gate.

    This member names the DECIDING event, so it is correct even on a run where
    a real provider fault also occurred: on correlation
    ``6ce51f77-62c4-4785-93f5-42e06e6a0a67`` three rungs answered and were
    refused by the gate and the fourth hit a genuine HTTP 429, and the whole
    run was reported as quota-exhausted. The 429 is real and stays legible on
    that rung's own attempt record; it did not decide a run that had already
    been decided by three gate refusals.
    """

    TIMEOUT = "timeout"
    """The run was cancelled for exceeding its execution budget.

    Emitted by the handler cancellation path (the 240-second handler cancel),
    never by a provider or the quality gate (OMN-19435). Before this member
    existed, that cancel recorded ``status=timeout`` with a null cause --
    measured at 10 such runs in 7 days of local receipts -- because no member
    named the run's own clock running out. Distinct from ``PROVIDER_ERROR``:
    the provider may never have responded at all, so there is nothing
    provider-side to report.
    """

    NO_TERMINAL = "no_terminal"
    """No component ever published a terminal event for this run.

    Reserved for the planned reaper (OMN-19435): a run that neither a
    provider, the quality gate nor the handler cancellation path ever
    terminated, discovered by reconciliation against a missing record rather
    than reported by the run itself. Distinct from ``None``, which means no
    classification was attempted on a terminal that exists; this member means
    the terminal itself never arrived.
    """


__all__: list[str] = ["EnumDelegationTerminalFailureCause"]
