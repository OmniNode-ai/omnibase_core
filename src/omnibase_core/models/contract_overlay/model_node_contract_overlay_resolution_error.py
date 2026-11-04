# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A node's contract overlay could not be resolved (OMN-22469)."""

from __future__ import annotations

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelNodeContractOverlayResolutionError(ModelOnexError):
    """A node's contract overlay was unreadable or malformed, or no single resolver answers.

    Raised for an overlay that cannot be read or parsed, a contract section that is not a
    mapping, an installation with no resolver or more than one, and a resolver that answers
    the wrong type. ``overlay_path`` names the overlay that was looked at; it is ``None`` when
    nothing was looked at. A caller never falls back to the packaged contract on this error.
    """

    def __init__(self, message: str, *, overlay_path: str | None = None) -> None:
        super().__init__(
            message=message,
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            overlay_path=overlay_path,
        )
        self.overlay_path = overlay_path


__all__ = ["ModelNodeContractOverlayResolutionError"]
