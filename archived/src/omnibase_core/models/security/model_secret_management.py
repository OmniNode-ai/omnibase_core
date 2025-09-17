"""
ONEX Secret Management Models and Utilities.

This module provides compatibility imports for secret management
models that have been extracted to separate files as part of nm_arch_003.

All models have been enhanced with enterprise-grade features including:
- Comprehensive validation and business logic
- Security assessment and recommendations
- Performance optimization and monitoring
- Environment integration and factory methods
- Health checking and troubleshooting capabilities

Original models migrated to:
- SecretBackendEnum → ModelSecretBackend (model_secret_backend.py)
- ModelSecretConfig → ModelSecretConfig (model_secret_config.py)
- ModelSecureCredentials → ModelSecureCredentials (model_secure_credentials.py)
- ModelDatabaseSecureConfig → ModelDatabaseSecureConfig (model_database_secure_config.py)
- SecretManager → ModelSecretManager (model_secret_manager.py)
"""

# === Current Standards Imports ===

# Import all extracted models for current standards
from .model_secret_backend import ModelSecretBackend
from .model_secret_config import ModelSecretConfig
from .model_secret_manager import (
    ModelSecretManager,
    get_secret_manager,
    init_secret_manager,
    init_secret_manager_from_manager,
)
from .model_secure_credentials import ModelSecureCredentials

# === Current Standards Layer ===


# Provide compatibility for the original enum
class SecretBackendEnum:
    """
    Current enum standards layer.

    DEPRECATED: Use ModelSecretBackend instead for enhanced functionality.
    This class provides compatibility for existing code.
    """

    ENVIRONMENT = "environment"
    DOTENV = "dotenv"
    VAULT = "vault"
    KUBERNETES = "kubernetes"
    FILE = "file"

    @classmethod
    def to_model(cls, enum_value: str) -> ModelSecretBackend:
        """Convert enum value to ModelSecretBackend."""
        return ModelSecretBackend(backend_type=enum_value)


# Provide compatibility for SecretManager
class SecretManager:
    """
    Current SecretManager standards layer.

    DEPRECATED: Use ModelSecretManager instead for enhanced functionality.
    This class provides compatibility for existing code.
    """

    def __init__(self, config: ModelSecretConfig):
        """Initialize with ModelSecretManager internally."""
        self._manager = ModelSecretManager(config=config)

    def get_database_config(self):
        """Get database configuration (legacy method)."""
        return self._manager.get_database_config()

    def mask_sensitive_data(self, data: dict) -> dict:
        """Mask sensitive data (legacy method)."""
        return self._manager.mask_sensitive_data(data)


# === Enhanced Global Functions ===


def create_secret_manager_for_environment(
    environment: str = "auto",
) -> ModelSecretManager:
    """
    Create secret manager optimized for specific environment.

    Args:
        environment: Target environment ('development', 'production', 'kubernetes', 'auto')

    Returns:
        Configured ModelSecretManager instance
    """
    if environment == "auto":
        return ModelSecretManager.create_auto_configured()
    if environment == "development":
        return ModelSecretManager.create_for_development()
    if environment == "production":
        return ModelSecretManager.create_for_production()
    if environment == "kubernetes":
        return ModelSecretManager.create_for_kubernetes()
    msg = f"Unknown environment: {environment}"
    raise ValueError(msg)


def validate_secret_configuration(config_type: str, **kwargs) -> dict:
    """
    Validate secret configuration for specific type.

    Args:
        config_type: Type of configuration ('database', 'backend')
        **kwargs: Configuration parameters

    Returns:
        Validation result dictionary
    """
    if config_type == "database":
        try:
            from omnibase_core.models.configuration.model_database_secure_config import (
                ModelDatabaseSecureConfig,
            )

            config = ModelDatabaseSecureConfig(**kwargs)
            return config.validate_credentials()
        except Exception as e:
            return {"is_valid": False, "error": str(e)}

    elif config_type == "backend":
        try:
            backend = ModelSecretBackend(**kwargs)
            return {"is_valid": True, "backend": backend}
        except Exception as e:
            return {"is_valid": False, "error": str(e)}

    else:
        return {"is_valid": False, "error": f"Unknown config type: {config_type}"}


def get_security_recommendations(config_type: str, config_dict: dict) -> list:
    """
    Get security recommendations for configuration.

    Args:
        config_type: Type of configuration ('database', 'backend')
        config_dict: Configuration dictionary

    Returns:
        List of security recommendations
    """
    try:
        if config_type == "database":
            from omnibase_core.models.configuration.model_database_secure_config import (
                ModelDatabaseSecureConfig,
            )

            config = ModelDatabaseSecureConfig(**config_dict)
            assessment = config.get_security_assessment()
            return assessment.get("recommendations", [])

        if config_type == "backend":
            backend = ModelSecretBackend(**config_dict)
            return backend.get_security_recommendations()

        return [f"Unknown config type: {config_type}"]

    except Exception as e:
        return [f"Error getting recommendations: {e}"]


# === Export All Models ===

__all__ = [
    # New enhanced models
    "ModelSecretBackend",
    "ModelSecretConfig",
    "ModelSecretManager",
    "ModelSecureCredentials",
    # Current standards (deprecated)
    "SecretBackendEnum",
    "SecretManager",
    # Enhanced utility functions
    "create_secret_manager_for_environment",
    # Global functions
    "get_secret_manager",
    "get_security_recommendations",
    "init_secret_manager",
    "init_secret_manager_from_manager",
    "validate_secret_configuration",
]
