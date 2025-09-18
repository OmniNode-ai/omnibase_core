"""
Environment Default Values

Default resource limits and configuration values for different environment types.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ResourceLimitDefaults:
    """Default resource limits for an environment type."""

    cpu_cores: float
    memory_mb: int
    storage_gb: float
    max_connections: int
    max_requests_per_second: float
    max_processes: int | None = None
    max_threads: int | None = None
    network_bandwidth_mbps: float | None = None


class ModelEnvironmentDefaults:
    """
    Default configuration values for different environment types.

    Replaces hardcoded magic numbers with named constants.
    """

    # Production environment defaults
    PRODUCTION_DEFAULTS = ResourceLimitDefaults(
        cpu_cores=8.0,
        memory_mb=16384,
        storage_gb=100.0,
        max_connections=10000,
        max_requests_per_second=1000.0,
        max_processes=1000,
        max_threads=10000,
        network_bandwidth_mbps=1000.0,
    )

    # Staging environment defaults
    STAGING_DEFAULTS = ResourceLimitDefaults(
        cpu_cores=2.0,
        memory_mb=2048,
        storage_gb=10.0,
        max_connections=1000,
        max_requests_per_second=100.0,
        max_processes=100,
        max_threads=1000,
    )

    # Development environment defaults
    DEVELOPMENT_DEFAULTS = ResourceLimitDefaults(
        cpu_cores=1.0,
        memory_mb=512,
        storage_gb=1.0,
        max_connections=100,
        max_requests_per_second=10.0,
    )

    @classmethod
    def get_defaults_for_environment(
        cls, environment_name: str
    ) -> ResourceLimitDefaults:
        """Get default resource limits for environment."""
        from omnibase_core.enums import EnumEnvironmentType

        try:
            env_type = EnumEnvironmentType(environment_name)
            if env_type.is_production():
                return cls.PRODUCTION_DEFAULTS
            elif env_type.is_staging():
                return cls.STAGING_DEFAULTS
            else:
                return cls.DEVELOPMENT_DEFAULTS
        except ValueError:
            # Fallback for custom environment names
            if environment_name in ["production", "prod"]:
                return cls.PRODUCTION_DEFAULTS
            elif environment_name in ["staging", "stage", "test", "testing"]:
                return cls.STAGING_DEFAULTS
            else:
                return cls.DEVELOPMENT_DEFAULTS
