# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnumHealthStatusValue - Typed StrEnum for ModelHealthStatus.status field.
"""

from enum import StrEnum


class EnumHealthStatusValue(StrEnum):
    """Primary health status values for ModelHealthStatus.

    These values correspond to the allowed status strings for
    ModelHealthStatus.status, replacing the previous regex pattern
    validator with typed enum validation.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    CUSTOM = "custom"
