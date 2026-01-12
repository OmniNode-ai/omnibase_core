"""
Environment Enum.

Execution environment types for ONEX deployments.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEnvironment(StrValueHelper, str, Enum):
    """Execution environment types for ONEX deployments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    LOCAL = "local"
    INTEGRATION = "integration"
    PREVIEW = "preview"
    SANDBOX = "sandbox"

    @classmethod
    def is_production_like(cls, environment: "EnumEnvironment") -> bool:
        """
        Check if the environment is production-like.

        Args:
            environment: The environment to check

        Returns:
            True if production-like, False otherwise
        """
        return environment in {cls.PRODUCTION, cls.STAGING}

    @classmethod
    def is_development_like(cls, environment: "EnumEnvironment") -> bool:
        """
        Check if the environment is development-like.

        Args:
            environment: The environment to check

        Returns:
            True if development-like, False otherwise
        """
        return environment in {cls.DEVELOPMENT, cls.LOCAL, cls.SANDBOX}

    @classmethod
    def allows_debugging(cls, environment: "EnumEnvironment") -> bool:
        """
        Check if the environment allows debugging.

        Args:
            environment: The environment to check

        Returns:
            True if debugging is allowed, False otherwise
        """
        return environment in {cls.DEVELOPMENT, cls.LOCAL, cls.TESTING, cls.SANDBOX}

    @classmethod
    def requires_security_hardening(cls, environment: "EnumEnvironment") -> bool:
        """
        Check if the environment requires security hardening.

        Args:
            environment: The environment to check

        Returns:
            True if security hardening is required, False otherwise
        """
        return environment in {cls.PRODUCTION, cls.STAGING}

    @classmethod
    def get_log_level(cls, environment: "EnumEnvironment") -> str:
        """
        Get the appropriate log level for an environment.

        Args:
            environment: The environment to get the log level for

        Returns:
            Log level string
        """
        log_levels = {
            cls.DEVELOPMENT: "DEBUG",
            cls.LOCAL: "DEBUG",
            cls.SANDBOX: "DEBUG",
            cls.TESTING: "INFO",
            cls.INTEGRATION: "INFO",
            cls.STAGING: "WARN",
            cls.PREVIEW: "WARN",
            cls.PRODUCTION: "error",  # Note: lowercase for production
        }
        return log_levels.get(environment, "INFO")

    @classmethod
    def get_default_environment(cls) -> "EnumEnvironment":
        """
        Get the default environment.

        Returns:
            Default environment (DEVELOPMENT)
        """
        return cls.DEVELOPMENT
