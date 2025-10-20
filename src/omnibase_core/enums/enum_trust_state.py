from enum import Enum


class EnumTrustState(str, Enum):
    UNTRUSTED = "untrusted"
    TRUSTED = "trusted"
    VERIFIED = "verified"
