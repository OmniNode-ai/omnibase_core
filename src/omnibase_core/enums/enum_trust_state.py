from enum import Enum, unique


@unique
class EnumTrustState(str, Enum):
    UNTRUSTED = "untrusted"
    TRUSTED = "trusted"
    VERIFIED = "verified"
