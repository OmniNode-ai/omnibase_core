"""Core error codes that can be reused across all ONEX components."""

import re
from enum import unique

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_onex_error_code import EnumOnexErrorCode


@unique
class EnumCoreErrorCode(EnumOnexErrorCode):
    """
    Core error codes that can be reused across all ONEX components.

    These provide common error patterns that don't need to be redefined
    in each node's error_codes.py module.

    Error Code Format: ONEX_<COMPONENT>_<NUMBER>_<DESCRIPTION>
    """

    # Generic validation errors (001-020)
    INVALID_PARAMETER = "ONEX_CORE_001_INVALID_PARAMETER"
    MISSING_REQUIRED_PARAMETER = "ONEX_CORE_002_MISSING_REQUIRED_PARAMETER"
    PARAMETER_TYPE_MISMATCH = "ONEX_CORE_003_PARAMETER_TYPE_MISMATCH"
    PARAMETER_OUT_OF_RANGE = "ONEX_CORE_004_PARAMETER_OUT_OF_RANGE"
    VALIDATION_FAILED = "ONEX_CORE_005_VALIDATION_FAILED"
    VALIDATION_ERROR = "ONEX_CORE_006_VALIDATION_ERROR"
    INVALID_INPUT = "ONEX_CORE_007_INVALID_INPUT"
    INVALID_OPERATION = "ONEX_CORE_008_INVALID_OPERATION"
    CONVERSION_ERROR = "ONEX_CORE_009_CONVERSION_ERROR"
    PARSING_ERROR = "ONEX_CORE_010_PARSING_ERROR"

    # File system errors (021-040)
    FILE_NOT_FOUND = "ONEX_CORE_021_FILE_NOT_FOUND"
    FILE_READ_ERROR = "ONEX_CORE_022_FILE_READ_ERROR"
    FILE_WRITE_ERROR = "ONEX_CORE_023_FILE_WRITE_ERROR"
    DIRECTORY_NOT_FOUND = "ONEX_CORE_024_DIRECTORY_NOT_FOUND"
    PERMISSION_DENIED = "ONEX_CORE_025_PERMISSION_DENIED"
    FILE_OPERATION_ERROR = "ONEX_CORE_026_FILE_OPERATION_ERROR"
    FILE_ACCESS_ERROR = "ONEX_CORE_027_FILE_ACCESS_ERROR"
    NOT_FOUND = "ONEX_CORE_028_NOT_FOUND"
    PERMISSION_ERROR = "ONEX_CORE_029_PERMISSION_ERROR"

    # Configuration errors (041-060)
    INVALID_CONFIGURATION = "ONEX_CORE_041_INVALID_CONFIGURATION"
    CONFIGURATION_NOT_FOUND = "ONEX_CORE_042_CONFIGURATION_NOT_FOUND"
    CONFIGURATION_PARSE_ERROR = "ONEX_CORE_043_CONFIGURATION_PARSE_ERROR"
    CONFIGURATION_ERROR = "ONEX_CORE_044_CONFIGURATION_ERROR"

    # Registry errors (061-080)
    REGISTRY_NOT_FOUND = "ONEX_CORE_061_REGISTRY_NOT_FOUND"
    REGISTRY_INITIALIZATION_FAILED = "ONEX_CORE_062_REGISTRY_INITIALIZATION_FAILED"
    ITEM_NOT_REGISTERED = "ONEX_CORE_063_ITEM_NOT_REGISTERED"
    DUPLICATE_REGISTRATION = "ONEX_CORE_064_DUPLICATE_REGISTRATION"
    REGISTRY_VALIDATION_FAILED = "ONEX_CORE_065_REGISTRY_VALIDATION_FAILED"
    REGISTRY_RESOLUTION_FAILED = "ONEX_CORE_066_REGISTRY_RESOLUTION_FAILED"

    # Runtime errors (081-100)
    OPERATION_FAILED = "ONEX_CORE_081_OPERATION_FAILED"
    TIMEOUT_EXCEEDED = "ONEX_CORE_082_TIMEOUT_EXCEEDED"
    RESOURCE_UNAVAILABLE = "ONEX_CORE_083_RESOURCE_UNAVAILABLE"
    UNSUPPORTED_OPERATION = "ONEX_CORE_084_UNSUPPORTED_OPERATION"
    RESOURCE_NOT_FOUND = "ONEX_CORE_085_RESOURCE_NOT_FOUND"
    INVALID_STATE = "ONEX_CORE_086_INVALID_STATE"
    INITIALIZATION_FAILED = "ONEX_CORE_087_INITIALIZATION_FAILED"
    TIMEOUT = "ONEX_CORE_088_TIMEOUT"
    INTERNAL_ERROR = "ONEX_CORE_089_INTERNAL_ERROR"
    NETWORK_ERROR = "ONEX_CORE_090_NETWORK_ERROR"
    MIGRATION_ERROR = "ONEX_CORE_091_MIGRATION_ERROR"
    TIMEOUT_ERROR = "ONEX_CORE_092_TIMEOUT_ERROR"
    RESOURCE_ERROR = "ONEX_CORE_093_RESOURCE_ERROR"
    RUNTIME_ERROR = "ONEX_CORE_094_RUNTIME_ERROR"
    HANDLER_EXECUTION_ERROR = "ONEX_CORE_095_HANDLER_EXECUTION_ERROR"
    EVENT_BUS_ERROR = "ONEX_CORE_096_EVENT_BUS_ERROR"
    CONTRACT_VALIDATION_ERROR = "ONEX_CORE_097_CONTRACT_VALIDATION_ERROR"

    # Test and development errors (101-120)
    TEST_SETUP_FAILED = "ONEX_CORE_101_TEST_SETUP_FAILED"
    TEST_ASSERTION_FAILED = "ONEX_CORE_102_TEST_ASSERTION_FAILED"
    MOCK_CONFIGURATION_ERROR = "ONEX_CORE_103_MOCK_CONFIGURATION_ERROR"
    TEST_DATA_INVALID = "ONEX_CORE_104_TEST_DATA_INVALID"

    # Import and dependency errors (121-140)
    MODULE_NOT_FOUND = "ONEX_CORE_121_MODULE_NOT_FOUND"
    DEPENDENCY_UNAVAILABLE = "ONEX_CORE_122_DEPENDENCY_UNAVAILABLE"
    VERSION_INCOMPATIBLE = "ONEX_CORE_123_VERSION_INCOMPATIBLE"
    IMPORT_ERROR = "ONEX_CORE_124_IMPORT_ERROR"
    DEPENDENCY_ERROR = "ONEX_CORE_125_DEPENDENCY_ERROR"

    # Database errors (131-140)
    DATABASE_CONNECTION_ERROR = "ONEX_CORE_131_DATABASE_CONNECTION_ERROR"
    DATABASE_OPERATION_ERROR = "ONEX_CORE_132_DATABASE_OPERATION_ERROR"
    DATABASE_QUERY_ERROR = "ONEX_CORE_133_DATABASE_QUERY_ERROR"

    # Abstract method and implementation errors (141-160)
    METHOD_NOT_IMPLEMENTED = "ONEX_CORE_141_METHOD_NOT_IMPLEMENTED"
    ABSTRACT_METHOD_CALLED = "ONEX_CORE_142_ABSTRACT_METHOD_CALLED"

    # LLM provider errors (161-180)
    NO_SUITABLE_PROVIDER = "ONEX_CORE_161_NO_SUITABLE_PROVIDER"
    RATE_LIMIT_ERROR = "ONEX_CORE_162_RATE_LIMIT_ERROR"
    AUTHENTICATION_ERROR = "ONEX_CORE_163_AUTHENTICATION_ERROR"
    QUOTA_EXCEEDED = "ONEX_CORE_164_QUOTA_EXCEEDED"
    PROCESSING_ERROR = "ONEX_CORE_165_PROCESSING_ERROR"

    # Type validation errors (181-190)
    TYPE_MISMATCH = "ONEX_CORE_181_TYPE_MISMATCH"
    TYPE_INTROSPECTION_ERROR = "ONEX_CORE_182_TYPE_INTROSPECTION_ERROR"

    # Intelligence and pattern recognition errors (191-200)
    INTELLIGENCE_PROCESSING_FAILED = "ONEX_CORE_191_INTELLIGENCE_PROCESSING_FAILED"
    PATTERN_RECOGNITION_FAILED = "ONEX_CORE_192_PATTERN_RECOGNITION_FAILED"
    CONTEXT_ANALYSIS_FAILED = "ONEX_CORE_193_CONTEXT_ANALYSIS_FAILED"
    LEARNING_ENGINE_FAILED = "ONEX_CORE_194_LEARNING_ENGINE_FAILED"
    INTELLIGENCE_COORDINATION_FAILED = "ONEX_CORE_195_INTELLIGENCE_COORDINATION_FAILED"

    # Service and system health errors (201-220)
    SYSTEM_HEALTH_DEGRADED = "ONEX_CORE_201_SYSTEM_HEALTH_DEGRADED"
    SERVICE_START_FAILED = "ONEX_CORE_202_SERVICE_START_FAILED"
    SERVICE_STOP_FAILED = "ONEX_CORE_203_SERVICE_STOP_FAILED"
    SERVICE_UNHEALTHY = "ONEX_CORE_204_SERVICE_UNHEALTHY"
    SERVICE_UNAVAILABLE = "ONEX_CORE_205_SERVICE_UNAVAILABLE"

    # Security errors (221-230)
    SECURITY_REPORT_FAILED = "ONEX_CORE_221_SECURITY_REPORT_FAILED"
    SECURITY_VIOLATION = "ONEX_CORE_222_SECURITY_VIOLATION"

    # Event and processing errors (231-240)
    EVENT_PROCESSING_FAILED = "ONEX_CORE_231_EVENT_PROCESSING_FAILED"

    # Contract and compliance errors (241-250)
    DEPENDENCY_FAILED = "ONEX_CORE_241_DEPENDENCY_FAILED"
    CONTRACT_VIOLATION = "ONEX_CORE_242_CONTRACT_VIOLATION"

    # Discovery and metadata errors (251-260)
    DISCOVERY_SETUP_FAILED = "ONEX_CORE_251_DISCOVERY_SETUP_FAILED"
    METADATA_LOAD_FAILED = "ONEX_CORE_252_METADATA_LOAD_FAILED"
    DISCOVERY_INVALID_NODE = "ONEX_CORE_253_DISCOVERY_INVALID_NODE"
    DISCOVERY_INVALID_REQUEST = "ONEX_CORE_254_DISCOVERY_INVALID_REQUEST"

    # Thread safety and concurrency errors (261-270)
    THREAD_SAFETY_VIOLATION = "ONEX_CORE_261_THREAD_SAFETY_VIOLATION"

    # Declarative node validation errors (271-280)
    ADAPTER_BINDING_ERROR = "ONEX_CORE_271_ADAPTER_BINDING_ERROR"
    PURITY_VIOLATION_ERROR = "ONEX_CORE_272_PURITY_VIOLATION_ERROR"
    NODE_EXECUTION_ERROR = "ONEX_CORE_273_NODE_EXECUTION_ERROR"
    UNSUPPORTED_CAPABILITY_ERROR = "ONEX_CORE_274_UNSUPPORTED_CAPABILITY_ERROR"

    # Workflow execution limit errors (281-290)
    WORKFLOW_STEP_LIMIT_EXCEEDED = "ONEX_CORE_281_WORKFLOW_STEP_LIMIT_EXCEEDED"
    WORKFLOW_PAYLOAD_SIZE_EXCEEDED = "ONEX_CORE_282_WORKFLOW_PAYLOAD_SIZE_EXCEEDED"
    WORKFLOW_TOTAL_PAYLOAD_EXCEEDED = "ONEX_CORE_283_WORKFLOW_TOTAL_PAYLOAD_EXCEEDED"

    # =========================================================================
    # Orchestrator Error Hierarchy (v1.0.1 Compliance)
    # =========================================================================
    # Three levels of errors as specified in CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md:
    #
    # Level 1 - Structural Validation Errors (291-300)
    #   - Malformed contracts, missing required fields, invalid syntax
    #   - Detected at contract parse time BEFORE any execution
    #   - These should never reach the orchestrator if SPI/Infra contract loading is correct
    #
    # Level 2 - Semantic Validation Errors (301-310)
    #   - Valid structure but invalid semantics (cycles, invalid dependencies, duplicate IDs)
    #   - Detected during validation BEFORE workflow execution begins
    #   - Prevents execution of logically invalid workflows
    #
    # Level 3 - Execution-Time Errors (311-320)
    #   - Runtime failures during workflow/action execution
    #   - Timeouts, step failures, resource unavailability
    #   - Occur AFTER validation passes, during actual execution
    # =========================================================================

    # Level 1: Structural validation errors (291-300)
    ORCHESTRATOR_STRUCT_MISSING_FIELD = (
        "ONEX_CORE_291_ORCHESTRATOR_STRUCT_MISSING_FIELD"
    )
    ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE = (
        "ONEX_CORE_292_ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE"
    )
    ORCHESTRATOR_STRUCT_MALFORMED_CONTRACT = (
        "ONEX_CORE_293_ORCHESTRATOR_STRUCT_MALFORMED_CONTRACT"
    )
    ORCHESTRATOR_STRUCT_INVALID_STEP_TYPE = (
        "ONEX_CORE_294_ORCHESTRATOR_STRUCT_INVALID_STEP_TYPE"
    )
    ORCHESTRATOR_STRUCT_WORKFLOW_NOT_LOADED = (
        "ONEX_CORE_295_ORCHESTRATOR_STRUCT_WORKFLOW_NOT_LOADED"
    )

    # Level 2: Semantic validation errors (301-310)
    ORCHESTRATOR_SEMANTIC_CYCLE_DETECTED = (
        "ONEX_CORE_301_ORCHESTRATOR_SEMANTIC_CYCLE_DETECTED"
    )
    ORCHESTRATOR_SEMANTIC_INVALID_DEPENDENCY = (
        "ONEX_CORE_302_ORCHESTRATOR_SEMANTIC_INVALID_DEPENDENCY"
    )
    ORCHESTRATOR_SEMANTIC_DUPLICATE_STEP_ID = (
        "ONEX_CORE_303_ORCHESTRATOR_SEMANTIC_DUPLICATE_STEP_ID"
    )
    ORCHESTRATOR_SEMANTIC_MISSING_DEPENDENCY = (
        "ONEX_CORE_304_ORCHESTRATOR_SEMANTIC_MISSING_DEPENDENCY"
    )
    ORCHESTRATOR_SEMANTIC_INVALID_EXECUTION_MODE = (
        "ONEX_CORE_305_ORCHESTRATOR_SEMANTIC_INVALID_EXECUTION_MODE"
    )

    # Level 3: Execution-time errors (311-320)
    ORCHESTRATOR_EXEC_STEP_TIMEOUT = "ONEX_CORE_311_ORCHESTRATOR_EXEC_STEP_TIMEOUT"
    ORCHESTRATOR_EXEC_STEP_FAILED = "ONEX_CORE_312_ORCHESTRATOR_EXEC_STEP_FAILED"
    ORCHESTRATOR_EXEC_ACTION_REJECTED = (
        "ONEX_CORE_313_ORCHESTRATOR_EXEC_ACTION_REJECTED"
    )
    ORCHESTRATOR_EXEC_WORKFLOW_TIMEOUT = (
        "ONEX_CORE_314_ORCHESTRATOR_EXEC_WORKFLOW_TIMEOUT"
    )
    ORCHESTRATOR_EXEC_LEASE_EXPIRED = "ONEX_CORE_315_ORCHESTRATOR_EXEC_LEASE_EXPIRED"
    ORCHESTRATOR_EXEC_WORKFLOW_FAILED = (
        "ONEX_CORE_316_ORCHESTRATOR_EXEC_WORKFLOW_FAILED"
    )
    ORCHESTRATOR_EXEC_ITERATION_LIMIT_EXCEEDED = (
        "ONEX_CORE_317_ORCHESTRATOR_EXEC_ITERATION_LIMIT_EXCEEDED"
    )

    # Cache errors (321-330)
    CACHE_BACKEND_ERROR = "ONEX_CORE_321_CACHE_BACKEND_ERROR"
    CACHE_CONNECTION_ERROR = "ONEX_CORE_322_CACHE_CONNECTION_ERROR"
    CACHE_TIMEOUT_ERROR = "ONEX_CORE_323_CACHE_TIMEOUT_ERROR"
    CACHE_OPERATION_FAILED = "ONEX_CORE_324_CACHE_OPERATION_FAILED"
    CACHE_BACKEND_NOT_CONNECTED = "ONEX_CORE_325_CACHE_BACKEND_NOT_CONNECTED"

    # Replay infrastructure errors (331-340)
    REPLAY_RECORD_NOT_FOUND = "ONEX_CORE_331_REPLAY_RECORD_NOT_FOUND"
    REPLAY_NOT_IN_REPLAY_MODE = "ONEX_CORE_332_REPLAY_NOT_IN_REPLAY_MODE"
    REPLAY_INVALID_EFFECT_TYPE = "ONEX_CORE_333_REPLAY_INVALID_EFFECT_TYPE"
    REPLAY_SEQUENCE_EXHAUSTED = "ONEX_CORE_334_REPLAY_SEQUENCE_EXHAUSTED"
    REPLAY_ENFORCEMENT_BLOCKED = "ONEX_CORE_335_REPLAY_ENFORCEMENT_BLOCKED"

    def get_component(self) -> str:
        """Get the component identifier for this error code."""
        return "CORE"

    def get_number(self) -> int:
        """Get the numeric identifier for this error code."""
        # Extract number from error code string (e.g., "ONEX_CORE_001_..." -> 1)
        match = re.search(r"ONEX_CORE_(\d+)_", self.value)
        return int(match.group(1)) if match else 0

    def get_description(self) -> str:
        """Get a human-readable description for this error code."""
        return get_core_error_description(self)

    def get_exit_code(self) -> int:
        """Get the appropriate CLI exit code for this error."""
        return get_exit_code_for_core_error(self)


