# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Narrow-error contract for `ServiceRegistry.resolve_service` (OMN-9242).

When the caller resolves an interface that has no active registrations, the
registry must raise the narrow :class:`ServiceResolutionError` subclass (not
the generic :class:`ModelOnexError`). The narrow type is what
``HandlerResolver`` Step 3 pattern-matches on to fall through to the
``event_bus`` / zero-arg construction precedence — a broader raise flattens
"service not registered" into every other container failure and breaks
auto-wiring.

The subclass must still be catchable as ``ModelOnexError`` /
``ContainerWiringError`` so existing broad handlers keep working; these tests
lock both properties in.

See ``docs/plans/2026-04-19-runtime-permanent-fix-and-regression-guard-part-1.md``
(Task 7) and fix #2 in ``docs/tracking/2026-04-19-runtime-hot-patch-snapshots.md``.
"""

from __future__ import annotations

import pytest

from omnibase_core.container.container_service_registry import ServiceRegistry
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.container_wiring_error import ContainerWiringError
from omnibase_core.errors.error_service_resolution import ServiceResolutionError
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class _IUnregisteredProtocol:
    """Test-only protocol interface that is never registered."""


class _IRegisteredProtocol:
    """Test-only protocol interface registered then unregistered."""


class _Impl(_IRegisteredProtocol):
    """Trivial implementation used to exercise the unregister path."""


@pytest.mark.unit
class TestRegistryRaisesServiceResolutionError:
    """Narrow-error contract for `resolve_service` unregistered paths."""

    @pytest.mark.asyncio
    async def test_resolve_never_registered_raises_service_resolution_error(
        self, registry: ServiceRegistry
    ) -> None:
        """Resolving an interface that was never registered raises the narrow
        subclass, not the generic ModelOnexError."""
        with pytest.raises(ServiceResolutionError) as exc_info:
            await registry.resolve_service(_IUnregisteredProtocol)

        assert exc_info.value.error_code == EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED
        assert "_IUnregisteredProtocol" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_after_unregister_raises_service_resolution_error(
        self, registry: ServiceRegistry
    ) -> None:
        """Register then unregister; subsequent resolve still raises the
        narrow subclass (not the generic parent)."""
        registration_id = await registry.register_instance(
            interface=_IRegisteredProtocol,
            instance=_Impl(),
            scope="global",
        )
        result = await registry.unregister_service(registration_id)
        assert result is True

        with pytest.raises(ServiceResolutionError):
            await registry.resolve_service(_IRegisteredProtocol)

    @pytest.mark.asyncio
    async def test_service_resolution_error_is_container_wiring_error_subclass(
        self, registry: ServiceRegistry
    ) -> None:
        """Backward-compat: narrow error must still be catchable as the
        parent `ContainerWiringError` / `ModelOnexError`, so broad handlers
        (e.g. decorator error-wrapping) keep working."""
        with pytest.raises(ContainerWiringError) as exc_info:
            await registry.resolve_service(_IUnregisteredProtocol)

        # Explicit subclass assertions — the parent-class catch above already
        # proves isinstance(ContainerWiringError), but we pin both rungs of
        # the hierarchy for future-proofing.
        assert isinstance(exc_info.value, ServiceResolutionError)
        assert isinstance(exc_info.value, ContainerWiringError)
        assert isinstance(exc_info.value, ModelOnexError)
