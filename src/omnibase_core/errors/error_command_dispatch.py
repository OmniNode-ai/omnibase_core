# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Command dispatch error for the registry-driven CLI.

Raised by ServiceCommandDispatcher when dispatch configuration is invalid or an
unimplemented invocation type (stub) is invoked.

.. versionadded:: 0.19.0  (OMN-2553)
"""

from __future__ import annotations

__all__ = [
    "CommandDispatchError",
]


class CommandDispatchError(Exception):
    """Raised when dispatch configuration is invalid or a stub is invoked.

    This is distinct from a runtime dispatch failure (which is captured in
    ``CommandDispatchResult.success = False``).  This exception indicates a
    programming error — e.g., dispatching an HTTP_ENDPOINT command without
    an implementation registered, or calling KAFKA_EVENT dispatch without
    a configured Kafka producer.

    .. versionadded:: 0.19.0  (OMN-2553)
    """