# Mapping from core error codes to exit codes
CORE_ERROR_CODE_TO_EXIT_CODE: dict[EnumCoreErrorCode, EnumCLIExitCode] = {
    # Validation errors -> ERROR
    EnumCoreErrorCode.INVALID_PARAMETER: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.VALIDATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.VALIDATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INVALID_INPUT: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INVALID_OPERATION: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONVERSION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PARSING_ERROR: EnumCLIExitCode.ERROR,
    # File system errors -> ERROR
    EnumCoreErrorCode.FILE_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.FILE_READ_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.FILE_WRITE_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DIRECTORY_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PERMISSION_DENIED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.FILE_OPERATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.FILE_ACCESS_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PERMISSION_ERROR: EnumCLIExitCode.ERROR,
    # Configuration errors -> ERROR
    EnumCoreErrorCode.INVALID_CONFIGURATION: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONFIGURATION_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONFIGURATION_ERROR: EnumCLIExitCode.ERROR,
    # Registry errors -> ERROR
    EnumCoreErrorCode.REGISTRY_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.REGISTRY_INITIALIZATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ITEM_NOT_REGISTERED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DUPLICATE_REGISTRATION: EnumCLIExitCode.WARNING,
    # Runtime errors -> ERROR
    EnumCoreErrorCode.OPERATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.TIMEOUT_EXCEEDED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.RESOURCE_UNAVAILABLE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.UNSUPPORTED_OPERATION: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.RESOURCE_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INVALID_STATE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INITIALIZATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.TIMEOUT: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INTERNAL_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.NETWORK_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.MIGRATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.TIMEOUT_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.RESOURCE_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.RUNTIME_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.HANDLER_EXECUTION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.EVENT_BUS_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR: EnumCLIExitCode.ERROR,
    # Database errors -> ERROR
    EnumCoreErrorCode.DATABASE_CONNECTION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DATABASE_OPERATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DATABASE_QUERY_ERROR: EnumCLIExitCode.ERROR,
    # LLM provider errors -> ERROR
    EnumCoreErrorCode.NO_SUITABLE_PROVIDER: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.RATE_LIMIT_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.AUTHENTICATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.QUOTA_EXCEEDED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PROCESSING_ERROR: EnumCLIExitCode.ERROR,
    # Type validation errors -> ERROR
    EnumCoreErrorCode.TYPE_MISMATCH: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.TYPE_INTROSPECTION_ERROR: EnumCLIExitCode.ERROR,
    # Intelligence errors -> ERROR
    EnumCoreErrorCode.INTELLIGENCE_PROCESSING_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PATTERN_RECOGNITION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONTEXT_ANALYSIS_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.LEARNING_ENGINE_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INTELLIGENCE_COORDINATION_FAILED: EnumCLIExitCode.ERROR,
    # Service/system health errors -> ERROR
    EnumCoreErrorCode.SYSTEM_HEALTH_DEGRADED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.SERVICE_START_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.SERVICE_STOP_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.SERVICE_UNHEALTHY: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.SERVICE_UNAVAILABLE: EnumCLIExitCode.ERROR,
    # Security errors -> ERROR
    EnumCoreErrorCode.SECURITY_REPORT_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.SECURITY_VIOLATION: EnumCLIExitCode.ERROR,
    # Event processing errors -> ERROR
    EnumCoreErrorCode.EVENT_PROCESSING_FAILED: EnumCLIExitCode.ERROR,
    # Contract/compliance errors -> ERROR
    EnumCoreErrorCode.DEPENDENCY_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONTRACT_VIOLATION: EnumCLIExitCode.ERROR,
    # Discovery/metadata errors -> ERROR
    EnumCoreErrorCode.DISCOVERY_SETUP_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.METADATA_LOAD_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DISCOVERY_INVALID_NODE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DISCOVERY_INVALID_REQUEST: EnumCLIExitCode.ERROR,
    # Thread safety/concurrency errors -> ERROR
    EnumCoreErrorCode.THREAD_SAFETY_VIOLATION: EnumCLIExitCode.ERROR,
    # Declarative node validation errors -> ERROR
    EnumCoreErrorCode.ADAPTER_BINDING_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PURITY_VIOLATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.NODE_EXECUTION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR: EnumCLIExitCode.ERROR,
    # Workflow execution limit errors -> ERROR
    EnumCoreErrorCode.WORKFLOW_STEP_LIMIT_EXCEEDED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.WORKFLOW_PAYLOAD_SIZE_EXCEEDED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.WORKFLOW_TOTAL_PAYLOAD_EXCEEDED: EnumCLIExitCode.ERROR,
    # Orchestrator Level 1 (Structural) errors -> ERROR
    EnumCoreErrorCode.ORCHESTRATOR_STRUCT_MISSING_FIELD: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_STRUCT_MALFORMED_CONTRACT: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_STEP_TYPE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_STRUCT_WORKFLOW_NOT_LOADED: EnumCLIExitCode.ERROR,
    # Orchestrator Level 2 (Semantic) errors -> ERROR
    EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_CYCLE_DETECTED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_INVALID_DEPENDENCY: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_DUPLICATE_STEP_ID: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_MISSING_DEPENDENCY: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_INVALID_EXECUTION_MODE: EnumCLIExitCode.ERROR,
    # Orchestrator Level 3 (Execution) errors -> ERROR
    EnumCoreErrorCode.ORCHESTRATOR_EXEC_STEP_TIMEOUT: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_EXEC_STEP_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_EXEC_ACTION_REJECTED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_EXEC_WORKFLOW_TIMEOUT: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_EXEC_LEASE_EXPIRED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_EXEC_WORKFLOW_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ORCHESTRATOR_EXEC_ITERATION_LIMIT_EXCEEDED: EnumCLIExitCode.ERROR,
    # Cache errors -> ERROR
    EnumCoreErrorCode.CACHE_BACKEND_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CACHE_CONNECTION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CACHE_TIMEOUT_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CACHE_OPERATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CACHE_BACKEND_NOT_CONNECTED: EnumCLIExitCode.ERROR,
    # Replay infrastructure errors -> ERROR
    EnumCoreErrorCode.REPLAY_RECORD_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.REPLAY_NOT_IN_REPLAY_MODE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.REPLAY_INVALID_EFFECT_TYPE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.REPLAY_SEQUENCE_EXHAUSTED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.REPLAY_ENFORCEMENT_BLOCKED: EnumCLIExitCode.ERROR,
}


