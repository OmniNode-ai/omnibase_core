# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Re-export shim for :class:`ModelFailFastDetails`.

The canonical definition was relocated DOWN into the foundation-layer
``omnibase_core.errors`` package (OMN-14335, OMN-3210) alongside
``ModelOnexError`` to sever the ``errors -> models`` import back-edge. This
module preserves the historical
``omnibase_core.models.errors.model_fail_fast_details`` import path. New code
should import from ``omnibase_core.errors.model_fail_fast_details``.
"""

from omnibase_core.errors.model_fail_fast_details import (  # re-export
    ModelFailFastDetails,
)

__all__ = ["ModelFailFastDetails"]
