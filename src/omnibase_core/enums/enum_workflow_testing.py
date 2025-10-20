#!/usr/bin/env python3
"""
ONEX Workflow Testing Enumerations

This module provides all enumerations for the ONEX workflow testing system,
supporting flexible dependency accommodation and comprehensive test workflows.
"""

from enum import Enum


class EnumAccommodationLevel(str, Enum):
    """Enumeration of dependency accommodation levels"""

    FULL_REAL = "full_real"
    FULL_MOCK = "full_mock"
    HYBRID_SMART = "hybrid_smart"
    SELECTIVE = "selective"
    PROGRESSIVE = "progressive"


class EnumAccommodationStrategy(str, Enum):
    """Enumeration of accommodation strategies"""

    HYBRID_SMART = "hybrid_smart"
    DEVELOPMENT_FAST = "development_fast"
    CI_CD_RELIABLE = "ci_cd_reliable"
    INTEGRATION_THOROUGH = "integration_thorough"
    PERFORMANCE_REALISTIC = "performance_realistic"


class EnumAccommodationType(str, Enum):
    """Enumeration of accommodation types"""

    REAL = "real"
    MOCK = "mock"
    MOCK_WITH_FAILURE_INJECTION = "mock_with_failure_injection"
    REAL_WITH_MONITORING = "real_with_monitoring"


class EnumFallbackStrategy(str, Enum):
    """Enumeration of fallback strategies"""

    MOCK_IF_REAL_UNAVAILABLE = "mock_if_real_unavailable"
    SKIP_IF_UNAVAILABLE = "skip_if_unavailable"
    FAIL_IF_UNAVAILABLE = "fail_if_unavailable"
    MOCK_FOR_DETERMINISTIC_TESTS = "mock_for_deterministic_tests"


class EnumTestExecutionStatus(str, Enum):
    """Enumeration of test execution statuses"""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    ERROR = "error"
    ACCOMMODATION_FAILED = "accommodation_failed"


class EnumTestWorkflowPriority(str, Enum):
    """Enumeration of test workflow priorities"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnumTestContext(str, Enum):
    """Enumeration of test execution contexts"""

    CI_CD_ENVIRONMENT = "ci_cd_environment"
    LOCAL_DEVELOPMENT = "local_development"
    INTEGRATION_TESTING = "integration_testing"
    PERFORMANCE_TESTING = "performance_testing"
    PRODUCTION_VALIDATION = "production_validation"


class EnumDependencyType(str, Enum):
    """Enumeration of dependency types"""

    SERVICE = "service"
    REGISTRY = "registry"
    EVENT_BUS = "event_bus"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    LLM_SERVICE = "llm_service"
    FILE_SYSTEM = "file_system"


class EnumMockBehaviorType(str, Enum):
    """Enumeration of mock behavior types"""

    SUCCESS_RESPONSE = "success_response"
    FAILURE_RESPONSE = "failure_response"
    TIMEOUT_SIMULATION = "timeout_simulation"
    LATENCY_SIMULATION = "latency_simulation"
    INTERMITTENT_FAILURE = "intermittent_failure"
    DETERMINISTIC_RESPONSE = "deterministic_response"


class EnumValidationRule(str, Enum):
    """Enumeration of validation rules for test assertions"""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"
    TYPE_MATCH = "type_match"
    IS_NOT_NONE = "is_not_none"
    IS_NONE = "is_none"
    LENGTH_EQUALS = "length_equals"
    ALL_ITEMS_MATCH = "all_items_match"
