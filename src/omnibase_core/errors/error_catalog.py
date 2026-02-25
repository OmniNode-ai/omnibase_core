# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Catalog error hierarchy for the registry-driven CLI Command Catalog.

These errors are raised by ServiceCatalogManager during catalog
materialization (fetch, verify, cache, load) operations.

.. versionadded:: 0.19.0  (OMN-2544)
"""

from __future__ import annotations

__all__ = [
    "CatalogError",
    "CatalogLoadError",
    "CatalogSignatureError",
    "CatalogVersionError",
]


class CatalogError(Exception):
    """Base error for all catalog failures.

    Raised by ServiceCatalogManager when a catalog operation fails.
    Catch this base class to handle all catalog errors uniformly.

    .. versionadded:: 0.19.0  (OMN-2544)
    """


class CatalogLoadError(CatalogError):
    """Raised when the cache file is missing, corrupt, or unreadable.

    Callers should instruct the user to run ``omn refresh`` to rebuild
    the catalog cache.

    .. versionadded:: 0.19.0  (OMN-2544)
    """


class CatalogSignatureError(CatalogError):
    """Raised when Ed25519 signature verification fails on load or refresh.

    This is a hard error — not a warning.  It indicates either:
    - The cached catalog file has been tampered with.
    - The publisher's signing key has changed since the last refresh.

    Callers should instruct the user to run ``omn refresh`` to re-fetch
    and re-verify the catalog from the live registry.

    .. versionadded:: 0.19.0  (OMN-2544)
    """


class CatalogVersionError(CatalogError):
    """Raised when the cached catalog was written by an incompatible CLI version.

    Occurs when ``ServiceCatalogManager.load()`` detects that the cache
    was built for a different CLI version than the current running binary.

    Callers should instruct the user to run ``omn refresh`` to rebuild
    the catalog for the current CLI version.

    .. versionadded:: 0.19.0  (OMN-2544)
    """
