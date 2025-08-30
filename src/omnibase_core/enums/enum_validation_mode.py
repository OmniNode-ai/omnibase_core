from enum import Enum


class EnumValidationMode(Enum):
    """Enumeration of validation modes for tool testing."""

    STRICT = "strict"
    LENIENT = "lenient"
    SMOKE = "smoke"
    REGRESSION = "regression"
    INTEGRATION = "integration"
