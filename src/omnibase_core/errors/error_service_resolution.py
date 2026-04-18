# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ServiceResolutionError — the requested service is not registered.

This is the narrow "soft miss" that `HandlerResolver` (in
`omnibase_core.services.service_handler_resolver`) catches and treats as a
fallthrough signal to later precedence steps (event_bus / zero-arg). Any
other container exception (KeyError, AttributeError, RuntimeError, or an
unrelated `ContainerWiringError` subclass) propagates untouched so
container-internal bugs are never silenced.

Hierarchy:
    ModelOnexError                          (omnibase_core.models.errors)
        └── ContainerWiringError            (container_wiring_error.py)
                └── ServiceResolutionError  (this module)

Kept intentionally minimal — no error-code enum plumbing or extra metadata
fields. Sole purpose is narrow `except` targeting for the resolver
fallthrough. Additional fields require a plan revision, not a drive-by
append. See `docs/plans/2026-04-18-handler-resolver-architecture.md`
§"Task 3 Step 3a".
"""

from __future__ import annotations

from omnibase_core.errors.container_wiring_error import ContainerWiringError


class ServiceResolutionError(ContainerWiringError):
    """The requested service is not registered in the DI container."""


__all__ = ["ServiceResolutionError"]
