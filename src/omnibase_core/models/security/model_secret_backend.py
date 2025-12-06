import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_backend_type import EnumBackendType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_latency_level import EnumLatencyLevel
from omnibase_core.enums.enum_overhead_type import EnumOverheadType
from omnibase_core.enums.enum_scalability_level import EnumScalabilityLevel
from omnibase_core.enums.enum_security_level import EnumSecurityLevel
from omnibase_core.enums.enum_throughput_level import EnumThroughputLevel
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .model_backend_capabilities import ModelBackendCapabilities
from .model_backend_config import ModelBackendConfig
from .model_backend_config_validation import ModelBackendConfigValidation
from .model_backend_performance_profile import ModelBackendPerformanceProfile
from .model_backend_security_profile import ModelBackendSecurityProfile


class ModelSecretBackend(BaseModel):
    """
    Enterprise-grade secret backend configuration with comprehensive validation,
    business logic, and backend-specific capability management.

    Features:
    - Strong typing with comprehensive validation
    - Backend capability assessment and validation
    - Configuration validation for each backend type
    - Environment detection and recommendations
    - Security assessment and best practices
    - Performance characteristics analysis
    """

    backend_type: EnumBackendType = Field(
        default=EnumBackendType.ENVIRONMENT,
        description="Secret backend type",
    )

    @field_validator("backend_type", mode="before")
    @classmethod
    def validate_backend_type(cls, v: Any) -> EnumBackendType:
        """Validate and normalize backend type."""
        if isinstance(v, EnumBackendType):
            return v

        if isinstance(v, str):
            return EnumBackendType.from_string(v)

        msg = f"Invalid backend type: {v}"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    # === Backend Capability Assessment ===

    # Backend capabilities mapping
    BACKEND_CAPABILITIES: dict[EnumBackendType, ModelBackendCapabilities] = {
        EnumBackendType.ENVIRONMENT: ModelBackendCapabilities(
            supports_secrets=True,
            supports_rotation=False,
            supports_encryption=False,
            supports_audit=False,
            supports_versioning=False,
            supports_access_control=False,
            production_ready=True,
            requires_external_service=False,
        ),
        EnumBackendType.DOTENV: ModelBackendCapabilities(
            supports_secrets=True,
            supports_rotation=False,
            supports_encryption=False,
            supports_audit=False,
            supports_versioning=True,  # Via version control
            supports_access_control=True,  # Via file permissions
            production_ready=False,  # Development only
            requires_external_service=False,
        ),
        EnumBackendType.VAULT: ModelBackendCapabilities(
            supports_secrets=True,
            supports_rotation=True,
            supports_encryption=True,
            supports_audit=True,
            supports_versioning=True,
            supports_access_control=True,
            production_ready=True,
            requires_external_service=True,
        ),
        EnumBackendType.KUBERNETES: ModelBackendCapabilities(
            supports_secrets=True,
            supports_rotation=True,
            supports_encryption=True,
            supports_audit=True,
            supports_versioning=False,
            supports_access_control=True,
            production_ready=True,
            requires_external_service=True,
        ),
        EnumBackendType.FILE: ModelBackendCapabilities(
            supports_secrets=True,
            supports_rotation=False,
            supports_encryption=False,
            supports_audit=False,
            supports_versioning=True,  # Via version control
            supports_access_control=True,  # Via file permissions
            production_ready=False,  # Not recommended
            requires_external_service=False,
        ),
    }

    def get_backend_capabilities(self) -> ModelBackendCapabilities:
        """Get capabilities supported by this backend type."""
        return self.BACKEND_CAPABILITIES.get(
            self.backend_type,
            ModelBackendCapabilities(
                supports_secrets=True,
                supports_rotation=False,
                supports_encryption=False,
                supports_audit=False,
                supports_versioning=False,
                supports_access_control=False,
                production_ready=False,
                requires_external_service=False,
            ),  # Default capabilities
        )

    def supports_capability(self, capability: str) -> bool:
        """Check if backend supports a specific capability."""
        capabilities = self.get_backend_capabilities()
        return getattr(capabilities, capability, False)

    def is_production_ready(self) -> bool:
        """Check if this backend is suitable for production use."""
        return self.supports_capability("production_ready")

    def requires_external_service(self) -> bool:
        """Check if this backend requires an external service."""
        return self.supports_capability("requires_external_service")

    # === Configuration Validation ===

    # Configuration field mappings
    REQUIRED_CONFIG_FIELDS: dict[EnumBackendType, set[str]] = {
        EnumBackendType.ENVIRONMENT: set(),  # No additional config required
        EnumBackendType.DOTENV: {"dotenv_path"},
        EnumBackendType.VAULT: {"vault_url", "vault_token"},
        EnumBackendType.KUBERNETES: set(),  # Uses in-cluster config
        EnumBackendType.FILE: {"file_path"},
    }

    OPTIONAL_CONFIG_FIELDS: dict[EnumBackendType, set[str]] = {
        EnumBackendType.ENVIRONMENT: {"env_prefix"},
        EnumBackendType.DOTENV: {"auto_load_dotenv", "env_prefix"},
        EnumBackendType.VAULT: {"vault_namespace", "vault_path", "vault_role"},
        EnumBackendType.KUBERNETES: {"namespace", "secret_name"},
        EnumBackendType.FILE: {"encryption_key", "file_permissions"},
    }

    def get_required_config_fields(self) -> set[str]:
        """Get required configuration fields for this backend."""
        return self.REQUIRED_CONFIG_FIELDS.get(self.backend_type, set())

    def get_optional_config_fields(self) -> set[str]:
        """Get optional configuration fields for this backend."""
        return self.OPTIONAL_CONFIG_FIELDS.get(self.backend_type, set())

    def validate_config(
        self,
        config: ModelBackendConfig,
    ) -> ModelBackendConfigValidation:
        """Validate configuration for this backend type."""
        issues = []
        required_fields = self.get_required_config_fields()

        # Check required fields
        for field in required_fields:
            if not getattr(config, field, None):
                issues.append(
                    f"Missing required field for {self.backend_type.value} backend: {field}",
                )

        # Backend-specific validation
        if self.backend_type == EnumBackendType.DOTENV:
            if config.dotenv_path and not config.dotenv_path.exists():
                issues.append(f"Dotenv file does not exist: {config.dotenv_path}")

        elif self.backend_type == EnumBackendType.VAULT:
            if config.vault_url and not config.vault_url.startswith(
                ("http://", "https://"),
            ):
                issues.append("Vault URL must start with http:// or https://")

        elif self.backend_type == EnumBackendType.FILE and config.file_path:
            if config.file_path.exists() and not config.file_path.is_file():
                issues.append(f"File path is not a file: {config.file_path}")
            elif not config.file_path.parent.exists():
                issues.append(
                    f"Directory does not exist: {config.file_path.parent}",
                )

        return ModelBackendConfigValidation(
            is_valid=len(issues) == 0,
            issues=issues,
            required_fields_missing=[
                field for field in required_fields if not getattr(config, field, None)
            ],
        )

    # === Environment Detection ===

    def detect_environment_type(self) -> str:
        """Detect the current environment type for backend recommendations."""
        # Check for Kubernetes environment
        if Path("/var/run/secrets/kubernetes.io/serviceaccount").exists() or os.getenv(
            "KUBERNETES_SERVICE_HOST",
        ):
            return "kubernetes"

        # Check for development environment indicators
        if (
            Path(".env").exists()
            or Path(".env.local").exists()
            or os.getenv("NODE_ENV") == "development"
            or os.getenv("ENVIRONMENT") == "development"
        ):
            return "development"

        # Check for CI environment
        ci_indicators = ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", "GITLAB_CI"]
        if any(os.getenv(indicator) for indicator in ci_indicators):
            return "ci"

        # Default to production
        return "production"

    ENVIRONMENT_RECOMMENDATIONS: dict[str, list[EnumBackendType]] = {
        "development": [EnumBackendType.DOTENV, EnumBackendType.ENVIRONMENT],
        "ci": [EnumBackendType.ENVIRONMENT],
        "kubernetes": [EnumBackendType.KUBERNETES, EnumBackendType.VAULT],
        "production": [
            EnumBackendType.VAULT,
            EnumBackendType.KUBERNETES,
            EnumBackendType.ENVIRONMENT,
        ],
    }

    def get_recommended_backends(
        self,
        environment_type: str | None = None,
    ) -> list[EnumBackendType]:
        """Get recommended backends for the given environment."""
        if environment_type is None:
            environment_type = self.detect_environment_type()

        return self.ENVIRONMENT_RECOMMENDATIONS.get(
            environment_type,
            [EnumBackendType.ENVIRONMENT],
        )

    # === Security Assessment ===

    # Security profile mappings
    SECURITY_PROFILES: dict[EnumBackendType, ModelBackendSecurityProfile] = {
        EnumBackendType.ENVIRONMENT: ModelBackendSecurityProfile(
            encryption_at_rest="none",
            encryption_in_transit="none",
            access_control="os_level",
            audit_logging="none",
            secret_rotation="manual",
            security_level=EnumSecurityLevel.BASIC,
        ),
        EnumBackendType.DOTENV: ModelBackendSecurityProfile(
            encryption_at_rest="none",
            encryption_in_transit="none",
            access_control="file_permissions",
            audit_logging="version_control",
            secret_rotation="manual",
            security_level=EnumSecurityLevel.DEVELOPMENT_ONLY,
        ),
        EnumBackendType.VAULT: ModelBackendSecurityProfile(
            encryption_at_rest="strong",
            encryption_in_transit="tls",
            access_control="policy_based",
            audit_logging="comprehensive",
            secret_rotation="automatic",
            security_level=EnumSecurityLevel.ENTERPRISE,
        ),
        EnumBackendType.KUBERNETES: ModelBackendSecurityProfile(
            encryption_at_rest="configurable",
            encryption_in_transit="tls",
            access_control="rbac",
            audit_logging="cluster_level",
            secret_rotation="manual_or_operator",
            security_level=EnumSecurityLevel.PRODUCTION,
        ),
        EnumBackendType.FILE: ModelBackendSecurityProfile(
            encryption_at_rest="optional",
            encryption_in_transit="none",
            access_control="file_permissions",
            audit_logging="version_control",
            secret_rotation="manual",
            security_level=EnumSecurityLevel.NOT_RECOMMENDED,
        ),
    }

    def get_security_profile(self) -> ModelBackendSecurityProfile:
        """Get security characteristics of this backend."""
        return self.SECURITY_PROFILES.get(
            self.backend_type,
            ModelBackendSecurityProfile(
                encryption_at_rest="none",
                encryption_in_transit="none",
                access_control="none",
                audit_logging="none",
                secret_rotation="manual",
                security_level=EnumSecurityLevel.BASIC,
            ),  # Default security profile
        )

    # Security recommendations mappings
    SECURITY_RECOMMENDATIONS: dict[EnumBackendType, list[str]] = {
        EnumBackendType.ENVIRONMENT: [
            "Use environment variables for production deployment",
            "Ensure secrets are not logged or exposed in process list[Any]s",
            "Consider Vault or Kubernetes secrets for enhanced security",
        ],
        EnumBackendType.DOTENV: [
            "Only use .env files for development environments",
            "Never commit .env files to version control",
            "Use .env.example templates for team collaboration",
        ],
        EnumBackendType.VAULT: [
            "Enable audit logging for compliance",
            "Use dynamic secrets where possible",
            "Implement proper Vault policies and authentication",
        ],
        EnumBackendType.KUBERNETES: [
            "Enable encryption at rest for etcd",
            "Use RBAC to control access to secrets",
            "Consider using sealed secrets or external secret operators",
        ],
        EnumBackendType.FILE: [
            "Encrypt files containing secrets",
            "Set restrictive file permissions (600)",
            "Consider using Vault or Kubernetes secrets instead",
        ],
    }

    def get_security_recommendations(self) -> list[str]:
        """Get security recommendations for this backend."""
        return self.SECURITY_RECOMMENDATIONS.get(self.backend_type, [])

    # === Performance Characteristics ===

    # Performance profile mappings
    PERFORMANCE_PROFILES: dict[EnumBackendType, ModelBackendPerformanceProfile] = {
        EnumBackendType.ENVIRONMENT: ModelBackendPerformanceProfile(
            latency=EnumLatencyLevel.MINIMAL,
            throughput=EnumThroughputLevel.HIGH,
            scalability=EnumScalabilityLevel.EXCELLENT,
            overhead=EnumOverheadType.NONE,
        ),
        EnumBackendType.DOTENV: ModelBackendPerformanceProfile(
            latency=EnumLatencyLevel.MINIMAL,
            throughput=EnumThroughputLevel.HIGH,
            scalability=EnumScalabilityLevel.GOOD,
            overhead=EnumOverheadType.FILE_IO,
        ),
        EnumBackendType.VAULT: ModelBackendPerformanceProfile(
            latency=EnumLatencyLevel.MODERATE,
            throughput=EnumThroughputLevel.MODERATE,
            scalability=EnumScalabilityLevel.EXCELLENT,
            overhead=EnumOverheadType.NETWORK_AUTH,
        ),
        EnumBackendType.KUBERNETES: ModelBackendPerformanceProfile(
            latency=EnumLatencyLevel.LOW,
            throughput=EnumThroughputLevel.HIGH,
            scalability=EnumScalabilityLevel.EXCELLENT,
            overhead=EnumOverheadType.API_CALLS,
        ),
        EnumBackendType.FILE: ModelBackendPerformanceProfile(
            latency=EnumLatencyLevel.LOW,
            throughput=EnumThroughputLevel.HIGH,
            scalability=EnumScalabilityLevel.LIMITED,
            overhead=EnumOverheadType.FILE_IO,
        ),
    }

    def get_performance_profile(self) -> ModelBackendPerformanceProfile:
        """Get performance characteristics of this backend."""
        return self.PERFORMANCE_PROFILES.get(
            self.backend_type,
            ModelBackendPerformanceProfile(
                latency=EnumLatencyLevel.MINIMAL,
                throughput=EnumThroughputLevel.MODERATE,
                scalability=EnumScalabilityLevel.GOOD,
                overhead=EnumOverheadType.NONE,
            ),  # Default performance profile
        )

    # === Factory Methods ===

    @classmethod
    def create_environment(cls) -> "ModelSecretBackend":
        """Create environment variable backend configuration."""
        return cls(backend_type=EnumBackendType.ENVIRONMENT)

    @classmethod
    def create_dotenv(cls) -> "ModelSecretBackend":
        """Create .env file backend configuration."""
        return cls(backend_type=EnumBackendType.DOTENV)

    @classmethod
    def create_vault(cls) -> "ModelSecretBackend":
        """Create Vault backend configuration."""
        return cls(backend_type=EnumBackendType.VAULT)

    @classmethod
    def create_kubernetes(cls) -> "ModelSecretBackend":
        """Create Kubernetes secrets backend configuration."""
        return cls(backend_type=EnumBackendType.KUBERNETES)

    @classmethod
    def create_file(cls) -> "ModelSecretBackend":
        """Create file-based backend configuration."""
        return cls(backend_type=EnumBackendType.FILE)

    @classmethod
    def create_for_environment(
        cls,
        environment_type: str | None = None,
    ) -> "ModelSecretBackend":
        """Create backend configuration recommended for the current environment."""
        temp_instance = cls(backend_type=EnumBackendType.ENVIRONMENT)
        if environment_type is None:
            environment_type = temp_instance.detect_environment_type()

        recommended = temp_instance.get_recommended_backends(environment_type)
        if not recommended or len(recommended) == 0:
            msg = f"No backends recommended for environment type: {environment_type}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        backend_type = recommended[0]

        return cls(backend_type=backend_type)
