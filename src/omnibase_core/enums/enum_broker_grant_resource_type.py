# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resource types supported by declared broker grants."""

from enum import StrEnum, unique


@unique
class EnumBrokerGrantResourceType(StrEnum):
    """A broker resource to which a principal's grant applies."""

    TOPIC = "topic"
    GROUP = "group"


__all__ = ["EnumBrokerGrantResourceType"]
