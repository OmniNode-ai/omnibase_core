# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelHandlerResolverContext - input to HandlerResolver.resolve().

Frozen Pydantic model carrying the construction-time inputs required for a
single handler resolution decision. Populated at auto-wiring time (manifest
load) and passed to the resolver without mutation.

Justification for introducing this model rather than reusing `PreparedWiring`:
`PreparedWiring` represents the *output* of wiring (post-resolution:
callback, category, routes). `ModelHandlerResolverContext` is the *input*.
Different phase, different data. See the plan §"Known Types Inventory" at
`docs/plans/2026-04-18-handler-resolver-architecture.md`.

Layering (permanent, see §"Layering Invariants" in the plan):
    `ownership_query`, `container`, `event_bus`, and the SPI-owned
    resolver-produced `handler_instance` are typed `object | None`. The
    repository layering rule forbids `omnibase_core` from importing
    `omnibase_spi`. Runtime `isinstance(ownership_query,
    ProtocolHandlerOwnershipQuery)` checks are performed at the infra
    boundary in `handler_wiring.py`, not here. Do NOT narrow these fields
    without first lifting the layering constraint at the plan level.

Scope (by partner ruling):
    This model carries only the inputs required for construction-time
    resolution. Logging, metrics, feature flags, runtime identity, backend
    registries, and post-resolution report state are explicitly out of
    scope. Additions require a plan revision, not a one-line field append.

Explicit dependencies split into TWO fields intentionally:
    - `explicit_dependency_shape` — declarative names only, populated by
      `discover_contracts()`. Safe to carry in a frozen manifest; never
      constructs anything.
    - `materialized_explicit_dependencies` — runtime-filled per-handler
      dep map produced by `create_registry(...)` at wiring time.
    Discovery touches only the former; the resolver consumes only the
    latter for construction.
"""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field


class ModelHandlerResolverContext(BaseModel):
    """Input to `HandlerResolver.resolve()` — frozen, extra-forbidden."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    handler_cls: type = Field(
        ...,
        description="Handler class (already imported) to resolve to an instance.",
    )
    handler_module: str = Field(
        ...,
        min_length=1,
        description="Fully-qualified module path of the handler class.",
    )
    handler_name: str = Field(
        ...,
        min_length=1,
        description="Handler class name, used in wiring-report identifiers.",
    )
    contract_name: str = Field(
        ...,
        min_length=1,
        description="Discovered contract name owning this handler declaration.",
    )
    node_name: str = Field(
        ...,
        min_length=1,
        description="Node name whose registry declares this handler.",
    )
    # Declarative: dependency names per handler, populated by discovery.
    explicit_dependency_shape: Mapping[str, tuple[str, ...]] | None = Field(
        default=None,
        description=(
            "Declarative per-handler dependency names. Safe to carry in a "
            "frozen manifest; never constructs anything. Populated by "
            "discover_contracts() (Task 6)."
        ),
    )
    # Runtime: materialized per-handler dep maps, filled by create_registry.
    materialized_explicit_dependencies: Mapping[str, Mapping[str, object]] | None = (
        Field(
            default=None,
            description=(
                "Runtime-filled per-handler dependency map produced by "
                "create_registry(...) at wiring time. Consumed by the "
                "resolver for Step 2 construction."
            ),
        )
    )
    event_bus: object | None = Field(
        default=None,
        description=(
            "Event-bus candidate. Typed object | None per layering "
            "invariants; narrowed at the infra boundary, not here."
        ),
    )
    container: object | None = Field(
        default=None,
        description=(
            "DI container candidate. Typed object | None per layering "
            "invariants; narrowed at the infra boundary."
        ),
    )
    # ownership_query: typed as object | None. See the plan's
    # "Layering Invariants" section — the SPI protocol lives in omnibase_spi
    # and cannot be referenced from omnibase_core without violating the
    # compat -> core -> spi -> infra dependency direction.
    ownership_query: object | None = Field(
        default=None,
        description=(
            "Local-ownership query answering 'is this handler's parent "
            "node hosted in this runtime?'. Typed object | None "
            "permanently per layering invariants."
        ),
    )


__all__ = ["ModelHandlerResolverContext"]
