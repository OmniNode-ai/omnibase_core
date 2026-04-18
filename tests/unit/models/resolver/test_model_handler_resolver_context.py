# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelHandlerResolverContext (OMN-9195/OMN-9196).

Verifies:
- frozen + extra="forbid" config (plan Step 4/5)
- required-field signature (handler_cls/module/name/contract/node)
- 5 optional fields default to None (plan Acceptance)
- two explicit-dependency fields modeled separately (plan Step 5)
- layering invariant: `object | None` fields accept arbitrary non-protocol sentinels
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.resolver.model_handler_resolver_context import (
    ModelHandlerResolverContext,
)


class _HandlerClassFixture:
    """Dummy handler-like class used as `handler_cls` in tests."""


def _make_minimal_context(**overrides: object) -> ModelHandlerResolverContext:
    """Helper building a minimal valid context with only the required fields."""
    base: dict[str, object] = {
        "handler_cls": _HandlerClassFixture,
        "handler_module": "pkg.mod",
        "handler_name": "HandlerFoo",
        "contract_name": "node_foo",
        "node_name": "node_foo",
    }
    base.update(overrides)
    return ModelHandlerResolverContext(**base)  # type: ignore[arg-type]  # NOTE(OMN-9196): dict[str, object] splat into Pydantic model with typed fields; mypy cannot narrow kwargs from a generic mapping


@pytest.mark.unit
class TestModelHandlerResolverContextFrozen:
    """Frozen/immutable-assignment contract."""

    def test_context_is_frozen(self) -> None:
        """Plan Step 4: mutation must raise ValidationError."""
        ctx = _make_minimal_context()
        with pytest.raises(ValidationError):
            ctx.handler_name = "Mutated"  # type: ignore[misc]  # NOTE(OMN-9196): intentional assignment to frozen field verifies immutability enforcement

    def test_context_rejects_extra_fields(self) -> None:
        """Plan Step 4: extra='forbid' rejects unknown kwargs."""
        with pytest.raises(ValidationError):
            ModelHandlerResolverContext(
                handler_cls=_HandlerClassFixture,
                handler_module="pkg.mod",
                handler_name="HandlerFoo",
                contract_name="node_foo",
                node_name="node_foo",
                unknown_field="x",  # type: ignore[call-arg]  # NOTE(OMN-9196): intentional unknown kwarg verifies extra='forbid' rejection
            )


@pytest.mark.unit
class TestModelHandlerResolverContextOptionalFields:
    """All 5 SPI/runtime-bound fields default to None (acceptance criterion)."""

    def test_context_optional_fields_default_none(self) -> None:
        """Plan Acceptance: test asserts 5 fields default to None."""
        ctx = _make_minimal_context()
        assert ctx.explicit_dependency_shape is None
        assert ctx.materialized_explicit_dependencies is None
        assert ctx.event_bus is None
        assert ctx.container is None
        assert ctx.ownership_query is None


@pytest.mark.unit
class TestModelHandlerResolverContextRequiredFields:
    """Required-field signature fails closed when any core field is missing."""

    @pytest.mark.parametrize(
        "missing_field",
        [
            "handler_cls",
            "handler_module",
            "handler_name",
            "contract_name",
            "node_name",
        ],
    )
    def test_missing_required_field_raises(self, missing_field: str) -> None:
        kwargs: dict[str, object] = {
            "handler_cls": _HandlerClassFixture,
            "handler_module": "pkg.mod",
            "handler_name": "HandlerFoo",
            "contract_name": "node_foo",
            "node_name": "node_foo",
        }
        kwargs.pop(missing_field)
        with pytest.raises(ValidationError):
            ModelHandlerResolverContext(**kwargs)  # type: ignore[arg-type]  # NOTE(OMN-9196): dict[str, object] splat into Pydantic model with typed fields; mypy cannot narrow kwargs from a generic mapping

    @pytest.mark.parametrize(
        "empty_field",
        [
            "handler_module",
            "handler_name",
            "contract_name",
            "node_name",
        ],
    )
    def test_empty_string_fields_rejected(self, empty_field: str) -> None:
        """min_length=1 on string fields — empty string must fail."""
        with pytest.raises(ValidationError):
            _make_minimal_context(**{empty_field: ""})


@pytest.mark.unit
class TestModelHandlerResolverContextExplicitDependencySplit:
    """Two explicit-dependency fields exist and have distinct types."""

    def test_shape_and_materialized_are_separate_fields(self) -> None:
        """Plan Step 5: declarative names-only vs runtime-materialized map."""
        field_names = set(ModelHandlerResolverContext.model_fields.keys())
        assert "explicit_dependency_shape" in field_names
        assert "materialized_explicit_dependencies" in field_names
        # Ensure we have NOT collapsed them into a single legacy field.
        assert "explicit_dependencies" not in field_names

    def test_can_supply_shape_without_materialized(self) -> None:
        """Discovery phase: shape populated, materialized is None."""
        ctx = _make_minimal_context(
            explicit_dependency_shape={"HandlerFoo": ("dep_a", "dep_b")},
        )
        assert ctx.explicit_dependency_shape == {"HandlerFoo": ("dep_a", "dep_b")}
        assert ctx.materialized_explicit_dependencies is None

    def test_can_supply_materialized_without_shape(self) -> None:
        """Runtime: materialized populated, shape may be None."""
        sentinel_dep = object()
        ctx = _make_minimal_context(
            materialized_explicit_dependencies={
                "HandlerFoo": {"dep_a": sentinel_dep},
            },
        )
        assert ctx.materialized_explicit_dependencies is not None
        assert (
            ctx.materialized_explicit_dependencies["HandlerFoo"]["dep_a"]
            is sentinel_dep
        )
        assert ctx.explicit_dependency_shape is None


@pytest.mark.unit
class TestModelHandlerResolverContextLayeringInvariant:
    """Layering invariant: object|None fields accept non-protocol objects.

    Verifies that construction does NOT narrow to any SPI protocol — any
    Python object is accepted at the core layer; protocol conformance is
    enforced at the infra boundary (plan §Layering Invariants).
    """

    def test_accepts_arbitrary_objects_for_spi_fields(self) -> None:
        bus_sentinel = object()
        container_sentinel = object()
        ownership_sentinel = object()
        ctx = _make_minimal_context(
            event_bus=bus_sentinel,
            container=container_sentinel,
            ownership_query=ownership_sentinel,
        )
        assert ctx.event_bus is bus_sentinel
        assert ctx.container is container_sentinel
        assert ctx.ownership_query is ownership_sentinel


@pytest.mark.unit
class TestModelHandlerResolverContextExportedFromPackage:
    """Re-export hygiene: model importable from `omnibase_core.models.resolver`."""

    def test_reexport_from_resolver_package(self) -> None:
        from omnibase_core.models.resolver import (
            ModelHandlerResolverContext as ReexportedCtx,
        )

        assert ReexportedCtx is ModelHandlerResolverContext


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
