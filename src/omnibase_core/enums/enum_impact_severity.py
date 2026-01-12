# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Business impact severity enumeration.

DOCUMENTED EXCEPTION per ADR-006 Status Taxonomy (OMN-1311):
    This enum is intentionally NOT merged into the canonical EnumSeverity because:

    1. **Business Domain**: This enum represents business impact levels, not
       technical severity. Values like HIGH, MEDIUM, LOW, MINIMAL express
       business criticality rather than logging/error severity.

    2. **Different Scale**: Uses a 5-level business impact scale (CRITICAL,
       HIGH, MEDIUM, LOW, MINIMAL) that doesn't map directly to the 6-level
       technical severity scale (DEBUG through FATAL).

    3. **Semantic Difference**: "HIGH impact" is semantically different from
       "ERROR severity". A HIGH business impact issue might only be a WARNING
       technically, and vice versa.

For general-purpose technical severity classification, use EnumSeverity instead:
    from omnibase_core.enums.enum_severity import EnumSeverity

This enum is used for business impact assessment, SLA classification, and
incident prioritization systems.
"""

from enum import Enum, unique


@unique
class EnumImpactSeverity(str, Enum):
    """
    Business impact severity levels.

    Used for assessing and classifying the business impact of issues,
    incidents, or changes. NOT for technical severity classification.
    """

    CRITICAL = "critical"
    """Business-critical impact requiring immediate attention."""

    HIGH = "high"
    """High business impact requiring urgent attention."""

    MEDIUM = "medium"
    """Moderate business impact with manageable urgency."""

    LOW = "low"
    """Low business impact, can be addressed in normal course."""

    MINIMAL = "minimal"
    """Minimal or negligible business impact."""


__all__ = ["EnumImpactSeverity"]
