"""
Retention policy enumeration.

Defines data retention policies for compliance and lifecycle management.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRetentionPolicy(StrValueHelper, str, Enum):
    """
    Enumeration of data retention policies.

    Used for data lifecycle management and compliance requirements.
    """

    # Time-based policies
    INDEFINITE = "indefinite"
    PERMANENT = "permanent"

    # Years-based policies
    ONE_YEAR = "1_year"
    TWO_YEARS = "2_years"
    THREE_YEARS = "3_years"
    FIVE_YEARS = "5_years"
    SEVEN_YEARS = "7_years"
    TEN_YEARS = "10_years"

    # Months-based policies
    ONE_MONTH = "1_month"
    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"

    # Days-based policies
    SEVEN_DAYS = "7_days"
    THIRTY_DAYS = "30_days"
    NINETY_DAYS = "90_days"

    # Event-based policies
    AFTER_PROJECT_COMPLETION = "after_project_completion"
    AFTER_EXPIRATION = "after_expiration"
    AFTER_PROCESSING = "after_processing"

    # Special policies
    IMMEDIATE_DELETE = "immediate_delete"
    NO_RETENTION = "no_retention"
    DEFAULT = "default"
    CUSTOM = "custom"
    UNKNOWN = "unknown"

    @classmethod
    def get_duration_days(cls, policy: EnumRetentionPolicy) -> int | None:
        """Get retention duration in days (None for indefinite/special policies)."""
        mapping = {
            cls.SEVEN_DAYS: 7,
            cls.THIRTY_DAYS: 30,
            cls.NINETY_DAYS: 90,
            cls.ONE_MONTH: 30,
            cls.THREE_MONTHS: 90,
            cls.SIX_MONTHS: 180,
            cls.ONE_YEAR: 365,
            cls.TWO_YEARS: 730,
            cls.THREE_YEARS: 1095,
            cls.FIVE_YEARS: 1825,
            cls.SEVEN_YEARS: 2555,
            cls.TEN_YEARS: 3650,
            cls.IMMEDIATE_DELETE: 0,
            cls.NO_RETENTION: 0,
        }
        return mapping.get(policy)

    @classmethod
    def is_time_based(cls, policy: EnumRetentionPolicy) -> bool:
        """Check if policy is time-based."""
        return policy in {
            cls.SEVEN_DAYS,
            cls.THIRTY_DAYS,
            cls.NINETY_DAYS,
            cls.ONE_MONTH,
            cls.THREE_MONTHS,
            cls.SIX_MONTHS,
            cls.ONE_YEAR,
            cls.TWO_YEARS,
            cls.THREE_YEARS,
            cls.FIVE_YEARS,
            cls.SEVEN_YEARS,
            cls.TEN_YEARS,
        }

    @classmethod
    def is_event_based(cls, policy: EnumRetentionPolicy) -> bool:
        """Check if policy is event-based."""
        return policy in {
            cls.AFTER_PROJECT_COMPLETION,
            cls.AFTER_EXPIRATION,
            cls.AFTER_PROCESSING,
        }

    @classmethod
    def is_permanent(cls, policy: EnumRetentionPolicy) -> bool:
        """Check if policy keeps data permanently."""
        return policy in {
            cls.INDEFINITE,
            cls.PERMANENT,
        }

    @classmethod
    def requires_immediate_action(cls, policy: EnumRetentionPolicy) -> bool:
        """Check if policy requires immediate action."""
        return policy in {
            cls.IMMEDIATE_DELETE,
            cls.NO_RETENTION,
        }

    @classmethod
    def get_compliance_level(cls, policy: EnumRetentionPolicy) -> str:
        """Get compliance level for policy."""
        if cls.is_permanent(policy):
            return "low_compliance"
        if cls.is_time_based(policy):
            return "high_compliance"
        if cls.is_event_based(policy):
            return "medium_compliance"
        if cls.requires_immediate_action(policy):
            return "high_compliance"
        return "unknown_compliance"


# Export the enum
__all__ = ["EnumRetentionPolicy"]
