# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Distribution source protocol of the node announcement step (OMN-21589)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from importlib.metadata import Distribution
    from pathlib import Path


@runtime_checkable
class ProtocolAnnounceDistributionSource(Protocol):
    """Where the announcer finds installed distributions and their files."""

    def distributions(self) -> tuple[Distribution, ...]:
        """Installed distributions, read from metadata alone."""
        ...

    def search_roots(self) -> tuple[Path, ...]:
        """Directories searched for a contract file beside a package's modules."""
        ...
