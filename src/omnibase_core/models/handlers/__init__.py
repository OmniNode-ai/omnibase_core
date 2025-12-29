# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler models module.

This module provides models and utilities for handler type metadata,
which describes replay behavior, security requirements, and execution
semantics for different handler categories.

Usage:
    >>> from omnibase_core.models.handlers import (
    ...     ModelHandlerTypeMetadata,
    ...     get_handler_type_metadata,
    ...     ProtocolHandlerTypeResolver,
    ... )
    >>> from omnibase_core.enums import EnumHandlerTypeCategory
    >>>
    >>> # Get metadata for a handler category
    >>> metadata = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
    >>> metadata.is_replay_safe
    True
    >>> metadata.allows_caching
    True

See Also:
    - :class:`~omnibase_core.enums.enum_handler_type_category.EnumHandlerTypeCategory`:
      Behavioral classification of handlers (COMPUTE, EFFECT, NONDETERMINISTIC_COMPUTE)
    - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
      External system classification (HTTP, DATABASE, etc.)
"""

from omnibase_core.models.handlers.model_handler_type_metadata import (
    ModelHandlerTypeMetadata,
    get_handler_type_metadata,
)
from omnibase_core.protocols.handlers.protocol_handler_type_resolver import (
    ProtocolHandlerTypeResolver,
)

__all__ = [
    "ModelHandlerTypeMetadata",
    "get_handler_type_metadata",
    "ProtocolHandlerTypeResolver",
]
