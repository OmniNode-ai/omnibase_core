"""
Environment Type Enumeration

Standard environment types for ONEX architecture.
"""

from enum import Enum


class EnumEnvironmentType(str, Enum):
    """
    Standard environment types.

    String-based enum for environment classification.
    """

    DEVELOPMENT = "development"
    DEV = "dev"
    LOCAL = "local"
    STAGING = "staging"
    STAGE = "stage"
    TEST = "test"
    TESTING = "testing"
    PRODUCTION = "production"
    PROD = "prod"

    @classmethod
    def get_display_name(cls, environment_type: "EnumEnvironmentType") -> str:
        """Get human-readable display name for environment type."""
        display_names = {
            cls.DEVELOPMENT: "Development",
            cls.DEV: "Development",
            cls.LOCAL: "Local Development",
            cls.STAGING: "Staging",
            cls.STAGE: "Staging",
            cls.TEST: "Testing",
            cls.TESTING: "Testing",
            cls.PRODUCTION: "Production",
            cls.PROD: "Production",
        }
        return display_names.get(environment_type, environment_type.value.title())

    def is_development(self) -> bool:
        """Check if this is a development environment."""
        dev_types = {self.DEVELOPMENT, self.DEV, self.LOCAL}
        return self in dev_types

    def is_staging(self) -> bool:
        """Check if this is a staging environment."""
        staging_types = {self.STAGING, self.STAGE, self.TEST, self.TESTING}
        return self in staging_types

    def is_production(self) -> bool:
        """Check if this is a production environment."""
        prod_types = {self.PRODUCTION, self.PROD}
        return self in prod_types

    def get_default_timeout_multiplier(self) -> float:
        """Get default timeout multiplier for this environment type."""
        if self.is_production():
            return 2.0  # Longer timeouts in production
        if self.is_development():
            return 0.5  # Shorter timeouts in development
        return 1.0  # Default timeouts for staging

    def get_default_retry_multiplier(self) -> float:
        """Get default retry multiplier for this environment type."""
        if self.is_production():
            return 2.0  # More retries in production
        if self.is_development():
            return 0.5  # Fewer retries in development
        return 1.0  # Default retries for staging
