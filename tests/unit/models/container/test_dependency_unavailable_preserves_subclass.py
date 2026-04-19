# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression test for OMN-9243 — preserve ServiceResolutionError subclass.

HandlerResolver Step 3 narrowly catches `ServiceResolutionError` (subclass of
`ContainerWiringError`, subclass of `ModelOnexError`) to distinguish
"service-not-registered -> fall through to event_bus/zero-arg" from
"generic wiring failure -> crash boot". Before OMN-9243's fix, the
`get_service_async` except block wrapped every caught exception — including
`ServiceResolutionError` — into a generic `ModelOnexError(DEPENDENCY_UNAVAILABLE)`.
That flattened the subclass and broke the HandlerResolver fallthrough path,
crash-looping the runtime on every boot.

This test pins the post-fix behavior: `ServiceResolutionError` raised inside
`ServiceRegistry.resolve_service()` propagates unchanged out of
`get_service_async`. A generic `RuntimeError` raised there is still wrapped
into `DEPENDENCY_UNAVAILABLE` (to prove the carve-out is narrow).

See:
  - docs/plans/2026-04-19-runtime-permanent-fix-and-regression-guard-part-1.md
    § Task 8
  - docs/tracking/2026-04-19-runtime-hot-patch-snapshots.md § fix #3
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_service_resolution import ServiceResolutionError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class _ProtocolFoo:
    """Placeholder protocol target for resolution (shape is irrelevant — the
    container is mocked to fail before any real resolution happens)."""


def _make_container_with_failing_registry(
    raise_exception: BaseException,
) -> ModelONEXContainer:
    """Build a container whose ServiceRegistry.resolve_service raises `raise_exception`.

    We don't need a real registry for this test — just an object with an
    AsyncMock `resolve_service` that raises, which is exactly what the
    `get_service_async` except clause is designed to handle.
    """
    container = ModelONEXContainer(enable_service_registry=False)
    fake_registry: Any = AsyncMock()
    fake_registry.resolve_service = AsyncMock(side_effect=raise_exception)
    # Bypass the formal initialize_service_registry() path — we only need the
    # resolve_service behavior, not a fully-wired registry.
    container._service_registry = fake_registry
    container._enable_service_registry = True
    return container


@pytest.mark.unit
class TestGetServiceAsyncPreservesServiceResolutionError:
    """Verify the narrow ServiceResolutionError subclass survives the except block."""

    def test_service_resolution_error_propagates_unchanged(self) -> None:
        """A ServiceResolutionError raised by the registry must propagate as-is.

        Before OMN-9243 this was flattened into `ModelOnexError(DEPENDENCY_UNAVAILABLE)`,
        breaking HandlerResolver Step 3 fallthrough. After the fix the narrow
        subclass propagates untouched so resolver fallthrough works.
        """
        # Arrange
        narrow_err = ServiceResolutionError(
            message="No service registered for interface 'ProtocolFoo'.",
            error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
        )
        container = _make_container_with_failing_registry(narrow_err)

        # Act / Assert
        with pytest.raises(ServiceResolutionError) as exc_info:
            asyncio.run(container.get_service_async(_ProtocolFoo))

        # The raised exception IS the ServiceResolutionError subclass — not a
        # wrapped generic ModelOnexError.
        assert type(exc_info.value) is ServiceResolutionError
        assert exc_info.value is narrow_err

    def test_generic_runtime_error_is_still_wrapped_as_dependency_unavailable(
        self,
    ) -> None:
        """Non-ServiceResolutionError exceptions keep the existing wrap behavior.

        Proves the OMN-9243 carve-out is narrow: only ServiceResolutionError
        escapes; generic RuntimeError/KeyError/etc. are still translated into
        DEPENDENCY_UNAVAILABLE so wiring bugs remain loud.
        """
        # Arrange
        container = _make_container_with_failing_registry(
            RuntimeError("unrelated internal failure")
        )

        # Act / Assert
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(container.get_service_async(_ProtocolFoo))

        # Not a ServiceResolutionError — the generic DEPENDENCY_UNAVAILABLE wrap.
        assert not isinstance(exc_info.value, ServiceResolutionError)
        assert exc_info.value.error_code == EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE
