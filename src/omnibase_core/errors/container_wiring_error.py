# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ContainerWiringError — base class for DI-container-wiring failures.

Hierarchy:
    ModelOnexError                          (omnibase_core.models.errors)
        └── ContainerWiringError            (this module)
                └── ServiceResolutionError  (error_service_resolution.py)

Reserved namespace for future container-wiring-specific errors (registration
conflicts, configuration issues, etc.). Callers should typically catch a more
specific subclass (currently only `ServiceResolutionError`).

Design note: kept intentionally minimal — no error-code enum plumbing or
extra metadata fields. Sole purpose is to give the resolver a narrow
inheritance target for `except` clauses without swallowing unrelated
container-internal bugs. See
`docs/plans/2026-04-18-handler-resolver-architecture.md` §"Task 3 Step 3a".
"""

from __future__ import annotations

from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ContainerWiringError(ModelOnexError):
    """Generic DI-container-wiring failure — base class for narrower errors."""


__all__ = ["ContainerWiringError"]
