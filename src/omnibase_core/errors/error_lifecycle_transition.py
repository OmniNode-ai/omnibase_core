# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""LifecycleTransitionError — raised when a chain transition violates FSM rules
(OMN-9885)."""


class LifecycleTransitionError(ValueError):
    """Raised when a chain transition violates the dispatch lifecycle FSM rules."""


__all__ = ["LifecycleTransitionError"]
