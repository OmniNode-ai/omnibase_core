"""
Enum for role levels.
"""

from enum import Enum


class EnumRoleLevel(str, Enum):
    """Role levels for users."""

    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    STAFF = "staff"
    DISTINGUISHED = "distinguished"
    FELLOW = "fellow"
