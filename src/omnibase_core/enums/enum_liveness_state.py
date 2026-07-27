# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Demand-aware liveness state enumeration.

OMN-15126 implementation of the OMN-14845 design
(``docs/design/2026-07-20-demand-aware-liveness-state-machine-design.md``,
omni_home#201, section 3.1). Five states, fail-closed by construction: only
``HEALTHY`` satisfies a mandatory L2/L3 transition. Balanced Kafka topic
offsets or a green process cannot certify liveness by themselves — this state
machine requires an exact input-event-to-terminal-event-to-projection
key/value join for ``HEALTHY``, and treats "no demand this cycle" and
"cannot resolve a liveness claim" as distinct, explicit, non-passing states
rather than folding either into ``RED``.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumLivenessState"]


@unique
class EnumLivenessState(UtilStrValueHelper, str, Enum):
    """State produced by the demand-aware liveness evaluation pipeline (design §3.2).

    - ``NOT_READY``: the registry entry or its declared demand source is
      missing, unreadable, or fails validation/query. No liveness claim is
      possible. Blocks.
    - ``NO_DEMAND``: the demand source was queried successfully and returned
      zero eligible demand for the evaluation window, AND a prior ``HEALTHY``
      receipt for this surface is still within its freshness SLO. The surface
      may be perfectly correct; there was simply nothing to prove this cycle.
      Blocks a mandatory transition until a verifier injects bounded synthetic
      demand and obtains ``HEALTHY``.
    - ``HEALTHY``: at least one eligible-demand correlation was matched
      end-to-end (input event -> terminal event -> exact projection
      key/value) inside the surface's declared freshness/error budget.
      Passes.
    - ``STALE``: zero eligible demand this cycle AND no ``HEALTHY`` receipt on
      record within ``freshness_slo_seconds`` (demand-independent: a surface
      with a stale-or-absent proof record is ``STALE`` regardless of whether
      this cycle happens to have demand). Blocks.
    - ``RED``: eligible demand existed and was checked, and the failed ratio
      of checked correlations exceeded the registry's declared
      ``error_budget_ratio``. Blocks.
    """

    NOT_READY = "not_ready"
    NO_DEMAND = "no_demand"
    HEALTHY = "healthy"
    STALE = "stale"
    RED = "red"
