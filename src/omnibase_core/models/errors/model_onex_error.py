# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Re-export shim for :class:`ModelOnexError`.

The canonical definition was relocated DOWN into the foundation-layer
``omnibase_core.errors`` package (OMN-14335, OMN-3210) to sever the
``errors -> models`` import back-edge enforced by the import-linter
``core-foundation-no-upward`` contract. This module preserves the historical
``omnibase_core.models.errors.model_onex_error`` import path so the repo-wide
and cross-repo importers keep working unchanged. New code should import from
``omnibase_core.errors.model_onex_error``.
"""

from omnibase_core.errors.model_onex_error import ModelOnexError  # re-export

__all__ = ["ModelOnexError"]
