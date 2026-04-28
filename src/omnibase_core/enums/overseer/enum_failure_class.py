# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumFailureClass(StrEnum):
    """Classification of failure types for overseer error routing.

    Each failure class maps to a distinct recovery strategy in the overseer.
    """

    TRANSIENT = "transient"
    """Temporary failure — retryable (network timeout, rate limit)."""

    PERMANENT = "permanent"
    """Unrecoverable failure — do not retry (invalid input, auth denied)."""

    RESOURCE_EXHAUSTION = "resource_exhaustion"
    """Resource limit hit — backoff or scale (OOM, disk full, quota)."""

    TIMEOUT = "timeout"
    """Operation exceeded time budget."""

    DEPENDENCY = "dependency"
    """Upstream dependency unavailable or failing."""

    CONFIGURATION = "configuration"
    """Misconfiguration detected — requires human intervention."""

    DATA_INTEGRITY = "data_integrity"
    """Data corruption or constraint violation."""

    UNKNOWN = "unknown"
    """Unclassified failure — fallback category."""


__all__: list[str] = ["EnumFailureClass"]
