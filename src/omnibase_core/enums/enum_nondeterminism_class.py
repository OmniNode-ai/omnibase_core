# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Nondeterminism classification for mixin-to-handler migration."""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNondeterminismClass(StrValueHelper, str, Enum):
    """Classification of nondeterminism sources in mixins.

    Used during mixin-to-handler migration to determine whether a mixin
    can be safely converted to a pure compute handler or requires an
    effect handler wrapper.
    """

    DETERMINISTIC = "deterministic"
    """Pure deterministic logic. Same input always produces same output."""

    TIME = "time"
    """Uses time-dependent operations (datetime.now(), timestamps)."""

    RANDOM = "random"
    """Uses random or unique ID generation (random.random(), uuid4())."""

    NETWORK = "network"
    """Performs network I/O (HTTP calls, sockets, Kafka publishing)."""

    EXTERNAL_STATE = "external_state"
    """Reads external state (environment variables, config files, database)."""

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensure exhaustive handling in match statements.

        Uses AssertionError instead of ModelOnexError to avoid
        circular imports in the enum module.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumNondeterminismClass"]
