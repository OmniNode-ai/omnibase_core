"""
Config Type Enum.

Strongly typed configuration type values for system configuration classification.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConfigType(StrValueHelper, str, Enum):
    """
    Strongly typed configuration type values.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for configuration type operations.
    """

    # Core configuration types
    NODE_CONFIG = "node_config"
    FUNCTION_CONFIG = "function_config"
    SERVICE_CONFIG = "service_config"
    DATABASE_CONFIG = "database_config"
    CACHE_CONFIG = "cache_config"

    # Infrastructure configuration types
    LOGGING_CONFIG = "logging_config"
    METRICS_CONFIG = "metrics_config"
    VALIDATION_CONFIG = "validation_config"
    SECURITY_CONFIG = "security_config"
    NETWORK_CONFIG = "network_config"

    # Application configuration types
    TEMPLATE_CONFIG = "template_config"
    GENERATION_CONFIG = "generation_config"
    DISCOVERY_CONFIG = "discovery_config"
    RUNTIME_CONFIG = "runtime_config"
    CLI_CONFIG = "cli_config"

    # Data configuration types
    SCHEMA_CONFIG = "schema_config"
    MODEL_CONFIG = "model_config"
    FILTER_CONFIG = "filter_config"
    METADATA_CONFIG = "metadata_config"

    # Environment configuration types
    DEVELOPMENT_CONFIG = "development_config"
    TESTING_CONFIG = "testing_config"
    PRODUCTION_CONFIG = "production_config"
    STAGING_CONFIG = "staging_config"

    # Generic types
    GENERAL_CONFIG = "general_config"
    CUSTOM_CONFIG = "custom_config"
    UNKNOWN_CONFIG = "unknown_config"

    @classmethod
    def is_core_config(cls, config_type: EnumConfigType) -> bool:
        """Check if the config type is a core system configuration."""
        return config_type in {
            cls.NODE_CONFIG,
            cls.FUNCTION_CONFIG,
            cls.SERVICE_CONFIG,
            cls.DATABASE_CONFIG,
            cls.CACHE_CONFIG,
        }

    @classmethod
    def is_infrastructure_config(cls, config_type: EnumConfigType) -> bool:
        """Check if the config type is infrastructure configuration."""
        return config_type in {
            cls.LOGGING_CONFIG,
            cls.METRICS_CONFIG,
            cls.VALIDATION_CONFIG,
            cls.SECURITY_CONFIG,
            cls.NETWORK_CONFIG,
        }

    @classmethod
    def is_application_config(cls, config_type: EnumConfigType) -> bool:
        """Check if the config type is application configuration."""
        return config_type in {
            cls.TEMPLATE_CONFIG,
            cls.GENERATION_CONFIG,
            cls.DISCOVERY_CONFIG,
            cls.RUNTIME_CONFIG,
            cls.CLI_CONFIG,
        }

    @classmethod
    def is_data_config(cls, config_type: EnumConfigType) -> bool:
        """Check if the config type is data-related configuration."""
        return config_type in {
            cls.SCHEMA_CONFIG,
            cls.MODEL_CONFIG,
            cls.FILTER_CONFIG,
            cls.METADATA_CONFIG,
        }

    @classmethod
    def is_environment_config(cls, config_type: EnumConfigType) -> bool:
        """Check if the config type is environment-specific configuration."""
        return config_type in {
            cls.DEVELOPMENT_CONFIG,
            cls.TESTING_CONFIG,
            cls.PRODUCTION_CONFIG,
            cls.STAGING_CONFIG,
        }


# Export for use
__all__ = ["EnumConfigType"]
