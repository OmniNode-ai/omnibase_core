from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

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
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message=msg,
    )


def validate_secret_configuration(config_type: str, **kwargs: Any) -> dict[str, Any]:
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
            result = config.validate_credentials()
            # Convert Pydantic model to dict
            return result.model_dump()
        except (
            Exception
        ) as e:  # fallback-ok: validation returns structured error dict, caller handles
            return {"is_valid": False, "error": str(e)}

    elif config_type == "backend":
        try:
            backend = ModelSecretBackend(**kwargs)
            return {"is_valid": True, "backend": backend}
        except (
            Exception
        ) as e:  # fallback-ok: validation returns structured error dict, caller handles
            return {"is_valid": False, "error": str(e)}

    else:
        return {"is_valid": False, "error": f"Unknown config type: {config_type}"}


def get_security_recommendations(
    config_type: str, config_dict: dict[str, Any]
) -> list[Any]:
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
            recommendations: list[Any] = assessment.get("recommendations", [])
            return recommendations

        if config_type == "backend":
            backend = ModelSecretBackend(**config_dict)
            return backend.get_security_recommendations()

        return [f"Unknown config type: {config_type}"]

    except (
        Exception
    ) as e:  # fallback-ok: recommendations return error list, non-critical helper function
        return [f"Error getting recommendations: {e}"]


# === Export All Models ===

__all__ = [
    "ModelSecretConfig",
    "ModelSecretManager",
    "ModelSecureCredentials",
]
