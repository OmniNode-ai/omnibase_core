# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Selection-reason enum for the Context Authority Rule (OMN-12843 / M3).

Every context factor selected for per-run injection carries a typed reason so
that injection is auditable: there is no "hidden authority". The reason answers
*why this factor was chosen*, paired in the Authority 5-tuple with the factor,
its stable source id, its measured effectiveness score, and the experiment
cohort (if any).

Semantics:

* ``POLICY_EFFECTIVENESS`` — selected because its measured effectiveness score
  (resolved from the M2 capsule store) ranked it in.
* ``POLICY_REQUIRED_FACTOR`` — declared required by the profile; admitted by
  policy and stamped (auditable, not silent).
* ``EXPERIMENT_ASSIGNMENT`` — a forced/arm-fixed selection under an active
  experiment cohort. Permitted ONLY when a cohort id is present.
* ``EXPLORATION`` — cold-start / decay re-trial (the M4 explore path). The
  reason is reserved here; the bandit logic lands in M4.
* ``FALLBACK_NO_SCORE`` — the candidate has no M2 score yet. Explicit, not
  silent: ``effectiveness_score`` is ``None`` only with this reason.
"""

from __future__ import annotations

from enum import StrEnum


class EnumSelectionReason(StrEnum):
    """Typed authority reason stamped on each selected context factor."""

    POLICY_EFFECTIVENESS = "policy_effectiveness"
    POLICY_REQUIRED_FACTOR = "policy_required_factor"
    EXPERIMENT_ASSIGNMENT = "experiment_assignment"
    EXPLORATION = "exploration"
    FALLBACK_NO_SCORE = "fallback_no_score"


__all__ = [
    "EnumSelectionReason",
]
