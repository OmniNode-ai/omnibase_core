# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ServiceLocalHandlerOwnershipQuery.

Covers the Phase 1 local-ownership semantics: "hosted here" == "node_name is in
the frozen set of locally discovered contracts." No SQL, no projection reads.

Layering note (OMN-9200 plan §Layering Invariants):
    omnibase_core MUST NOT import omnibase_spi. The protocol-conformance check
    (isinstance against ProtocolHandlerOwnershipQuery) lives under
    omnibase_infra/tests/unit/runtime/ — here we verify the duck-typed shape
    only.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.services.service_local_handler_ownership_query import (
    ServiceLocalHandlerOwnershipQuery,
)


@pytest.mark.unit
def test_returns_true_for_locally_discovered_node() -> None:
    svc = ServiceLocalHandlerOwnershipQuery(
        local_node_names=frozenset({"node_foo", "node_bar"})
    )
    assert svc.is_owned_here("node_foo") is True


@pytest.mark.unit
def test_returns_false_for_unknown_node() -> None:
    svc = ServiceLocalHandlerOwnershipQuery(local_node_names=frozenset({"node_foo"}))
    assert svc.is_owned_here("node_other") is False


@pytest.mark.unit
def test_empty_local_set_rejects_everything() -> None:
    svc = ServiceLocalHandlerOwnershipQuery(local_node_names=frozenset())
    assert svc.is_owned_here("node_foo") is False
    assert svc.is_owned_here("") is False


@pytest.mark.unit
def test_is_owned_here_is_deterministic_and_pure() -> None:
    svc = ServiceLocalHandlerOwnershipQuery(local_node_names=frozenset({"a"}))
    assert svc.is_owned_here("a") is True
    assert svc.is_owned_here("a") is True  # idempotent
    assert svc.is_owned_here("b") is False
    assert svc.is_owned_here("b") is False  # idempotent


@pytest.mark.unit
def test_is_owned_here_has_duck_typed_protocol_shape() -> None:
    """Structural shape only — core tests cannot import omnibase_spi.

    The concrete protocol-conformance assertion (isinstance against
    ProtocolHandlerOwnershipQuery) lives in
    omnibase_infra/tests/unit/runtime/test_handler_wiring_resolver_integration.py
    where spi is importable. Here we only verify the method exists and returns
    bool, matching the duck-typed contract the resolver depends on.
    """
    import inspect

    svc = ServiceLocalHandlerOwnershipQuery(local_node_names=frozenset({"a"}))
    assert hasattr(svc, "is_owned_here")
    assert callable(svc.is_owned_here)
    assert isinstance(svc.is_owned_here("a"), bool)

    # Signature: is_owned_here(self, node_name: str) -> bool
    # Note: the implementation uses `from __future__ import annotations`, so
    # inspect.signature surfaces annotations as strings. Resolve eagerly with
    # eval_str=True to compare against the real types.
    sig = inspect.signature(svc.is_owned_here, eval_str=True)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "node_name"
    assert params[0].annotation is str
    assert sig.return_annotation is bool


@pytest.mark.unit
def test_local_node_names_is_immutable_post_construction() -> None:
    """Pydantic frozen config forbids reassigning fields after construction."""
    svc = ServiceLocalHandlerOwnershipQuery(local_node_names=frozenset({"a"}))
    with pytest.raises(ValidationError):
        svc.local_node_names = frozenset({"b"})  # type: ignore[misc]


@pytest.mark.unit
def test_frozenset_field_rejects_mutation_attempts() -> None:
    """The stored frozenset itself has no mutation API — sanity check."""
    svc = ServiceLocalHandlerOwnershipQuery(local_node_names=frozenset({"a"}))
    # frozenset has no .add() — AttributeError, not silent success
    with pytest.raises(AttributeError):
        svc.local_node_names.add("b")  # type: ignore[attr-defined]
