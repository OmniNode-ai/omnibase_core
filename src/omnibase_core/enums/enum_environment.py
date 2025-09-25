"""
Environment enumeration.

Defines environment types for deployment and execution contexts.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumEnvironment(str, Enum):
    """
    Enumeration of environment types.

    Used for categorizing deployment and execution environments.
    """

    # Standard environments
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    # Additional environments
    LOCAL = "local"
    INTEGRATION = "integration"
    PREVIEW = "preview"
    SANDBOX = "sandbox"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_production_like(cls, environment: EnumEnvironment) -> bool:
        """Check if environment is production-like (requires high standards)."""
        return environment in {cls.PRODUCTION, cls.STAGING}

    @classmethod
    def is_development_like(cls, environment: EnumEnvironment) -> bool:
        """Check if environment is development-like (allows debugging)."""
        return environment in {cls.DEVELOPMENT, cls.LOCAL, cls.SANDBOX}

    @classmethod
    def allows_debugging(cls, environment: EnumEnvironment) -> bool:
        """Check if environment allows debugging features."""
        return environment in {cls.DEVELOPMENT, cls.LOCAL, cls.TESTING, cls.SANDBOX}

    @classmethod
    def requires_security_hardening(cls, environment: EnumEnvironment) -> bool:
        """Check if environment requires security hardening."""
        return environment in {cls.PRODUCTION, cls.STAGING}

    @classmethod
    def get_log_level(cls, environment: EnumEnvironment) -> str:
        """Get recommended log level for environment."""
        log_levels = {
            cls.DEVELOPMENT: "DEBUG",
            cls.LOCAL: "DEBUG",
            cls.SANDBOX: "DEBUG",
            cls.TESTING: "INFO",
            cls.INTEGRATION: "INFO",
            cls.STAGING: "WARN",
            cls.PREVIEW: "WARN",
            cls.PRODUCTION: "error",
        }
        return log_levels.get(environment, "INFO")

    @classmethod
    def get_default_environment(cls) -> EnumEnvironment:
        """Get the default environment."""
        return cls.DEVELOPMENT


# Export the enum
__all__ = ["EnumEnvironment"]
