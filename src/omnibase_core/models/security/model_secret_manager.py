import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.singleton_holders import _SecretManagerHolder

from .model_configuration_summary import ModelConfigurationSummary
from .model_credentials_analysis import ModelCredentialsAnalysis, ModelManagerAssessment
from .model_mask_data import ModelMaskData
from .model_secret_config import ModelSecretConfig
from .model_secure_credentials import ModelSecureCredentials

if TYPE_CHECKING:
    from omnibase_core.models.configuration.model_database_secure_config import (
        ModelDatabaseSecureConfig,
    )
    from omnibase_core.models.core.model_health_check_result import (
        ModelHealthCheckResult,
    )

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

T = TypeVar("T", bound=ModelSecureCredentials)

# Exclude T from wildcard imports
__all__ = ["ModelSecretManager"]


class ModelSecretManager(BaseModel):
    """
    Enterprise-grade centralized secret management for ONEX with comprehensive
    backend support, validation, and operational monitoring.

    Features:
    - Multi-backend secret management (environment, dotenv, vault, kubernetes, file)
    - Credential validation and strength assessment
    - Fallback and recovery mechanisms
    - Health checks and troubleshooting
    """

    config: ModelSecretConfig = Field(
        default_factory=ModelSecretConfig,
        description="Secret management configuration",
    )

    audit_enabled: bool = Field(
        default=True,
        description="Enable audit logging for security monitoring",
    )

    fallback_enabled: bool = Field(
        default=True,
        description="Enable fallback to secondary backends on failure",
    )

    def model_post_init(self, __context: object | None = None) -> None:
        """Initialize secret manager after model creation."""
        self._initialize_environment()

    def _initialize_environment(self) -> None:
        """Initialize environment based on configuration."""
        from omnibase_core.enums.enum_backend_type import EnumBackendType

        try:
            if self.config.backend.backend_type == EnumBackendType.DOTENV:
                self._load_dotenv_environment()
        except Exception as e:
            logging.exception(f"Failed to initialize secret manager: {e}")

    def _load_dotenv_environment(self) -> None:
        """Load environment variables from .env file if configured."""
        if not self.config.auto_load_dotenv or not DOTENV_AVAILABLE:
            return

        # Use configured path or look for common locations
        env_paths = []
        if self.config.dotenv_path:
            env_paths.append(self.config.dotenv_path)
        else:
            env_paths.extend(
                [
                    Path(".env"),
                    Path(".env.local"),
                    Path("config/.env"),
                    Path(".env.development"),
                ],
            )

        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                logging.info(f"Loaded environment variables from {env_path}")
                break

    # === Core Secret Management ===

    def get_database_config(
        self,
        env_prefix: str = "ONEX_DB_",
    ) -> "ModelDatabaseSecureConfig":
        """Get secure database configuration with validation."""
        from omnibase_core.models.configuration.model_database_secure_config import (
            ModelDatabaseSecureConfig,
        )

        try:
            config = self._load_with_fallback(ModelDatabaseSecureConfig, env_prefix)

            # Validate configuration
            validation = config.validate_credentials()
            if not validation.is_valid:
                msg = f"Invalid database configuration: {validation.errors}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

            return config

        except Exception:
            raise

    def _load_with_fallback(self, config_class: type[T], env_prefix: str) -> T:
        """Load configuration with fallback support."""
        try:
            # Try primary backend
            return config_class.load_from_env(env_prefix)

        except Exception:
            if not self.fallback_enabled or not self.config.fallback_backends:
                raise

            # Try fallback backends
            for fallback_backend in self.config.fallback_backends:
                try:
                    # Temporarily switch to fallback backend
                    original_backend = self.config.backend
                    self.config.backend = fallback_backend

                    config = config_class.load_from_env(env_prefix)

                    # Restore original backend
                    self.config.backend = original_backend

                    return config

                except Exception:
                    continue

                finally:
                    # Ensure original backend is restored
                    self.config.backend = original_backend

            # All fallbacks failed
            raise

    # === Credential Analysis ===

    def mask_sensitive_data(
        self,
        data: ModelMaskData,
        mask_level: str = "standard",
    ) -> ModelMaskData:
        """Enhanced sensitive data masking with multiple security levels."""
        sensitive_keys = {
            "password",
            "token",
            "key",
            "secret",
            "credential",
            "api_key",
            "bearer_token",
            "sasl_password",
            "ssl_password",
            "ssl_key_password",
            "private_key",
            "auth",
            "authorization",
        }

        def mask_value(value: str, level: str) -> str:
            if level == "minimal":
                # Show first and last 2 characters for debugging
                if len(value) <= 4:
                    return "*" * len(value)
                return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
            if level == "aggressive":
                return "***REDACTED***"
            # standard
            return "***MASKED***"

        def mask_recursive(
            obj: str | int | bool | list[Any] | dict[str, Any] | ModelMaskData,
        ) -> str | int | bool | list[Any] | dict[str, Any] | ModelMaskData:
            if isinstance(obj, dict):
                return {
                    key: (
                        mask_recursive(value)
                        if not any(
                            sensitive in key.lower() for sensitive in sensitive_keys
                        )
                        else mask_value(str(value), mask_level)
                    )
                    for key, value in obj.items()
                }
            if isinstance(obj, list):
                return [mask_recursive(item) for item in obj]
            return obj

        # Parameter is typed as ModelMaskData, no need to check
        masked_dict = mask_recursive(data.to_dict())
        return (
            ModelMaskData.from_dict(masked_dict)
            if isinstance(masked_dict, dict)
            else data
        )

    def analyze_credentials_strength(
        self,
        credentials: ModelSecureCredentials,
    ) -> ModelCredentialsAnalysis:
        """Comprehensive credential strength analysis."""
        base_analysis = credentials.get_credential_strength_assessment()

        # Create manager-specific assessment
        security_profile = self.config.backend.get_security_profile()
        manager_assessment = ModelManagerAssessment(
            backend_security_level=security_profile.security_level.value,
            audit_compliance="compliant" if self.audit_enabled else "non_compliant",
            fallback_resilience=(
                "high"
                if self.fallback_enabled and self.config.fallback_backends
                else "low"
            ),
        )

        # Combine base analysis with manager assessment
        return ModelCredentialsAnalysis(
            strength_score=base_analysis.strength_score,
            password_entropy=base_analysis.password_entropy,
            common_patterns=base_analysis.common_patterns,
            security_issues=base_analysis.security_issues,
            recommendations=base_analysis.recommendations,
            compliance_status=base_analysis.compliance_status,
            risk_level=base_analysis.risk_level,
            manager_assessment=manager_assessment,
        )

    # === Health Monitoring ===

    def health_check(self) -> "ModelHealthCheckResult":
        """Comprehensive health check of secret management system."""
        from omnibase_core.models.core.model_health_check_result import (
            HealthCheckComponent,
            ModelHealthCheckResult,
        )

        components = []
        warnings = []
        status = "healthy"

        try:
            # Check backend health
            backend_health = self.config.health_check()

            # Create component for backend
            backend_component = HealthCheckComponent(
                name="secret_backend",
                status="healthy" if backend_health.healthy else "unhealthy",
                message=(
                    "Backend health check completed"
                    if backend_health.healthy
                    else f"Backend unhealthy: {', '.join(backend_health.issues)}"
                ),
            )
            components.append(backend_component)

            if not backend_health.healthy:
                status = "unhealthy"
                warnings.extend(backend_health.issues)

        except Exception as e:
            status = "unhealthy"
            components.append(
                HealthCheckComponent(
                    name="secret_backend",
                    status="unhealthy",
                    message=f"Health check failed: {e}",
                ),
            )
            warnings.append(f"Health check failed: {e}")

        return ModelHealthCheckResult(
            status=status,
            service_name="secret_manager",
            components=components,
            warnings=warnings,
            checks_passed=len([c for c in components if c.status == "healthy"]),
            checks_failed=len([c for c in components if c.status == "unhealthy"]),
        )

    # === Configuration Management ===

    def get_configuration_summary(self) -> ModelConfigurationSummary:
        """Get summary of current configuration."""
        # Get models
        backend_capabilities = self.config.backend.get_backend_capabilities()
        security_profile = self.config.backend.get_security_profile()
        performance_profile = self.config.backend.get_performance_profile()

        # Convert to dicts/strings as expected by ModelConfigurationSummary
        return ModelConfigurationSummary(
            backend_type=self.config.backend.backend_type.value,
            backend_capabilities=backend_capabilities.model_dump(),
            security_profile=security_profile.model_dump(),
            performance_profile=performance_profile.model_dump(),
            audit_enabled=self.audit_enabled,
            fallback_enabled=self.fallback_enabled,
            fallback_backends=[
                fb.backend_type.value for fb in self.config.fallback_backends
            ],
            environment_type=self.config.backend.detect_environment_type(),
            production_ready=self.config.backend.is_production_ready(),
        )

    # === Factory Methods ===

    @classmethod
    def create_for_development(
        cls,
        dotenv_path: str | None = None,
    ) -> "ModelSecretManager":
        """Create secret manager optimized for development environment."""
        config = ModelSecretConfig.create_for_development(dotenv_path)

        return cls(config=config, audit_enabled=True)

    @classmethod
    def create_for_production(cls, backend_type: str = "vault") -> "ModelSecretManager":
        """Create secret manager optimized for production environment."""
        from omnibase_core.enums.enum_backend_type import EnumBackendType

        # Convert string to enum
        backend_enum = (
            EnumBackendType.from_string(backend_type)
            if isinstance(backend_type, str)
            else backend_type
        )
        config = ModelSecretConfig.create_for_production(backend_enum)

        return cls(config=config, audit_enabled=True, fallback_enabled=True)

    @classmethod
    def create_for_kubernetes(
        cls,
        namespace: str = "default",
        secret_name: str = "onex-secrets",  # noqa: S107 - config name, not a password
    ) -> "ModelSecretManager":
        """Create secret manager for Kubernetes environment."""
        config = ModelSecretConfig.create_for_kubernetes(namespace, secret_name)

        return cls(config=config, audit_enabled=True, fallback_enabled=True)

    @classmethod
    def create_auto_configured(cls) -> "ModelSecretManager":
        """Create automatically configured secret manager based on environment detection."""
        config = ModelSecretConfig.create_auto_configured()

        return cls(config=config, audit_enabled=True, fallback_enabled=True)