def get_exit_code_for_core_error(error_code: EnumCoreErrorCode) -> int:
    """
    Get the appropriate CLI exit code for a core error code.

    Args:
        error_code: The EnumCoreErrorCode to map

    Returns:
        The corresponding CLI exit code (integer)
    """
    return CORE_ERROR_CODE_TO_EXIT_CODE.get(error_code, EnumCLIExitCode.ERROR).value


def get_core_error_description(error_code: EnumCoreErrorCode) -> str:
    """
    Get a human-readable description for a core error code.

    Args:
        error_code: The EnumCoreErrorCode to describe

    Returns:
        A human-readable description of the error
    """
    descriptions = {
        EnumCoreErrorCode.INVALID_PARAMETER: "Invalid parameter value",
        EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER: "Required parameter missing",
        EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH: "Parameter type mismatch",
        EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE: "Parameter value out of range",
        EnumCoreErrorCode.VALIDATION_FAILED: "Validation failed",
        EnumCoreErrorCode.VALIDATION_ERROR: "Validation error occurred",
        EnumCoreErrorCode.INVALID_INPUT: "Invalid input provided",
        EnumCoreErrorCode.INVALID_OPERATION: "Invalid operation requested",
        EnumCoreErrorCode.CONVERSION_ERROR: "Data conversion error",
        EnumCoreErrorCode.PARSING_ERROR: "Data parsing error",
        EnumCoreErrorCode.FILE_NOT_FOUND: "File not found",
        EnumCoreErrorCode.FILE_READ_ERROR: "Cannot read file",
        EnumCoreErrorCode.FILE_WRITE_ERROR: "Cannot write file",
        EnumCoreErrorCode.DIRECTORY_NOT_FOUND: "Directory not found",
        EnumCoreErrorCode.PERMISSION_DENIED: "Permission denied",
        EnumCoreErrorCode.FILE_OPERATION_ERROR: "File operation failed",
        EnumCoreErrorCode.FILE_ACCESS_ERROR: "File access error",
        EnumCoreErrorCode.NOT_FOUND: "Resource not found",
        EnumCoreErrorCode.PERMISSION_ERROR: "Permission error",
        EnumCoreErrorCode.INVALID_CONFIGURATION: "Invalid configuration",
        EnumCoreErrorCode.CONFIGURATION_NOT_FOUND: "Configuration not found",
        EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR: "Configuration parse error",
        EnumCoreErrorCode.CONFIGURATION_ERROR: "Configuration error",
        EnumCoreErrorCode.REGISTRY_NOT_FOUND: "Registry not found",
        EnumCoreErrorCode.REGISTRY_INITIALIZATION_FAILED: "Registry initialization failed",
        EnumCoreErrorCode.ITEM_NOT_REGISTERED: "Item not registered",
        EnumCoreErrorCode.DUPLICATE_REGISTRATION: "Duplicate registration",
        EnumCoreErrorCode.REGISTRY_VALIDATION_FAILED: "Registry validation failed",
        EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED: "Service resolution from registry failed",
        EnumCoreErrorCode.OPERATION_FAILED: "Operation failed",
        EnumCoreErrorCode.TIMEOUT_EXCEEDED: "Timeout exceeded",
        EnumCoreErrorCode.RESOURCE_UNAVAILABLE: "Resource unavailable",
        EnumCoreErrorCode.UNSUPPORTED_OPERATION: "Unsupported operation",
        EnumCoreErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
        EnumCoreErrorCode.INVALID_STATE: "Invalid state",
        EnumCoreErrorCode.INITIALIZATION_FAILED: "Initialization failed",
        EnumCoreErrorCode.TIMEOUT: "Operation timed out",
        EnumCoreErrorCode.INTERNAL_ERROR: "Internal error occurred",
        EnumCoreErrorCode.NETWORK_ERROR: "Network error occurred",
        EnumCoreErrorCode.MIGRATION_ERROR: "Migration error occurred",
        EnumCoreErrorCode.TIMEOUT_ERROR: "Timeout error occurred",
        EnumCoreErrorCode.RESOURCE_ERROR: "Resource error occurred",
        EnumCoreErrorCode.RUNTIME_ERROR: "Runtime error occurred",
        EnumCoreErrorCode.HANDLER_EXECUTION_ERROR: "Handler execution failed",
        EnumCoreErrorCode.EVENT_BUS_ERROR: "Event bus operation failed",
        EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR: "Contract validation failed",
        EnumCoreErrorCode.TEST_SETUP_FAILED: "Test setup failed",
        EnumCoreErrorCode.TEST_ASSERTION_FAILED: "Test assertion failed",
        EnumCoreErrorCode.MOCK_CONFIGURATION_ERROR: "Mock configuration error",
        EnumCoreErrorCode.TEST_DATA_INVALID: "Test data is invalid",
        EnumCoreErrorCode.DATABASE_CONNECTION_ERROR: "Database connection failed",
        EnumCoreErrorCode.DATABASE_OPERATION_ERROR: "Database operation failed",
        EnumCoreErrorCode.DATABASE_QUERY_ERROR: "Database query failed",
        EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED: "Method not implemented",
        EnumCoreErrorCode.ABSTRACT_METHOD_CALLED: "Abstract method called directly",
        EnumCoreErrorCode.MODULE_NOT_FOUND: "Module not found",
        EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE: "Dependency unavailable",
        EnumCoreErrorCode.VERSION_INCOMPATIBLE: "Version incompatible",
        EnumCoreErrorCode.IMPORT_ERROR: "Import error occurred",
        EnumCoreErrorCode.DEPENDENCY_ERROR: "Dependency error occurred",
        EnumCoreErrorCode.NO_SUITABLE_PROVIDER: "No suitable provider available",
        EnumCoreErrorCode.RATE_LIMIT_ERROR: "Rate limit exceeded",
        EnumCoreErrorCode.AUTHENTICATION_ERROR: "Authentication failed",
        EnumCoreErrorCode.QUOTA_EXCEEDED: "Quota exceeded",
        EnumCoreErrorCode.PROCESSING_ERROR: "Processing error",
        EnumCoreErrorCode.TYPE_MISMATCH: "Type mismatch in value conversion",
        EnumCoreErrorCode.TYPE_INTROSPECTION_ERROR: "Type introspection failed during runtime reflection",
        EnumCoreErrorCode.INTELLIGENCE_PROCESSING_FAILED: "Intelligence processing failed",
        EnumCoreErrorCode.PATTERN_RECOGNITION_FAILED: "Pattern recognition failed",
        EnumCoreErrorCode.CONTEXT_ANALYSIS_FAILED: "Context analysis failed",
        EnumCoreErrorCode.LEARNING_ENGINE_FAILED: "Learning engine operation failed",
        EnumCoreErrorCode.INTELLIGENCE_COORDINATION_FAILED: "Intelligence coordination failed",
        EnumCoreErrorCode.SYSTEM_HEALTH_DEGRADED: "System health has degraded",
        EnumCoreErrorCode.SERVICE_START_FAILED: "Service failed to start",
        EnumCoreErrorCode.SERVICE_STOP_FAILED: "Service failed to stop",
        EnumCoreErrorCode.SERVICE_UNHEALTHY: "Service is unhealthy",
        EnumCoreErrorCode.SERVICE_UNAVAILABLE: "Service is unavailable",
        EnumCoreErrorCode.SECURITY_REPORT_FAILED: "Security report generation failed",
        EnumCoreErrorCode.SECURITY_VIOLATION: "Security violation detected",
        EnumCoreErrorCode.EVENT_PROCESSING_FAILED: "Event processing failed",
        EnumCoreErrorCode.DEPENDENCY_FAILED: "Dependency check or operation failed",
        EnumCoreErrorCode.CONTRACT_VIOLATION: "Contract violation detected",
        EnumCoreErrorCode.DISCOVERY_SETUP_FAILED: "Discovery setup failed",
        EnumCoreErrorCode.METADATA_LOAD_FAILED: "Metadata loading failed",
        EnumCoreErrorCode.DISCOVERY_INVALID_NODE: "Discovery invalid node configuration",
        EnumCoreErrorCode.DISCOVERY_INVALID_REQUEST: "Discovery invalid request format",
        EnumCoreErrorCode.THREAD_SAFETY_VIOLATION: "Thread safety violation detected",
        EnumCoreErrorCode.ADAPTER_BINDING_ERROR: "Adapter binding failed",
        EnumCoreErrorCode.PURITY_VIOLATION_ERROR: "Purity violation in pure node",
        EnumCoreErrorCode.NODE_EXECUTION_ERROR: "Node execution failed",
        EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR: "Unsupported capability requested",
        EnumCoreErrorCode.WORKFLOW_STEP_LIMIT_EXCEEDED: "Workflow step count exceeds maximum limit",
        EnumCoreErrorCode.WORKFLOW_PAYLOAD_SIZE_EXCEEDED: "Workflow step payload size exceeds maximum limit",
        EnumCoreErrorCode.WORKFLOW_TOTAL_PAYLOAD_EXCEEDED: "Workflow total payload size exceeds maximum limit",
        # Orchestrator Level 1 (Structural) - detected at contract parse time
        EnumCoreErrorCode.ORCHESTRATOR_STRUCT_MISSING_FIELD: "Orchestrator: required field missing in contract",
        EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE: "Orchestrator: field has invalid type in contract",
        EnumCoreErrorCode.ORCHESTRATOR_STRUCT_MALFORMED_CONTRACT: "Orchestrator: malformed contract structure",
        EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_STEP_TYPE: "Orchestrator: invalid step_type value",
        EnumCoreErrorCode.ORCHESTRATOR_STRUCT_WORKFLOW_NOT_LOADED: "Orchestrator: workflow definition not loaded",
        # Orchestrator Level 2 (Semantic) - detected during validation before execution
        EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_CYCLE_DETECTED: "Orchestrator: dependency cycle detected in workflow",
        EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_INVALID_DEPENDENCY: "Orchestrator: invalid dependency reference",
        EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_DUPLICATE_STEP_ID: "Orchestrator: duplicate step_id in workflow",
        EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_MISSING_DEPENDENCY: "Orchestrator: referenced dependency step not found",
        EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_INVALID_EXECUTION_MODE: "Orchestrator: invalid execution mode for v1.0",
        # Orchestrator Level 3 (Execution) - detected during workflow execution
        EnumCoreErrorCode.ORCHESTRATOR_EXEC_STEP_TIMEOUT: "Orchestrator: step execution timed out",
        EnumCoreErrorCode.ORCHESTRATOR_EXEC_STEP_FAILED: "Orchestrator: step execution failed",
        EnumCoreErrorCode.ORCHESTRATOR_EXEC_ACTION_REJECTED: "Orchestrator: action was rejected by target node",
        EnumCoreErrorCode.ORCHESTRATOR_EXEC_WORKFLOW_TIMEOUT: "Orchestrator: workflow execution timed out",
        EnumCoreErrorCode.ORCHESTRATOR_EXEC_LEASE_EXPIRED: "Orchestrator: action lease expired during execution",
        EnumCoreErrorCode.ORCHESTRATOR_EXEC_WORKFLOW_FAILED: "Orchestrator: workflow execution failed",
        EnumCoreErrorCode.ORCHESTRATOR_EXEC_ITERATION_LIMIT_EXCEEDED: "Orchestrator: workflow iteration limit exceeded (DoS protection)",
        # Cache errors
        EnumCoreErrorCode.CACHE_BACKEND_ERROR: "Cache backend operation failed",
        EnumCoreErrorCode.CACHE_CONNECTION_ERROR: "Cache backend connection failed",
        EnumCoreErrorCode.CACHE_TIMEOUT_ERROR: "Cache operation timed out",
        EnumCoreErrorCode.CACHE_OPERATION_FAILED: "Cache operation failed",
        EnumCoreErrorCode.CACHE_BACKEND_NOT_CONNECTED: "Cache backend is not connected",
        # Replay infrastructure errors
        EnumCoreErrorCode.REPLAY_RECORD_NOT_FOUND: "Replay: no matching effect record found",
        EnumCoreErrorCode.REPLAY_NOT_IN_REPLAY_MODE: "Replay: recorder is not in replay mode",
        EnumCoreErrorCode.REPLAY_INVALID_EFFECT_TYPE: "Replay: effect_type must not be empty",
        EnumCoreErrorCode.REPLAY_SEQUENCE_EXHAUSTED: "Replay: UUID/value sequence exhausted during replay",
        EnumCoreErrorCode.REPLAY_ENFORCEMENT_BLOCKED: "Replay: non-deterministic effect blocked in strict mode",
    }
    return descriptions.get(error_code, "Unknown error")
