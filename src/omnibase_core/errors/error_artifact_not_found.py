# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed missing-artifact error for the content-addressed artifact store."""


class ArtifactNotFoundError(FileNotFoundError):
    """Raised when an artifact blob or metadata sidecar is absent.

    Inherits :class:`FileNotFoundError` so existing missing-file recovery paths
    retain their established behavior.
    """


__all__ = ["ArtifactNotFoundError"]