def get_secret_manager() -> ModelSecretManager:
    """Get the secret manager instance (now via DI container)."""
    from omnibase_core.models.container.model_onex_container import (
        get_model_onex_container_sync,
    )

    try:
        container = get_model_onex_container_sync()
        manager: ModelSecretManager = container.secret_manager()
        return manager
    except (
        Exception
    ):  # fallback-ok: DI container unavailable during bootstrap or circular dependency scenarios
        # Fallback to singleton holder
        manager = _SecretManagerHolder.get()
        if manager is None:
            manager = ModelSecretManager()
            _SecretManagerHolder.set(manager)
        # Type narrowing: manager is now guaranteed to be ModelSecretManager
        assert manager is not None
        return manager


def init_secret_manager(config: ModelSecretConfig) -> ModelSecretManager:
    """Initialize global secret manager with custom config (now via DI container)."""
    from omnibase_core.models.container.model_onex_container import (
        get_model_onex_container_sync,
    )

    manager = ModelSecretManager(config=config)

    try:
        # Try to set in container
        container = get_model_onex_container_sync()
        # Container manages its own instance, but we update holder as fallback
        _SecretManagerHolder.set(manager)
        result: ModelSecretManager = container.secret_manager()
        return result
    except (
        Exception
    ):  # fallback-ok: DI container unavailable during bootstrap or circular dependency scenarios
        # Fallback to singleton holder
        _SecretManagerHolder.set(manager)
        return manager


def init_secret_manager_from_manager(manager: ModelSecretManager) -> ModelSecretManager:
    """Initialize global secret manager from existing manager instance (now via DI container)."""
    from omnibase_core.models.container.model_onex_container import (
        get_model_onex_container_sync,
    )

    try:
        # Try to set in container
        container = get_model_onex_container_sync()
        # Container manages its own instance, but we update holder as fallback
        _SecretManagerHolder.set(manager)
        result: ModelSecretManager = container.secret_manager()
        return result
    except (
        Exception
    ):  # fallback-ok: DI container unavailable during bootstrap or circular dependency scenarios
        # Fallback to singleton holder
        _SecretManagerHolder.set(manager)
        return manager
