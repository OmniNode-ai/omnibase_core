# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structural read surface for content-addressed artifact references."""

from __future__ import annotations

from typing import Protocol


class ArtifactRefProtocol(Protocol):
    """Read-only artifact-reference surface used across layer boundaries."""

    @property
    def ref(self) -> str:
        """Return the content-addressed reference string."""
        ...


__all__ = ["ArtifactRefProtocol"]
