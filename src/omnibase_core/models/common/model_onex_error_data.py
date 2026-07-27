# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Re-export shim for :class:`_ModelOnexErrorData`.

The canonical definition was relocated DOWN into the foundation-layer
``omnibase_core.errors`` package (OMN-14335, OMN-3210) — it is the internal
structured-data companion of ``ModelOnexError`` and moved with it to sever the
``errors -> models`` import back-edge. This module preserves the historical
``omnibase_core.models.common.model_onex_error_data`` import path. New code
should import from ``omnibase_core.errors.model_onex_error_data``.
"""

from omnibase_core.errors.model_onex_error_data import (  # noqa: F401  (re-export)
    _ModelOnexErrorData,
)

__all__: list[str] = []
