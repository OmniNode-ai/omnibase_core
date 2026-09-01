# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Probe-target assertion (OMN-17312, epic OMN-17306).

Answers one question mechanically: *did the process that produced this stamp
run against the target this probe claims to be about?*

## The manual step this replaces

On 2026-08-31 a **valid** in-lane probe was performed by hand — read the
deployed container's ``direct_url.json``, compare the vendored ``omnimarket``
commit against ``origin/dev``, confirm the code under test was actually
present, and only then read the result as a statement about the lane. Two hours
earlier an **invalid** probe skipped that step (OMN-16932 record, correlation
``b9cd305c-8f31-497a-b404-b75b45b98341``): it published over the lane's broker,
so it looked addressed to ``.201``, while the orchestrator resolved out of the
operator's local venv on pre-fix ``omnimarket 0.4.11``. The lane's own logs had
zero hits for that correlation. Both probes printed a confident result; only
one of them was about the lane.

The difference between the two was entirely a human comparison. This module is
that comparison.

## Fails closed on UNKNOWN, not only on MISMATCH

The load-bearing property. In every incident of the OMN-17306 class the honest
answer was "I cannot tell" and every surface rendered it as "fine":
``core.bare=true`` made ``fetch`` exit 0 while ``checkout`` exited 128
(OMN-17291); ``DEPLOY_REF`` unset printed a warning into a 4000-line log and
built anyway; the drift guard's ``None`` short-circuit treated "not installed"
as "nothing to check" (OMN-14060 → OMN-14531).

So a declared field the stamp cannot answer is a REFUSAL, on the same terms as
a provable mismatch. The two are distinguished only in the message, because
they call for different repairs -- restamp versus re-target -- never in the
verdict.

An empty declaration is likewise a refusal: an assertion that compares zero
fields and returns PASS is the vacuous-check failure class OMN-14531 found
across 16/16 sweeps.

Pure comparison, no I/O: reading the declaration off a lane and the stamp off a
receipt is the caller's job (``onex identity assert-target`` in omnibase_infra).
"""

from __future__ import annotations

from omnibase_core.enums.enum_probe_target_disagreement import (
    EnumProbeTargetDisagreement,
)
from omnibase_core.models.runtime.model_declared_target_identity import (
    ModelDeclaredTargetIdentity,
)
from omnibase_core.models.runtime.model_probe_target_verdict import (
    ModelProbeTargetVerdict,
)
from omnibase_core.models.runtime.model_runtime_identity import ModelRuntimeIdentity

__all__ = [
    "ProbeTargetMismatchError",
    "assert_probe_target",
]


class ProbeTargetMismatchError(RuntimeError):
    """A stamp did not satisfy a target's declared identity.

    Carries the disagreement kind so a caller can distinguish "ran elsewhere"
    from "cannot tell" without parsing the message, while treating both as the
    same refusal.
    """

    def __init__(
        self,
        *,
        kind: EnumProbeTargetDisagreement,
        target_name: str,
        detail: str,
    ) -> None:
        self.kind = kind
        self.target_name = target_name
        self.detail = detail
        super().__init__(
            f"probe-target assertion FAILED ({kind.value}) for target "
            f"{target_name!r}: {detail}"
        )


def assert_probe_target(
    *,
    stamped: ModelRuntimeIdentity,
    declared: ModelDeclaredTargetIdentity,
) -> ModelProbeTargetVerdict:
    """Assert ``stamped`` satisfies ``declared``, or raise.

    Returns a verdict naming every field actually compared, so a caller can
    prove the assertion was not vacuous. Raises
    :class:`ProbeTargetMismatchError` on the first disagreement, checked
    cheapest-first (host, then locus, then per-package commits) so the message
    names the coarsest thing that is wrong -- "you were on the wrong host" is
    more useful than "omnimarket's commit differs" when both are true.

    Args:
        stamped: What the executing process said it was.
        declared: What the target says it is, read from the target's own
            surface. Never the caller's intent.

    Raises:
        ProbeTargetMismatchError: the declaration asserts nothing
            (EMPTY_DECLARATION), the stamp cannot answer a declared field
            (UNKNOWN), or the values differ (MISMATCH).
    """
    if declared.is_empty():
        raise ProbeTargetMismatchError(
            kind=EnumProbeTargetDisagreement.EMPTY_DECLARATION,
            target_name=declared.target_name,
            detail=(
                f"the declaration read from {declared.declared_by!r} asserts "
                "no comparable field (no host, no locus, no package commits), "
                "so asserting against it would compare nothing and pass "
                "unconditionally"
            ),
        )

    compared: list[str] = []

    if declared.host is not None:
        compared.append("host")
        if stamped.host != declared.host:
            raise ProbeTargetMismatchError(
                kind=EnumProbeTargetDisagreement.MISMATCH,
                target_name=declared.target_name,
                detail=(
                    f"host: stamped {stamped.host!r} != declared "
                    f"{declared.host!r} (declared by {declared.declared_by!r}) "
                    "-- this execution ran on a different machine than the "
                    "target it claims to prove"
                ),
            )

    if declared.locus_kind is not None:
        compared.append("locus_kind")
        if stamped.locus_kind is not declared.locus_kind:
            raise ProbeTargetMismatchError(
                kind=EnumProbeTargetDisagreement.MISMATCH,
                target_name=declared.target_name,
                detail=(
                    f"locus_kind: stamped {stamped.locus_kind.value!r} != "
                    f"declared {declared.locus_kind.value!r} -- selecting a "
                    "shared transport does not relocate execution (OMN-17295)"
                ),
            )

    if declared.execution_locus is not None:
        compared.append("execution_locus")
        if stamped.execution_locus != declared.execution_locus:
            raise ProbeTargetMismatchError(
                kind=EnumProbeTargetDisagreement.MISMATCH,
                target_name=declared.target_name,
                detail=(
                    f"execution_locus: stamped {stamped.execution_locus!r} != "
                    f"declared {declared.execution_locus!r}"
                ),
            )

    for name in sorted(declared.packages):
        expected = declared.packages[name]
        compared.append(f"package:{name}")
        entry = stamped.package(name)
        if entry is None:
            raise ProbeTargetMismatchError(
                kind=EnumProbeTargetDisagreement.UNKNOWN,
                target_name=declared.target_name,
                detail=(
                    f"package {name!r}: the target declares commit "
                    f"{expected} but the stamp is silent about this package, "
                    "so whether the code under test was present cannot be "
                    "determined -- restamp with this package included"
                ),
            )
        if entry.commit is None:
            raise ProbeTargetMismatchError(
                kind=EnumProbeTargetDisagreement.UNKNOWN,
                target_name=declared.target_name,
                detail=(
                    f"package {name!r}: the target declares commit "
                    f"{expected} but the stamp names no commit "
                    f"(source={entry.source.value}, version="
                    f"{entry.version!r}) -- a version string is not evidence "
                    "of content"
                ),
            )
        if entry.commit != expected:
            raise ProbeTargetMismatchError(
                kind=EnumProbeTargetDisagreement.MISMATCH,
                target_name=declared.target_name,
                detail=(
                    f"package {name!r}: stamped {entry.commit} != declared "
                    f"{expected} -- the executing code is not the code the "
                    "target declares it is running"
                ),
            )

    return ModelProbeTargetVerdict(
        target_name=declared.target_name,
        declared_by=declared.declared_by,
        compared_fields=compared,
    )
