# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed quota error for the content-addressed artifact store."""


class ArtifactQuotaExceededError(Exception):
    """Raised when a write would exceed a per-write or per-scope size quota.

    No bytes are persisted when this is raised — the write fails closed with no
    silent truncation.
    """


__all__ = ["ArtifactQuotaExceededError"]
