import os
import re
from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import Field, SecretStr, field_validator

from omnibase_core.model.core.model_connection_properties import \
    ModelConnectionProperties
from omnibase_core.model.core.model_masked_connection_properties import \
    ModelMaskedConnectionProperties

# Moved to TYPE_CHECKING import

if TYPE_CHECKING:
    from omnibase_core.model.core import (
        ModelPerformanceProfile,
        ModelSecurityAssessment,
    )

from omnibase_core.model.security.model_secure_credentials import \
    ModelSecureCredentials


class ModelKafkaSecureConfig(ModelSecureCredentials):
    """
    Enterprise-grade secure Kafka configuration with comprehensive security features,
    connection management, performance optimization, and operational monitoring.

    Features:
    - Comprehensive authentication and encryption support
    - Security assessment and configuration validation
    - Performance profiling and optimization recommendations
    - Connection health monitoring and troubleshooting
    - Environment-specific configuration management
    - Producer/consumer configuration optimization
    """

    bootstrap_servers: str = Field(
        ...,
        description="Kafka bootstrap servers (comma-separated)",
        pattern=r"^[a-zA-Z0-9\-\.:,\s]+$",
        max_length=500,
    )

    security_protocol: str = Field(
        default="PLAINTEXT",
        description="Security protocol",
        pattern=r"^(PLAINTEXT|SSL|SASL_PLAINTEXT|SASL_SSL)$",
    )

    sasl_mechanism: Optional[str] = Field(
        default=None,
        description="SASL mechanism (PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, GSSAPI, OAUTHBEARER)",
        pattern=r"^(PLAIN|SCRAM-SHA-256|SCRAM-SHA-512|GSSAPI|OAUTHBEARER)$",
    )

    sasl_username: Optional[str] = Field(
        default=None, description="SASL username", max_length=100
    )

    sasl_password: Optional[SecretStr] = Field(
        default=None, description="SASL password (secured)"
    )

    ssl_keyfile_path: Optional[str] = Field(
        default=None, description="Path to SSL key file", max_length=500
    )

    ssl_keyfile_password: Optional[SecretStr] = Field(
        default=None, description="SSL key file password (secured)"
    )

    ssl_certfile_path: Optional[str] = Field(
        default=None, description="Path to SSL certificate file", max_length=500
    )

    ssl_cafile_path: Optional[str] = Field(
        default=None, description="Path to SSL CA file", max_length=500
    )

    ssl_check_hostname: bool = Field(
        default=True, description="Whether to check SSL hostname"
    )

    ssl_verify_mode: str = Field(
        default="required",
        description="SSL certificate verification mode",
        pattern=r"^(none|optional|required)$",
    )

    client_id: Optional[str] = Field(
        default=None, description="Kafka client ID for identification", max_length=100
    )

    request_timeout_ms: int = Field(
        default=30000, description="Request timeout in milliseconds", ge=1000, le=300000
    )

    retry_backoff_ms: int = Field(
        default=100, description="Retry backoff time in milliseconds", ge=0, le=10000
    )

    max_retries: int = Field(
        default=3, description="Maximum number of retries", ge=0, le=10
    )

    compression_type: str = Field(
        default="none",
        description="Compression type for messages",
        pattern=r"^(none|gzip|snappy|lz4|zstd)$",
    )

    @field_validator("bootstrap_servers")
    @classmethod
    def validate_bootstrap_servers(cls, v: str) -> str:
        """Validate bootstrap servers format."""
        if not v or not v.strip():
            raise ValueError("Bootstrap servers cannot be empty")

        v = v.strip()

        # Split and validate each server
        servers = [server.strip() for server in v.split(",")]
        validated_servers = []

        for server in servers:
            if not server:
                continue

            # Basic format validation (host:port)
            if ":" not in server:
                raise ValueError(f"Invalid server format (missing port): {server}")

            host, port_str = server.rsplit(":", 1)

            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError(f"Invalid port number: {port}")
            except ValueError:
                raise ValueError(f"Invalid port in server: {server}")

            # Basic hostname validation
            if not re.match(r"^[a-zA-Z0-9\-\.]+$", host):
                raise ValueError(f"Invalid hostname: {host}")

            validated_servers.append(f"{host}:{port}")

        if not validated_servers:
            raise ValueError("No valid servers found in bootstrap_servers")

        return ",".join(validated_servers)

    @field_validator("security_protocol")
    @classmethod
    def validate_security_protocol(cls, v: str) -> str:
        """Validate and normalize security protocol."""
        if not v:
            return "PLAINTEXT"

        v = v.strip().upper()
        valid_protocols = {"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"}

        if v not in valid_protocols:
            raise ValueError(
                f"Invalid security protocol: {v}. Must be one of: {valid_protocols}"
            )

        return v

    # === Security Assessment ===

    def get_security_assessment(self) -> "ModelSecurityAssessment":
        """Comprehensive security assessment of Kafka configuration."""
        assessment = {
            "security_level": "none",
            "encryption_in_transit": False,
            "authentication_enabled": False,
            "certificate_validation": False,
            "vulnerabilities": [],
            "recommendations": [],
            "compliance_status": {},
        }

        # Assess security protocol
        if self.security_protocol == "PLAINTEXT":
            assessment["security_level"] = "none"
            assessment["vulnerabilities"].extend(
                [
                    "No encryption - traffic sent in plaintext",
                    "No authentication - unauthorized access possible",
                ]
            )
            assessment["recommendations"].extend(
                [
                    "Enable SSL/TLS encryption (security_protocol: SSL or SASL_SSL)",
                    "Enable SASL authentication for access control",
                ]
            )

        elif self.security_protocol == "SSL":
            assessment["security_level"] = "medium"
            assessment["encryption_in_transit"] = True
            assessment["certificate_validation"] = self.ssl_check_hostname

            if not self.ssl_check_hostname:
                assessment["vulnerabilities"].append(
                    "SSL hostname verification disabled"
                )
                assessment["recommendations"].append("Enable SSL hostname verification")

            if self.ssl_verify_mode == "none":
                assessment["vulnerabilities"].append(
                    "SSL certificate verification disabled"
                )
                assessment["recommendations"].append(
                    "Enable SSL certificate verification"
                )

        elif self.security_protocol in ["SASL_PLAINTEXT", "SASL_SSL"]:
            assessment["authentication_enabled"] = True

            if self.security_protocol == "SASL_SSL":
                assessment["security_level"] = "high"
                assessment["encryption_in_transit"] = True
                assessment["certificate_validation"] = self.ssl_check_hostname
            else:
                assessment["security_level"] = "medium"
                assessment["vulnerabilities"].append(
                    "SASL credentials sent in plaintext"
                )
                assessment["recommendations"].append(
                    "Use SASL_SSL for encrypted SASL authentication"
                )

            # Assess SASL mechanism
            if self.sasl_mechanism == "PLAIN":
                assessment["vulnerabilities"].append(
                    "PLAIN SASL mechanism is less secure"
                )
                assessment["recommendations"].append(
                    "Consider SCRAM-SHA-256 or SCRAM-SHA-512"
                )
            elif self.sasl_mechanism in ["SCRAM-SHA-256", "SCRAM-SHA-512"]:
                assessment["security_level"] = (
                    "high"
                    if assessment["security_level"] == "medium"
                    else assessment["security_level"]
                )

        # Assess credentials
        if self.sasl_username and not self.sasl_password:
            assessment["vulnerabilities"].append(
                "SASL username configured but password missing"
            )

        # Compliance assessment
        assessment["compliance_status"] = {
            "pci_dss": assessment["encryption_in_transit"]
            and assessment["authentication_enabled"],
            "hipaa": assessment["encryption_in_transit"]
            and assessment["authentication_enabled"],
            "gdpr": assessment["encryption_in_transit"],
            "sox": assessment["authentication_enabled"]
            and assessment.get("audit_logging", False),
        }

        return assessment

    def is_production_ready(self) -> bool:
        """Check if configuration is suitable for production deployment."""
        assessment = self.get_security_assessment()

        # Production requires at least medium security level
        if assessment["security_level"] == "none":
            return False

        # Check for critical vulnerabilities
        critical_vulnerabilities = [
            "No encryption - traffic sent in plaintext",
            "No authentication - unauthorized access possible",
        ]

        for vuln in assessment["vulnerabilities"]:
            if vuln in critical_vulnerabilities:
                return False

        return True

    # === Connection Management ===

    def get_connection_properties(self) -> ModelConnectionProperties:
        """Get Kafka client connection properties."""
        # Note: Kafka uses dot-notation properties, not the generic connection model
        # This returns a dict-like structure for Kafka compatibility
        props = {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "request.timeout.ms": self.request_timeout_ms,
            "retry.backoff.ms": self.retry_backoff_ms,
            "retries": self.max_retries,
            "compression.type": self.compression_type,
        }

        if self.client_id:
            props["client.id"] = self.client_id

        # SASL configuration
        if self.security_protocol in ["SASL_PLAINTEXT", "SASL_SSL"]:
            if self.sasl_mechanism:
                props["sasl.mechanism"] = self.sasl_mechanism

            if self.sasl_username and self.sasl_password:
                props["sasl.username"] = self.sasl_username
                props["sasl.password"] = self.sasl_password.get_secret_value()

        # SSL configuration
        if self.security_protocol in ["SSL", "SASL_SSL"]:
            props["ssl.check.hostname"] = self.ssl_check_hostname
            props["ssl.verify.mode"] = self.ssl_verify_mode

            if self.ssl_keyfile_path:
                props["ssl.keyfile"] = self.ssl_keyfile_path

            if self.ssl_keyfile_password:
                props["ssl.keyfile.password"] = (
                    self.ssl_keyfile_password.get_secret_value()
                )

            if self.ssl_certfile_path:
                props["ssl.certfile"] = self.ssl_certfile_path

            if self.ssl_cafile_path:
                props["ssl.cafile"] = self.ssl_cafile_path

        # Return ModelConnectionProperties with Kafka-specific mapping
        return ModelConnectionProperties(
            connection_string=f"kafka://{self.bootstrap_servers}",
            driver="kafka",
            protocol=self.security_protocol.lower(),
            host=(
                self.bootstrap_servers.split(",")[0].split(":")[0]
                if ":" in self.bootstrap_servers
                else self.bootstrap_servers
            ),
            port=(
                int(self.bootstrap_servers.split(",")[0].split(":")[1])
                if ":" in self.bootstrap_servers
                else 9092
            ),
            username=self.sasl_username,
            password=self.sasl_password,
            auth_mechanism=self.sasl_mechanism,
            use_ssl=self.security_protocol in ["SSL", "SASL_SSL"],
            ssl_mode=self.ssl_verify_mode,
            ssl_cert=self.ssl_certfile_path,
            ssl_key=self.ssl_keyfile_path,
            ssl_ca=self.ssl_cafile_path,
            options=props,  # Store all Kafka-specific properties in options
        )

    def get_masked_connection_properties(self) -> ModelMaskedConnectionProperties:
        """Get connection properties with secrets masked for logging."""
        props = self.get_connection_properties()

        # Create masked version from connection properties
        masked = ModelMaskedConnectionProperties(
            connection_string=props.connection_string,
            driver=props.driver,
            protocol=props.protocol,
            host=props.host,
            port=props.port,
            database=props.database,
            username=props.username if props.username else None,
            password="***MASKED***",  # Always mask password
            auth_mechanism=props.auth_mechanism,
            use_ssl=props.use_ssl,
            masked_fields=["password"],
        )

        # Mask sensitive values in options
        if props.options:
            masked_options = props.options.copy()
            sensitive_keys = {"sasl.password", "ssl.keyfile.password"}
            for key in sensitive_keys:
                if key in masked_options:
                    masked_options[key] = "***MASKED***"
                    masked.masked_fields.append(key)
            # Store masked options back (if ModelMaskedConnectionProperties has options field)

        return masked

    # === Performance Optimization ===

    def get_performance_profile(self) -> "ModelPerformanceProfile":
        """Get performance characteristics and recommendations."""
        profile = {
            "compression_efficiency": self._get_compression_efficiency(),
            "latency_impact": self._get_latency_impact(),
            "throughput_optimization": self._get_throughput_recommendations(),
            "resource_usage": self._get_resource_usage_profile(),
        }

        return profile

    def _get_compression_efficiency(self) -> Dict[str, str]:
        """Assess compression type efficiency."""
        compression_profiles = {
            "none": {
                "cpu_usage": "none",
                "compression_ratio": "none",
                "recommendation": "consider enabling for large messages",
            },
            "gzip": {
                "cpu_usage": "high",
                "compression_ratio": "excellent",
                "recommendation": "good for throughput over latency",
            },
            "snappy": {
                "cpu_usage": "medium",
                "compression_ratio": "good",
                "recommendation": "balanced performance",
            },
            "lz4": {
                "cpu_usage": "low",
                "compression_ratio": "good",
                "recommendation": "excellent for latency",
            },
            "zstd": {
                "cpu_usage": "medium",
                "compression_ratio": "excellent",
                "recommendation": "best overall performance",
            },
        }

        return compression_profiles.get(self.compression_type, {})

    def _get_latency_impact(self) -> Dict[str, str]:
        """Assess configuration impact on latency."""
        impact = {"overall": "low", "factors": []}

        # Security protocol impact
        if self.security_protocol in ["SSL", "SASL_SSL"]:
            impact["factors"].append("SSL handshake adds latency")
            impact["overall"] = "medium"

        if self.security_protocol in ["SASL_PLAINTEXT", "SASL_SSL"]:
            impact["factors"].append("SASL authentication adds latency")

        # Compression impact
        if self.compression_type in ["gzip"]:
            impact["factors"].append("High compression increases latency")
            impact["overall"] = "high" if impact["overall"] == "medium" else "medium"

        # Timeout impact
        if self.request_timeout_ms > 60000:
            impact["factors"].append("High timeout may delay error detection")

        return impact

    def _get_throughput_recommendations(self) -> List[str]:
        """Get throughput optimization recommendations."""
        recommendations = []

        if self.compression_type == "none":
            recommendations.append(
                "Enable compression (lz4 or snappy) for better throughput"
            )

        if self.max_retries > 5:
            recommendations.append(
                "Consider reducing max_retries for faster failure detection"
            )

        if self.retry_backoff_ms > 1000:
            recommendations.append(
                "Consider reducing retry_backoff_ms for faster retries"
            )

        return recommendations

    def _get_resource_usage_profile(self) -> Dict[str, str]:
        """Get resource usage characteristics."""
        profile = {
            "memory_usage": "medium",
            "cpu_usage": "low",
            "network_usage": "medium",
        }

        # Adjust based on compression
        compression_cpu_impact = {
            "none": "none",
            "gzip": "high",
            "snappy": "medium",
            "lz4": "low",
            "zstd": "medium",
        }

        profile["cpu_usage"] = compression_cpu_impact.get(self.compression_type, "low")

        # SSL increases CPU usage
        if self.security_protocol in ["SSL", "SASL_SSL"]:
            current_cpu = profile["cpu_usage"]
            if current_cpu == "low":
                profile["cpu_usage"] = "medium"
            elif current_cpu == "medium":
                profile["cpu_usage"] = "high"

        return profile

    # === Health Check & Troubleshooting ===

    def can_connect(self) -> bool:
        """Test if configuration allows successful connection."""
        validation = self.validate_credentials()
        if not validation["is_valid"]:
            return False

        # Check required fields for SASL
        if self.security_protocol in ["SASL_PLAINTEXT", "SASL_SSL"]:
            if not self.sasl_username or not self.sasl_password:
                return False

        # Check SSL files exist
        if self.security_protocol in ["SSL", "SASL_SSL"]:
            if self.ssl_keyfile_path and not os.path.exists(self.ssl_keyfile_path):
                return False
            if self.ssl_certfile_path and not os.path.exists(self.ssl_certfile_path):
                return False
            if self.ssl_cafile_path and not os.path.exists(self.ssl_cafile_path):
                return False

        return True

    def get_troubleshooting_guide(self) -> Dict[str, List[str]]:
        """Get troubleshooting guide for common issues."""
        guide = {
            "connection_failures": [
                "Verify bootstrap_servers are reachable",
                "Check security_protocol matches broker configuration",
                "Verify SASL credentials if using SASL authentication",
                "Check SSL certificates and paths if using SSL",
            ],
            "authentication_failures": [
                "Verify SASL username and password",
                "Check SASL mechanism is supported by broker",
                "Ensure SSL certificates are valid and not expired",
                "Verify SSL CA file contains broker's CA certificate",
            ],
            "performance_issues": [
                "Consider enabling compression for large messages",
                "Adjust request_timeout_ms and retry settings",
                "Check network latency to brokers",
                "Monitor client and broker CPU usage",
            ],
            "security_concerns": [
                "Use SASL_SSL for production environments",
                "Enable SSL hostname verification",
                "Use strong SASL mechanisms (SCRAM-SHA-256/512)",
                "Regularly rotate SASL passwords and SSL certificates",
            ],
        }

        return guide

    # === Environment Integration ===

    @classmethod
    def load_from_env(cls, env_prefix: str = "ONEX_KAFKA_") -> "ModelKafkaSecureConfig":
        """Load Kafka configuration from environment variables."""
        config_data = {
            "bootstrap_servers": os.getenv(
                f"{env_prefix}BOOTSTRAP_SERVERS", "localhost:9092"
            ),
            "security_protocol": os.getenv(
                f"{env_prefix}SECURITY_PROTOCOL", "PLAINTEXT"
            ),
            "sasl_mechanism": os.getenv(f"{env_prefix}SASL_MECHANISM"),
            "sasl_username": os.getenv(f"{env_prefix}SASL_USERNAME"),
            "ssl_keyfile_path": os.getenv(f"{env_prefix}SSL_KEYFILE_PATH"),
            "ssl_certfile_path": os.getenv(f"{env_prefix}SSL_CERTFILE_PATH"),
            "ssl_cafile_path": os.getenv(f"{env_prefix}SSL_CAFILE_PATH"),
            "ssl_check_hostname": os.getenv(
                f"{env_prefix}SSL_CHECK_HOSTNAME", "true"
            ).lower()
            == "true",
            "ssl_verify_mode": os.getenv(f"{env_prefix}SSL_VERIFY_MODE", "required"),
            "client_id": os.getenv(f"{env_prefix}CLIENT_ID"),
            "compression_type": os.getenv(f"{env_prefix}COMPRESSION_TYPE", "none"),
        }

        # Handle SecretStr fields
        sasl_password = os.getenv(f"{env_prefix}SASL_PASSWORD")
        if sasl_password:
            config_data["sasl_password"] = SecretStr(sasl_password)

        ssl_keyfile_password = os.getenv(f"{env_prefix}SSL_KEYFILE_PASSWORD")
        if ssl_keyfile_password:
            config_data["ssl_keyfile_password"] = SecretStr(ssl_keyfile_password)

        # Handle integer fields
        try:
            if timeout := os.getenv(f"{env_prefix}REQUEST_TIMEOUT_MS"):
                config_data["request_timeout_ms"] = int(timeout)
            if backoff := os.getenv(f"{env_prefix}RETRY_BACKOFF_MS"):
                config_data["retry_backoff_ms"] = int(backoff)
            if retries := os.getenv(f"{env_prefix}MAX_RETRIES"):
                config_data["max_retries"] = int(retries)
        except ValueError as e:
            raise ValueError(f"Invalid integer value in environment variables: {e}")

        # Remove None values
        config_data = {k: v for k, v in config_data.items() if v is not None}

        return cls(**config_data)

    # === Factory Methods ===

    @classmethod
    def create_plaintext(
        cls, bootstrap_servers: str = "localhost:9092"
    ) -> "ModelKafkaSecureConfig":
        """Create basic plaintext configuration for development."""
        return cls(bootstrap_servers=bootstrap_servers, security_protocol="PLAINTEXT")

    @classmethod
    def create_sasl_ssl(
        cls,
        bootstrap_servers: str,
        username: str,
        password: str,
        sasl_mechanism: str = "SCRAM-SHA-256",
    ) -> "ModelKafkaSecureConfig":
        """Create production-ready SASL_SSL configuration."""
        return cls(
            bootstrap_servers=bootstrap_servers,
            security_protocol="SASL_SSL",
            sasl_mechanism=sasl_mechanism,
            sasl_username=username,
            sasl_password=SecretStr(password),
            ssl_check_hostname=True,
            ssl_verify_mode="required",
        )

    @classmethod
    def create_ssl_mutual_auth(
        cls,
        bootstrap_servers: str,
        keyfile_path: str,
        certfile_path: str,
        cafile_path: str,
        keyfile_password: Optional[str] = None,
    ) -> "ModelKafkaSecureConfig":
        """Create SSL mutual authentication configuration."""
        config_data = {
            "bootstrap_servers": bootstrap_servers,
            "security_protocol": "SSL",
            "ssl_keyfile_path": keyfile_path,
            "ssl_certfile_path": certfile_path,
            "ssl_cafile_path": cafile_path,
            "ssl_check_hostname": True,
            "ssl_verify_mode": "required",
        }

        if keyfile_password:
            config_data["ssl_keyfile_password"] = SecretStr(keyfile_password)

        return cls(**config_data)
