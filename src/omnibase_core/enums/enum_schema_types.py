"""
Schema type enumeration for AST generation.

Provides standardized mapping between JSON schema types and Python types.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSchemaTypes(StrValueHelper, str, Enum):
    """Schema type enumeration for type-safe AST generation."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class EnumPythonTypes(StrValueHelper, str, Enum):
    """Python type enumeration for code generation."""

    # Primitive types
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"

    # Collection types
    LIST_STRING = "List[str]"
    LIST_INT = "List[int]"
    LIST_FLOAT = "List[float]"
    LIST_BOOL = "List[bool]"
    DICT_STRING_ANY = "Dict[str, Any]"

    # Core ONEX Models
    MODEL_OBJECT_DATA = "ModelObjectData"
    MODEL_SEMVER = "ModelSemVer"
    MODEL_ONEX_FIELD_MODEL = "ModelOnexFieldModel"

    # Processing Models
    MODEL_PROCESSING_RESULT = "ModelProcessingResult"
    MODEL_PROCESSING_CONFIG = "ModelProcessingConfig"
    MODEL_PROCESSING_METADATA = "ModelProcessingMetadata"

    # Validation Models
    MODEL_VALIDATION_RESULT = "ModelValidationResult"
    MODEL_VALIDATION_CONFIG = "ModelValidationConfig"
    MODEL_VALIDATION_ERROR = "ModelValidationError"
    MODEL_VALIDATION_WARNING = "ModelValidationWarning"
    MODEL_VALIDATION_RULE = "ModelValidationRule"

    # Node Models
    MODEL_NODE_STATUS = "ModelNodeStatus"
    MODEL_NODE_ACTION = "ModelNodeAction"
    MODEL_NODE_ACTION_TYPE = "ModelNodeActionType"
    MODEL_NODE_INFO = "ModelNodeInfo"
    MODEL_NODE_CAPABILITY = "ModelNodeCapability"
    MODEL_NODE_METADATA = "ModelNodeMetadata"

    # Action Models
    MODEL_ACTION = "ModelAction"
    MODEL_ACTION_CATEGORY = "ModelActionCategory"
    MODEL_ACTION_METADATA = "ModelActionMetadata"
    MODEL_ACTION_PAYLOAD = "ModelActionPayload"

    # Error Models
    MODEL_ERROR_DETAIL = "ModelErrorDetail"
    MODEL_ERROR_CONTEXT = "ModelErrorContext"

    # Resource Models
    MODEL_RESOURCE_USAGE = "ModelResourceUsage"
    MODEL_RESOURCE_METRICS = "ModelResourceMetrics"

    # Metric Models
    MODEL_METRICS_DATA = "ModelMetricsData"
    MODEL_METRIC_TAGS = "ModelMetricTags"
    MODEL_PERFORMANCE_METRICS = "ModelPerformanceMetrics"

    # CLI Models
    MODEL_CLI_COMMAND = "ModelCliCommand"
    MODEL_CLI_ARGUMENT = "ModelCliArgument"
    MODEL_CLI_CONFIG = "ModelCliConfig"

    # Schema Models
    MODEL_SCHEMA = "ModelSchema"
    MODEL_CONTRACT_DOCUMENT = "ModelContractDocument"

    # Complex object placeholder (will be replaced by specific types)
    MODEL_COMPLEX_OBJECT = MODEL_OBJECT_DATA  # Explicit alias


__all__ = ["EnumSchemaTypes"]
