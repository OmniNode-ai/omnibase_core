# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Topic Standard Enumeration.

Enumeration of recognized topic naming standards for ONEX routing.
"""

from enum import Enum, unique


@unique
class EnumTopicStandard(str, Enum):
    """
    Enumeration of recognized topic naming standards.

    ONEX supports multiple topic naming conventions depending on the context
    and deployment environment:

    - ONEX_KAFKA: The canonical ONEX Kafka format: onex.<domain>.<type>
    - ENVIRONMENT_AWARE: Environment-prefixed format: <env>.<domain>.<category>.<version>
    - UNKNOWN: Topic format could not be determined

    Example:
        >>> EnumTopicStandard.ONEX_KAFKA.value
        'onex_kafka'
        >>> str(EnumTopicStandard.ENVIRONMENT_AWARE)
        'environment_aware'
    """

    ONEX_KAFKA = "onex_kafka"
    """ONEX Kafka standard: onex.<domain>.<type>"""

    ENVIRONMENT_AWARE = "environment_aware"
    """Environment-aware format: <env>.<domain>.<category>.<version>"""

    UNKNOWN = "unknown"
    """Topic format could not be determined"""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


__all__ = ["EnumTopicStandard"]
