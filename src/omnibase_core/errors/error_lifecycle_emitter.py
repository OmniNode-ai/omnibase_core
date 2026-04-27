# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""LifecycleEmitterError — raised when a state is emitted by the wrong actor
(OMN-9885)."""


class LifecycleEmitterError(ValueError):
    """Raised when a lifecycle state is emitted by an actor that is not its owner."""


__all__ = ["LifecycleEmitterError"]
