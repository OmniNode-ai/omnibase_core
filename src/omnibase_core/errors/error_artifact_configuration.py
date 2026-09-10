# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed configuration error for the content-addressed artifact store."""


class ArtifactConfigurationError(ValueError):
    """Raised when an artifact-store request has an invalid configuration.

    Inherits :class:`ValueError` so existing callers that catch the standard
    configuration boundary continue to behave identically.
    """


__all__ = ["ArtifactConfigurationError"]
