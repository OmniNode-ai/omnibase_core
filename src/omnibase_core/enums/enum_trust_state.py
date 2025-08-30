from enum import Enum


class TrustStateEnum(str, Enum):
    UNTRUSTED = "untrusted"
    TRUSTED = "trusted"
    VERIFIED = "verified"
