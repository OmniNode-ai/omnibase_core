# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumHandlerResolutionOutcome - terminal outcomes of HandlerResolver.resolve().

Represents the six terminal branches of the `HandlerResolver` precedence chain
introduced by OMN-9195 (HandlerResolver Architecture Phase 1).

Five values correspond to successful resolution paths (including the
deliberate LOCAL_OWNERSHIP_SKIP non-error path, where the handler's parent
node is not hosted in this runtime). The sixth value (`UNRESOLVABLE`) is a
reserved terminal label; the resolver does NOT return it — it raises
`TypeError` when the precedence chain is exhausted so that OMN-8735's
fail-fast invariant is preserved.

Justification for introducing this enum rather than reusing
`EnumCoreErrorCode`: the outcomes are successful branches of a decision
chain, not error codes. Five of six values are success states. See
`docs/plans/2026-04-18-handler-resolver-architecture.md` §"Known Types
Inventory".
"""

from enum import StrEnum


class EnumHandlerResolutionOutcome(StrEnum):
    """Terminal outcome labels for the HandlerResolver precedence chain.

    Values are lowercase-snake for wire-stable serialization in wiring reports.
    """

    RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP = "resolved_via_local_ownership_skip"
    RESOLVED_VIA_NODE_REGISTRY = "resolved_via_node_registry"
    RESOLVED_VIA_CONTAINER = "resolved_via_container"
    RESOLVED_VIA_EVENT_BUS = "resolved_via_event_bus"
    RESOLVED_VIA_ZERO_ARG = "resolved_via_zero_arg"
    UNRESOLVABLE = "unresolvable"
