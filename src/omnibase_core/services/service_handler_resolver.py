# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerResolver — ordered-precedence handler resolution.

Precedence (first match wins):
    1. Local ownership skip — node not hosted here -> skip cleanly
    2. Node registry        — materialized explicit dep map from create_registry
    3. Container DI         — container.get_service(handler_cls)
    4. Event-bus injection  — __init__(self, event_bus) single param
    5. Zero-arg             — handler_cls()
    6. TypeError            — unresolvable (never returns UNRESOLVABLE)

Layering (permanent):
    `omnibase_core` MUST NOT import `omnibase_spi`. The resolver therefore
    duck-types `context.ownership_query.is_owned_here(...)` rather than
    referencing `ProtocolHandlerOwnershipQuery`. Runtime conformance is
    enforced one layer up, at the infra boundary in `handler_wiring.py`
    (Task 5), before the context is constructed. See the plan's
    §"Layering Invariants" for rationale.

Narrow exception handling (Step 3a):
    Only `ServiceResolutionError` (service-not-registered) is treated as a
    container miss and falls through to later precedence steps. Any other
    exception from `container.get_service(...)` — `KeyError`, `AttributeError`,
    `RuntimeError`, etc. — propagates untouched so container-internal bugs
    are never masked as graceful fallback.

Forward-compat namespace (not yet implemented — see
docs/plans/research/2026-04-18-marketplace-dynamic-loading-plans.md:192-199
and memory reference_hot_reload_is_planned.md):
    * hot-reload / late handler registration after boot
    * onex.backends pluggable backend resolution
