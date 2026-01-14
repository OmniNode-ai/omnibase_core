"""
SSL Context Options TypedDict.

SSL context options for connection libraries.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class TypedDictSSLContextOptions(TypedDict, total=False):
    """SSL context options for connection libraries."""

    verify: bool | None
    cert: Path | None
    key: Path | None
    ca_certs: Path | None


__all__ = ["TypedDictSSLContextOptions"]
