from enum import Enum, unique


@unique
class EnumValidationResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"
