# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Completion generator errors for the registry-driven CLI.

Raised by ServiceCompletionGenerator when a shell completion script cannot be
generated from the catalog.

.. versionadded:: 0.19.0  (OMN-2581)
"""

from __future__ import annotations

__all__ = [
    "CompletionGenerationError",
    "CompletionUnsupportedShellError",
]


class CompletionGenerationError(Exception):
    """Raised when a completion script cannot be generated.

    This indicates a structural problem, such as:
    - An unsupported shell was requested.
    - A schema entry is malformed.

    .. versionadded:: 0.19.0  (OMN-2581)
    """


class CompletionUnsupportedShellError(CompletionGenerationError):
    """Raised when an unsupported shell is requested.

    Supported shells: ``zsh``, ``bash``.

    .. versionadded:: 0.19.0  (OMN-2581)
    """
