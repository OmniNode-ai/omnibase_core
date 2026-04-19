# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolver models module.

Frozen Pydantic models supporting the HandlerResolver precedence chain
introduced by OMN-9195 (HandlerResolver Architecture Phase 1). See
`docs/plans/2026-04-18-handler-resolver-architecture.md` for the full spec.
"""

from omnibase_core.models.resolver.model_handler_resolution import (
    ModelHandlerResolution,
)
from omnibase_core.models.resolver.model_handler_resolver_context import (
    ModelHandlerResolverContext,
)

__all__ = [
    "ModelHandlerResolution",
    "ModelHandlerResolverContext",
]
