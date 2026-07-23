# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Topic-schema delta classification enum (OMN-12621).

Classifies the delta between two topic-schema bindings (old vs new). The
breaking members (``MAJOR_BUMP`` and ``NAMESPACE_RENAME``) require an adjacent
``ModelTopicMigrationContract``.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumTopicSchemaDelta(UtilStrValueHelper, str, Enum):
    """Classification of the delta between two topic-schema bindings."""

    NONE = "none"
    COMPATIBLE = "compatible"
    MAJOR_BUMP = "major_bump"
    NAMESPACE_RENAME = "namespace_rename"

    @property
    def is_breaking(self) -> bool:
        """True if the delta requires a topic-migration contract."""
        return self in (
            EnumTopicSchemaDelta.MAJOR_BUMP,
            EnumTopicSchemaDelta.NAMESPACE_RENAME,
        )


__all__ = ["EnumTopicSchemaDelta"]
