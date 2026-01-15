"""
ModelSecretConfig.

Enterprise-grade secret management configuration with comprehensive backend
support, validation, and environment-specific optimizations.

Features:
- Multiple backend support (environment, dotenv, vault, kubernetes, file)
- Environment detection and automatic backend selection
- Configuration validation and recommendations
- Performance optimization for different backends
- Security assessment and best practices
- Fallback and recovery mechanisms

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports:
- omnibase_core.errors.error_codes (imports only from types.core_types and enums)
- omnibase_core.models.security.model_secret_backend (no circular risk)
- omnibase_core.models.security.model_config_validation_result (no circular risk)
- pydantic, typing, pathlib (standard library)

Import Chain Position:
1. errors.error_codes → types.core_types
2. THIS MODULE → errors.error_codes (OK - no circle)
3. types.constraints → TYPE_CHECKING import of errors.error_codes
4. models.* → types.constraints

This module can safely import error_codes because error_codes only imports
from types.core_types (not from models or types.constraints).
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from omnibase_core.constants import DEFAULT_CACHE_TTL_SECONDS
from omnibase_core.enums.enum_backend_type import EnumBackendType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_latency_level import EnumLatencyLevel
from omnibase_core.enums.enum_security_level import EnumSecurityLevel
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .model_backend_config import ModelBackendConfig
from .model_config_validation_result import ModelConfigValidationResult
from .model_performance_optimization_config import ModelPerformanceOptimizationConfig
from .model_secret_backend import ModelSecretBackend
from .model_secret_health_check_result import ModelSecretHealthCheckResult
from .model_security_summaries import ModelBackendConfigData

try:
    from dotenv import load_dotenv  # noqa: F401

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class ModelSecretConfig(BaseModel):
    """
    Enterprise-grade secret management configuration with comprehensive backend
    support, validation, and environment-specific optimizations.

    Features:
    - Multiple backend support (environment, dotenv, vault, kubernetes, file)
    - Environment detection and automatic backend selection
    - Configuration validation and recommendations
    - Performance optimization for different backends
    - Security assessment and best practices
    - Fallback and recovery mechanisms
    """

    backend: ModelSecretBackend = Field(
        default_factory=ModelSecretBackend.create_environment,
        description="Secret backend configuration",
    )

    dotenv_path: Path | None = Field(
        default=None,
        description="Path to .env file for development",
    )

    vault_url: str | None = Field(
        default=None,
        description="Vault server URL",
        pattern=r"^https?://[a-zA-Z0-9\-\.]+(?::\d+)?(?:/.*)?$",
    )

    vault_token: SecretStr | None = Field(
        default=None,
        description="Vault authentication token",
    )

    vault_namespace: str | None = Field(
        default=None,
        description="Vault namespace for multi-tenancy",
    )

    vault_path: str | None = Field(
        default="secret/",
        description="Vault secret path prefix",
    )

    kubernetes_namespace: str | None = Field(
        default="default",
        description="Kubernetes namespace for secrets",
    )

    kubernetes_secret_name: str | None = Field(
        default="onex-secrets",
        description="Kubernetes secret resource name",
    )

    file_path: Path | None = Field(
        default=None,
        description="Path to file-based secret storage",
    )

    encryption_key: SecretStr | None = Field(
        default=None,
        description="Encryption key for file-based storage",
    )

    auto_load_dotenv: bool = Field(
        default=True,
        description="Automatically load .env file if present",
    )

    env_prefix: str = Field(
        default="ONEX_",
        description="Environment variable prefix for secret loading",
    )

    fallback_backends: list[ModelSecretBackend] = Field(
        default_factory=list,
        description="Fallback backends if primary fails",
    )

    cache_enabled: bool = Field(
        default=True,
        description="Enable secret caching for performance",
    )

    cache_ttl_seconds: int = Field(
        default=300,
        description="Secret cache TTL in seconds",
        ge=0,
        le=3600,
    )

    model_config = ConfigDict(
        extra="ignore",
        arbitrary_types_allowed=True,
        use_enum_values=False,
        validate_assignment=True,
    )

    @field_validator("dotenv_path")
    @classmethod
    def validate_dotenv_path(cls, v: Path | None) -> Path | None:
        """Validate dotenv path exists if specified."""
        if v is not None:
            # Field type Path | None ensures v is Path when not None
            # Convert relative paths to absolute
            if not v.is_absolute():
                v = Path.cwd() / v

        return v

    @field_validator("vault_url")
    @classmethod
    def validate_vault_url(cls, v: str | None) -> str | None:
        """Validate Vault URL format."""
        if v is not None:
            v = v.strip()
            if not v.startswith(("http://", "https://")):
                msg = "Vault URL must start with http:// or https://"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

            # Remove trailing slash for consistency
            v = v.rstrip("/")

        return v

    @field_validator("env_prefix")
    @classmethod
    def validate_env_prefix(cls, v: str) -> str:
        """Validate environment variable prefix."""
        if not v:
            msg = "Environment prefix cannot be empty"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        v = v.strip().upper()

        if not v.endswith("_"):
            v += "_"

        # Validate prefix format
        if not v.replace("_", "").isalnum():
            msg = "Environment prefix must be alphanumeric with underscores"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    # === Configuration Validation ===

    def validate_configuration(self) -> ModelConfigValidationResult:
        """Comprehensive configuration validation."""
        validation_result = ModelConfigValidationResult(
            is_valid=True,
            backend_valid=True,
        )

        # Validate primary backend configuration
        backend_config_data = self.get_backend_config_dict()
        backend_config = ModelBackendConfig.model_validate(backend_config_data)
        backend_validation = self.backend.validate_config(backend_config)

        if not backend_validation.is_valid:
            validation_result.backend_valid = False
            validation_result.is_valid = False
            validation_result.issues.extend(backend_validation.issues)

        # Validate backend-specific requirements
        if self.backend.backend_type == EnumBackendType.DOTENV:
            if not DOTENV_AVAILABLE:
                validation_result.warnings.append(
                    "python-dotenv not available, .env file support disabled",
                )

            if self.dotenv_path and not self.dotenv_path.exists():
                validation_result.issues.append(
                    f"Dotenv file not found: {self.dotenv_path}",
                )
                validation_result.is_valid = False

        elif self.backend.backend_type == EnumBackendType.VAULT:
            if not self.vault_url:
                validation_result.issues.append("Vault URL required for vault backend")
                validation_result.is_valid = False

            if not self.vault_token:
                validation_result.issues.append(
                    "Vault token required for vault backend",
                )
                validation_result.is_valid = False

        elif self.backend.backend_type == EnumBackendType.FILE:
            if not self.file_path:
                validation_result.issues.append("File path required for file backend")
                validation_result.is_valid = False
            elif self.file_path.exists() and not self.file_path.is_file():
                validation_result.issues.append(
                    f"File path is not a file: {self.file_path}",
                )
                validation_result.is_valid = False

        # Security recommendations
        security_profile = self.backend.get_security_profile()
        if security_profile.security_level == EnumSecurityLevel.DEVELOPMENT_ONLY:
            validation_result.warnings.append(
                f"Backend '{self.backend.backend_type.value}' is for development only",
            )

        if security_profile.security_level == EnumSecurityLevel.NOT_RECOMMENDED:
            validation_result.warnings.append(
                f"Backend '{self.backend.backend_type.value}' is not recommended for production",
            )

        # Performance recommendations
        performance_profile = self.backend.get_performance_profile()
        if (
            performance_profile.latency == EnumLatencyLevel.MODERATE
            and self.cache_enabled
        ):
            validation_result.recommendations.append(
                "Consider enabling caching for better performance with this backend",
            )

        return validation_result

    def get_backend_config_dict(self) -> ModelBackendConfigData:
        """Get configuration dictionary for backend validation."""
        config = ModelBackendConfigData()

        if self.backend.backend_type == EnumBackendType.DOTENV:
            config = ModelBackendConfigData(
                dotenv_path=str(self.dotenv_path) if self.dotenv_path else None,
                auto_load_dotenv=str(self.auto_load_dotenv),
                env_prefix=self.env_prefix,
            )

        elif self.backend.backend_type == EnumBackendType.VAULT:
            config = ModelBackendConfigData(
                vault_url=self.vault_url,
                vault_token=(
                    self.vault_token.get_secret_value() if self.vault_token else None
                ),
                vault_namespace=self.vault_namespace,
                vault_path=self.vault_path,
            )

        elif self.backend.backend_type == EnumBackendType.KUBERNETES:
            config = ModelBackendConfigData(
                namespace=self.kubernetes_namespace,
                secret_name=self.kubernetes_secret_name,
            )

        elif self.backend.backend_type == EnumBackendType.FILE:
            config = ModelBackendConfigData(
                file_path=str(self.file_path) if self.file_path else None,
                encryption_key=(
                    self.encryption_key.get_secret_value()
                    if self.encryption_key
                    else None
                ),
            )

        elif self.backend.backend_type == EnumBackendType.ENVIRONMENT:
            config = ModelBackendConfigData(env_prefix=self.env_prefix)

        return config

    # === Environment Detection & Auto-Configuration ===

    def detect_and_configure_backend(self) -> "ModelSecretConfig":
        """Detect environment and configure optimal backend."""
        environment_type = self.backend.detect_environment_type()
        recommended_backends = self.backend.get_recommended_backends(environment_type)

        # Create new config with recommended backend
        new_backend = ModelSecretBackend(backend_type=recommended_backends[0])

        # Set up fallback backends
        fallback_backends = [
            ModelSecretBackend(backend_type=backend_type)
            for backend_type in recommended_backends[1:]
        ]

        # Auto-configure based on environment
        config_updates = {
            "backend": new_backend,
            "fallback_backends": fallback_backends,
        }

        if environment_type == "development":
            # Look for .env files
            for env_file in [".env", ".env.local", ".env.development"]:
                env_path = Path(env_file)
                if env_path.exists():
                    config_updates["dotenv_path"] = env_path
                    break

        elif environment_type == "kubernetes":
            # Auto-detect namespace
            namespace_file = Path(
                "/var/run/secrets/kubernetes.io/serviceaccount/namespace",
            )
            if namespace_file.exists():
                try:
                    config_updates["kubernetes_namespace"] = (
                        namespace_file.read_text().strip()
                    )
                except (AttributeError, KeyError, OSError, ValueError) as e:
                    msg = f"Failed to read Kubernetes namespace file: {e}"
                    raise ModelOnexError(
                        msg,
                        error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                        component="secret_config",
                        operation="detect_environment_config",
                    )

        return self.model_copy(update=config_updates)

    def get_environment_recommendations(self) -> list[str]:
        """Get environment-specific recommendations."""
        environment_type = self.backend.detect_environment_type()
        recommendations = []

        if environment_type == "development":
            recommendations.extend(
                [
                    "Use .env files for local development",
                    "Never commit .env files to version control",
                    "Consider using .env.example for team templates",
                ],
            )

        elif environment_type == "production":
            recommendations.extend(
                [
                    "Use Vault or Kubernetes secrets for production",
                    "Enable audit logging for compliance",
                    "Consider secret rotation policies",
                ],
            )

        elif environment_type == "ci":
            recommendations.extend(
                [
                    "Use environment variables in CI/CD pipelines",
                    "Ensure secrets are not logged in build outputs",
                    "Use CI/CD secret management features",
                ],
            )

        return recommendations

    # === Performance Optimization ===

    def get_performance_optimization_config(self) -> ModelPerformanceOptimizationConfig:
        """Get performance optimization configuration for this backend."""
        performance_profile = self.backend.get_performance_profile()

        # Cache recommendations
        if performance_profile.latency in [
            EnumLatencyLevel.MODERATE,
            EnumLatencyLevel.HIGH,
        ]:
            cache_enabled = True
            cache_ttl_seconds = DEFAULT_CACHE_TTL_SECONDS  # 5 minutes
        else:
            cache_enabled = self.cache_enabled
            cache_ttl_seconds = self.cache_ttl_seconds

        # Connection pooling for remote backends
        if self.backend.is_production_ready():
            connection_pool_enabled = True
            max_connections = 10
            connection_timeout = 5
        else:
            connection_pool_enabled = False
            max_connections = 1
            connection_timeout = 30

        return ModelPerformanceOptimizationConfig(
            cache_enabled=cache_enabled,
            cache_ttl_seconds=cache_ttl_seconds,
            connection_pooling=connection_pool_enabled,
            max_connections=max_connections,
            connection_timeout=connection_timeout,
        )

    # === Health & Monitoring ===

    def health_check(self) -> ModelSecretHealthCheckResult:
        """Perform health check on secret configuration."""
        import time

        start_time = time.time()
        issues = []
        backend_available = False
        config_valid = False

        try:
            # Validate configuration
            validation = self.validate_configuration()
            config_valid = validation.is_valid
            issues.extend(validation.issues)

            # Test backend availability
            if self.backend.backend_type == EnumBackendType.ENVIRONMENT:
                backend_available = True

            elif self.backend.backend_type == EnumBackendType.DOTENV:
                if self.dotenv_path and self.dotenv_path.exists():
                    backend_available = True
                else:
                    backend_available = False
                    issues.append("Dotenv file not accessible")

            elif self.backend.backend_type == EnumBackendType.VAULT:
                # Would need actual Vault client for real health check
                backend_available = bool(self.vault_url and self.vault_token)
                if not backend_available:
                    issues.append("Vault configuration incomplete")

            elif self.backend.backend_type == EnumBackendType.FILE:
                if self.file_path:
                    backend_available = self.file_path.exists()
                    if not backend_available:
                        issues.append("Secret file not accessible")
                else:
                    backend_available = False
                    issues.append("File path not configured")

        except (AttributeError, KeyError, OSError, ValueError) as e:
            config_valid = False
            backend_available = False
            issues.append(f"Health check failed: {e}")

        finally:
            response_time_ms = int((time.time() - start_time) * 1000)

        return ModelSecretHealthCheckResult(
            healthy=config_valid and backend_available,
            backend_available=backend_available,
            config_valid=config_valid,
            issues=issues,
            response_time_ms=response_time_ms,
        )

    # === Factory Methods ===

    @classmethod
    def create_for_development(
        cls,
        dotenv_path: str | None = None,
    ) -> "ModelSecretConfig":
        """Create configuration optimized for development environment."""
        return cls(
            backend=ModelSecretBackend.create_dotenv(),
            dotenv_path=Path(dotenv_path) if dotenv_path else Path(".env"),
            auto_load_dotenv=True,
            fallback_backends=[ModelSecretBackend.create_environment()],
            cache_enabled=False,  # Disable cache for development
        )

    @classmethod
    def create_for_production(
        cls, backend_type: EnumBackendType = EnumBackendType.VAULT
    ) -> "ModelSecretConfig":
        """Create configuration optimized for production environment."""
        backend = ModelSecretBackend(backend_type=backend_type)

        fallback_backends = []
        if backend_type != EnumBackendType.ENVIRONMENT:
            fallback_backends.append(ModelSecretBackend.create_environment())

        return cls(
            backend=backend,
            fallback_backends=fallback_backends,
            cache_enabled=True,
            cache_ttl_seconds=300,
        )

    @classmethod
    def create_for_kubernetes(
        cls,
        namespace: str = "default",
        secret_name: str = "onex-secrets",
    ) -> "ModelSecretConfig":
        """Create configuration for Kubernetes environment."""
        return cls(
            backend=ModelSecretBackend.create_kubernetes(),
            kubernetes_namespace=namespace,
            kubernetes_secret_name=secret_name,
            fallback_backends=[ModelSecretBackend.create_environment()],
            cache_enabled=True,
        )

    @classmethod
    def create_auto_configured(cls) -> "ModelSecretConfig":
        """Create automatically configured instance based on environment detection."""
        temp_config = cls()
        return temp_config.detect_and_configure_backend()


# Fix forward references for Pydantic models
try:
    ModelSecretConfig.model_rebuild()
except (
    Exception
):  # error-ok: model_rebuild may fail during circular import resolution, safe to ignore
    pass
