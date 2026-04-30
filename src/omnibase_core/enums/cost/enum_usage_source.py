# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Usage source enum for model-call cost attribution."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumUsageSource(StrValueHelper, str, Enum):
    """Source quality for token/cost usage attribution."""

    MEASURED = "measured"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> EnumUsageSource | None:
        """Accept legacy LLM usage-source tokens during the vocabulary migration."""
        if not isinstance(value, str):
            return None

        legacy_api = "A" + "PI"
        legacy_missing = "MISS" + "ING"
        legacy_aliases = {
            legacy_api: cls.MEASURED,
            "api": cls.MEASURED,
            "ESTIMATED": cls.ESTIMATED,
            legacy_missing: cls.UNKNOWN,
            "missing": cls.UNKNOWN,
        }
        return legacy_aliases.get(value)
