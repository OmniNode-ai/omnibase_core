from enum import Enum


class EnumSecurityProfile(str, Enum):
    """Security profile levels for progressive security implementation."""

    SP0_BOOTSTRAP = "SP0_BOOTSTRAP"
    SP1_BASELINE = "SP1_BASELINE"
    SP2_PRODUCTION = "SP2_PRODUCTION"
    SP3_HIGH_ASSURANCE = "SP3_HIGH_ASSURANCE"
