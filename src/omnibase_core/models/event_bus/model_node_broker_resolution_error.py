# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A node's broker could not be resolved from its contract overlay (OMN-22362)."""

from __future__ import annotations

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelNodeBrokerResolutionError(ModelOnexError):
    """The broker a node is reached on was not declared, or could not be resolved.

    ``onex run-node`` takes its broker from the node's contract overlay and from
    nowhere else: no environment variable, no flag and no packaged default. Raised
    for a missing overlay, an overlay with no ``event_bus``, a malformed
    declaration, a lane the lane declaration does not bind, and an installation
    with no resolver registered. ``overlay_path`` names the overlay that was
    looked at, so the refusal says which file to write; it is ``None`` only when
    no resolver is installed and nothing was looked at.
    """

    def __init__(self, message: str, *, overlay_path: str | None = None) -> None:
        super().__init__(
            message=message,
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            overlay_path=overlay_path,
        )
        self.overlay_path = overlay_path


__all__ = ["ModelNodeBrokerResolutionError"]
