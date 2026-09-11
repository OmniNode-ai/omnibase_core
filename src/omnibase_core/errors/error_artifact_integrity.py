# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed integrity error for the content-addressed artifact store."""


class ArtifactIntegrityError(ValueError):
    """Raised when stored artifact bytes or metadata fail integrity checks.

    Inherits :class:`ValueError` to preserve the existing corruption boundary
    for callers that already catch standard validation errors.
    """


__all__ = ["ArtifactIntegrityError"]