These will extend `resolve` or add sibling methods in a future phase once
runtime identity and backend contracts are modeled. No stub methods are
reserved here — adding speculative API surface before the contract is
known is a commitment cost that future work would have to rename or delete.
"""

from __future__ import annotations

import inspect
import logging

from omnibase_core.enums.enum_handler_resolution_outcome import (
    EnumHandlerResolutionOutcome,
)
from omnibase_core.errors.error_service_resolution import ServiceResolutionError
from omnibase_core.models.resolver.model_handler_resolution import (
    ModelHandlerResolution,
)
from omnibase_core.models.resolver.model_handler_resolver_context import (
    ModelHandlerResolverContext,
)

logger = logging.getLogger(__name__)

_CONCRETE_PARAM_KINDS = (
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.KEYWORD_ONLY,
)


class HandlerResolver:
    """Ordered-precedence resolver for handler instantiation.

    Pure in its context argument — holds no internal state. Multiple
    concurrent `resolve()` calls on the same instance are safe.
    """

    def resolve(self, context: ModelHandlerResolverContext) -> ModelHandlerResolution:
        """Apply the six-step precedence chain; return a resolution record.

        Raises:
            TypeError: When no precedence path can construct the handler.
                       The error message names the handler and its required
                       constructor parameters to aid debugging.
            ServiceResolutionError: Never — this is caught internally as a
                soft miss and falls through to later steps.
            Exception: Any non-ServiceResolutionError raised by the container
                propagates untouched (container-internal bug, not a miss).
        """
        # Step 1 - local ownership skip (deliberate non-error skip).
        # Duck-typed per layering invariants: core cannot import the spi
        # Protocol. `handler_wiring.py` validates conformance before calling.
        if context.ownership_query is not None and hasattr(
            context.ownership_query, "is_owned_here"
        ):
            is_owned = context.ownership_query.is_owned_here(context.node_name)
            if not is_owned:
                logger.info(
                    "HandlerResolver: skipping %s.%s — node %r not hosted here",
                    context.handler_module,
                    context.handler_name,
                    context.node_name,
                )
                return ModelHandlerResolution(
                    outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP,
                    handler_instance=None,
                    skipped_handler=context.handler_name,
                    skipped_reason=(f"node {context.node_name!r} is not hosted here"),
                )

        # Step 2 - explicit materialized dependency map from node registry.
        mat = context.materialized_explicit_dependencies
        deps_for_this_handler = (
            mat.get(context.handler_name) if mat is not None else None
        )
        if deps_for_this_handler is not None:
            try:
                instance = context.handler_cls(**dict(deps_for_this_handler))
            except TypeError as exc:
                # TypeError is the idiomatic Python signal for a constructor-arg
                # mismatch and matches the handler_cls(**deps) failure mode
                # callers must catch. Wrapping as OnexError would obscure the
                # signature-mismatch diagnostic. Plan §"Task 3 Step 6" (OMN-9199).
                # error-ok: HandlerResolver constructor-arg mismatch surface.
                raise TypeError(
                    f"Handler {context.handler_module}.{context.handler_name} "
                    f"could not be constructed from materialized explicit "
                    f"dependencies: {exc}"
                ) from exc
            _log_overlap_if_any(context, chose="node_registry")
            return ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY,
                handler_instance=instance,
            )

        # Step 3 - container DI (narrow: only service-not-registered falls through).
        if context.container is not None:
            get_service = getattr(context.container, "get_service", None)
            if get_service is not None:
                try:
                    instance = get_service(context.handler_cls)
                except ServiceResolutionError:
                    # Documented miss — fall through to steps 4/5/6.
                    logger.debug(
                        "HandlerResolver: container miss "
                        "(ServiceResolutionError) for %s.%s — trying "
                        "event_bus/zero-arg",
                        context.handler_module,
                        context.handler_name,
                    )
                else:
                    _log_overlap_if_any(context, chose="container")
                    return ModelHandlerResolution(
                        outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_CONTAINER,
                        handler_instance=instance,
                    )

        # Compute concrete required params once for steps 4/5/6.
        sig = inspect.signature(context.handler_cls)
        non_self_required_params = {
            k: v
            for k, v in sig.parameters.items()
            if k != "self"
            and v.kind in _CONCRETE_PARAM_KINDS
            and v.default is inspect.Parameter.empty
        }

        # Step 4 - event_bus injection.
        if context.event_bus is not None and set(non_self_required_params) == {
            "event_bus"
        }:
            instance = context.handler_cls(event_bus=context.event_bus)
            return ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_EVENT_BUS,
                handler_instance=instance,
            )

        # Step 5 - zero-arg.
        if not non_self_required_params:
            instance = context.handler_cls()
            return ModelHandlerResolution(
                outcome=EnumHandlerResolutionOutcome.RESOLVED_VIA_ZERO_ARG,
                handler_instance=instance,
            )

        # Step 6 - unresolvable: HARD FAILURE (not a skip).
        dep_names = list(non_self_required_params)
        # TypeError is the idiomatic signal to handler_wiring.py that no
        # precedence path satisfied the handler's constructor requirements.
        # OnexError would add serialization overhead without improving the
        # caller's recovery surface; this is always a wiring bug, never a
        # recoverable runtime state. Plan §"Task 3 Step 6" (OMN-9199).
        # error-ok: HandlerResolver fail-fast per OMN-8735 invariant.
        raise TypeError(
            f"Handler {context.handler_module}.{context.handler_name} "
            f"requires constructor parameters {dep_names!r} but no "
            f"ownership_query, node registry explicit deps, container, or "
            f"event_bus could satisfy them."
        )


def _log_overlap_if_any(context: ModelHandlerResolverContext, *, chose: str) -> None:
    """Surface architecture smell: multiple precedence paths would have resolved.

    Logs at DEBUG only. Never raises. See plan §"Conflict Semantics".
    """
    shadowed: list[str] = []
    mat = context.materialized_explicit_dependencies
    if chose != "node_registry" and mat is not None and context.handler_name in mat:
        shadowed.append("node_registry")
    if chose != "container" and context.container is not None:
        # We don't re-probe the container here to avoid side effects; a
        # conservative "container present" signal is enough to warrant
        # investigation.
        shadowed.append("container(present)")
    if shadowed:
        logger.debug(
            "HandlerResolver: resolved %s.%s via %s; shadowed paths: %s",
            context.handler_module,
            context.handler_name,
            chose,
            ",".join(shadowed),
        )


__all__ = ["HandlerResolver"]
