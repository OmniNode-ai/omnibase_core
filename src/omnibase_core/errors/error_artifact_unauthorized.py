# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed authorization error for the content-addressed artifact store."""


class ArtifactUnauthorizedError(Exception):
    """Raised when a restricted artifact is read without authorization."""


__all__ = ["ArtifactUnauthorizedError"]
