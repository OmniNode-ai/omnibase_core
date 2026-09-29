# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Operations supported by declared broker grants."""

from enum import StrEnum, unique


@unique
class EnumBrokerGrantOperation(StrEnum):
    """An operation a broker grant permits."""

    READ = "read"
    WRITE = "write"
    DESCRIBE = "describe"


__all__ = ["EnumBrokerGrantOperation"]
