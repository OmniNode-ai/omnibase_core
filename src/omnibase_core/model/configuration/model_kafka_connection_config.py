import os
import re

from pydantic import BaseModel, Field, SecretStr, field_validator


class ModelKafkaConnectionConfig(BaseModel):
    """
    Enterprise-grade Kafka connection configuration with comprehensive validation,
    business logic, and environment override capabilities.

    Features:
    - Strong typing with comprehensive validation
    - Environment variable override support
    - Connection string parsing and generation
    - Security protocol validation
    - SASL/SSL configuration management
    - Health check capability assessment
    - Performance tuning recommendations
    """

    bootstrap_servers: str = Field(
        ...,
        description="Kafka bootstrap servers (comma-separated)",
        pattern=r"^[a-zA-Z0-9\-\.:,\s]+$",
        max_length=500,
    )
    topic_prefix: str | None = Field(
        None,
        description="Prefix for topic names",
        pattern=r"^[a-zA-Z0-9_\-]*$",
        max_length=50,
    )
    consumer_group: str | None = Field(
        None,
        description="Consumer group ID",
        pattern=r"^[a-zA-Z0-9_\-]*$",
        max_length=100,
    )
    timeout_ms: int = Field(
        5000,
        description="Connection timeout in milliseconds",
        ge=1000,
        le=300000,
    )
    security_protocol: str = Field(
        "PLAINTEXT",
        description="Security protocol (PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL)",
        pattern=r"^(PLAINTEXT|SSL|SASL_PLAINTEXT|SASL_SSL)$",
    )
    sasl_username: str | None = Field(
        None,
        description="SASL username for authentication",
        max_length=100,
    )
    sasl_password: SecretStr | None = Field(
        None,
        description="SASL password for authentication (secured)",
    )
    ssl_keyfile: str | None = Field(
        None,
        description="Path to SSL key file",
        max_length=500,
    )
    ssl_certfile: str | None = Field(
        None,
        description="Path to SSL certificate file",
        max_length=500,
    )
    ssl_cafile: str | None = Field(
        None,
        description="Path to SSL CA file",
        max_length=500,
    )

    @field_validator("bootstrap_servers", mode="before")
    @classmethod
    def validate_bootstrap_servers(cls, v: str) -> str:
        """Validate bootstrap servers format and reachability patterns."""
        if not v or not v.strip():
            msg = "Bootstrap servers cannot be empty"
            raise ValueError(msg)

        servers = [s.strip() for s in v.split(",")]
        validated_servers = []

        for server in servers:
            if not server:
                continue

            # Basic format validation (host:port or just host)
            if ":" in server:
                host, port_str = server.rsplit(":", 1)
                try:
                    port = int(port_str)
                    if not (1 <= port <= 65535):
                        msg = f"Invalid port number in server: {server}"
                        raise ValueError(msg)
                except ValueError:
                    msg = f"Invalid port format in server: {server}"
                    raise ValueError(msg)
            else:
                host = server

            # Host validation
            if not re.match(r"^[a-zA-Z0-9\-\.]+$", host):
                msg = f"Invalid host format in server: {server}"
                raise ValueError(msg)

            validated_servers.append(server)

        if not validated_servers:
            msg = "No valid bootstrap servers found"
            raise ValueError(msg)

        return ",".join(validated_servers)

    @field_validator("ssl_keyfile", "ssl_certfile", "ssl_cafile", mode="before")
    @classmethod
    def validate_ssl_files(cls, v: str | None) -> str | None:
        """Validate SSL file paths if provided."""
        if v is not None:
            # Basic path validation
            if not re.match(r"^[a-zA-Z0-9\-\._/\\:]+$", v):
                msg = f"Invalid SSL file path format: {v}"
                raise ValueError(msg)
        return v

    # === Connection Management ===

    def get_bootstrap_server_list(self) -> list[str]:
        """Get list of individual bootstrap servers."""
        return [s.strip() for s in self.bootstrap_servers.split(",") if s.strip()]

    def get_primary_bootstrap_server(self) -> str:
        """Get the first bootstrap server for primary connections."""
        servers = self.get_bootstrap_server_list()
        return servers[0] if servers else self.bootstrap_servers

    def get_connection_properties(self) -> dict[str, str]:
        """Get Kafka connection properties as key-value pairs."""
        props = {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "socket.connection.setup.timeout.ms": str(self.timeout_ms),
            "connections.max.idle.ms": str(
                self.timeout_ms * 6,
            ),  # 6x connection timeout
        }

        # Add consumer group if specified
        if self.consumer_group:
            props["group.id"] = self.consumer_group

        # Add SASL configuration
        if self.requires_sasl_authentication():
            if self.sasl_username:
                props["sasl.username"] = self.sasl_username
            if self.sasl_password:
                props["sasl.password"] = self.sasl_password.get_secret_value()

        # Add SSL configuration
        if self.requires_ssl():
            if self.ssl_keyfile:
                props["ssl.keystore.location"] = self.ssl_keyfile
            if self.ssl_certfile:
                props["ssl.certificate.location"] = self.ssl_certfile
            if self.ssl_cafile:
                props["ssl.ca.location"] = self.ssl_cafile

        return props

    def get_masked_connection_properties(self) -> dict[str, str]:
        """Get connection properties with sensitive values masked."""
        props = self.get_connection_properties()

        # Mask sensitive properties
        sensitive_keys = {"sasl.password", "ssl.keystore.password", "ssl.key.password"}
        for key in sensitive_keys:
            if props.get(key):
                props[key] = "***MASKED***"

        return props

    # === Security Assessment ===

    def requires_ssl(self) -> bool:
        """Check if SSL is required based on security protocol."""
        return self.security_protocol in ("SSL", "SASL_SSL")

    def requires_sasl_authentication(self) -> bool:
        """Check if SASL authentication is required."""
        return self.security_protocol in ("SASL_PLAINTEXT", "SASL_SSL")

    def is_secure_configuration(self) -> bool:
        """Assess if this is a secure configuration for production."""
        if self.security_protocol == "PLAINTEXT":
            return False  # Not secure for production

        if self.requires_sasl_authentication():
            if not self.sasl_username or not self.sasl_password:
                return False  # Missing SASL credentials

        if self.requires_ssl():
            # Basic SSL file presence check
            ssl_files_present = any(
                [self.ssl_keyfile, self.ssl_certfile, self.ssl_cafile],
            )
            if not ssl_files_present:
                return False  # SSL required but no files configured

        return True

    def get_security_recommendations(self) -> list[str]:
        """Get security recommendations for this configuration."""
        recommendations = []

        if self.security_protocol == "PLAINTEXT":
            recommendations.append(
                "Consider using SSL or SASL for production environments",
            )

        if self.requires_sasl_authentication() and not self.sasl_username:
            recommendations.append(
                "SASL username should be configured for authentication",
            )

        if self.requires_sasl_authentication() and not self.sasl_password:
            recommendations.append(
                "SASL password should be configured for authentication",
            )

        if self.requires_ssl() and not any(
            [self.ssl_keyfile, self.ssl_certfile, self.ssl_cafile],
        ):
            recommendations.append(
                "SSL files should be configured when using SSL security protocol",
            )

        if self.timeout_ms < 10000:
            recommendations.append(
                "Consider increasing timeout for production stability",
            )

        return recommendations

    # === Performance Assessment ===

    def get_performance_profile(self) -> dict[str, str]:
        """Get performance characteristics of this configuration."""
        profile = {
            "latency_profile": "low" if self.timeout_ms <= 5000 else "high",
            "security_overhead": (
                "none" if self.security_protocol == "PLAINTEXT" else "moderate"
            ),
            "connection_efficiency": (
                "high" if len(self.get_bootstrap_server_list()) > 1 else "moderate"
            ),
        }

        # Assess SSL overhead
        if self.requires_ssl():
            profile["ssl_overhead"] = "present"
        else:
            profile["ssl_overhead"] = "none"

        return profile

    def get_performance_recommendations(self) -> list[str]:
        """Get performance tuning recommendations."""
        recommendations = []

        servers = self.get_bootstrap_server_list()
        if len(servers) == 1:
            recommendations.append(
                "Consider configuring multiple bootstrap servers for redundancy",
            )

        if self.timeout_ms > 30000:
            recommendations.append(
                "High timeout may impact responsiveness - consider reducing",
            )

        if self.requires_ssl() and self.timeout_ms < 10000:
            recommendations.append(
                "SSL configurations may need higher timeouts for stability",
            )

        return recommendations

    # === Topic Management ===

    def get_effective_topic_name(self, base_topic: str) -> str:
        """Get the effective topic name with prefix applied."""
        if self.topic_prefix:
            return f"{self.topic_prefix}.{base_topic}"
        return base_topic

    def parse_topic_name(self, full_topic: str) -> tuple[str | None, str]:
        """Parse a full topic name to extract prefix and base name."""
        if self.topic_prefix and full_topic.startswith(f"{self.topic_prefix}."):
            base_topic = full_topic[len(self.topic_prefix) + 1 :]
            return self.topic_prefix, base_topic
        return None, full_topic

    # === Environment Override Support ===

    def apply_environment_overrides(self) -> "ModelKafkaConnectionConfig":
        """Apply environment variable overrides for CI/local testing."""
        overrides = {}

        # Environment variable mappings
        env_mappings = {
            "ONEX_KAFKA_BOOTSTRAP_SERVERS": "bootstrap_servers",
            "ONEX_KAFKA_SECURITY_PROTOCOL": "security_protocol",
            "ONEX_KAFKA_SASL_USERNAME": "sasl_username",
            "ONEX_KAFKA_SASL_PASSWORD": "sasl_password",
            "ONEX_KAFKA_SSL_KEYFILE": "ssl_keyfile",
            "ONEX_KAFKA_SSL_CERTFILE": "ssl_certfile",
            "ONEX_KAFKA_SSL_CAFILE": "ssl_cafile",
            "ONEX_KAFKA_TIMEOUT_MS": "timeout_ms",
            "ONEX_KAFKA_TOPIC_PREFIX": "topic_prefix",
            "ONEX_KAFKA_CONSUMER_GROUP": "consumer_group",
        }

        for env_var, field_name in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Type conversion for numeric fields
                if field_name == "timeout_ms":
                    try:
                        overrides[field_name] = int(env_value)
                    except ValueError:
                        continue  # Skip invalid values
                elif field_name == "sasl_password":
                    overrides[field_name] = SecretStr(env_value)
                else:
                    overrides[field_name] = env_value

        if overrides:
            # Create new instance with overrides
            current_data = self.model_dump()
            current_data.update(overrides)
            return ModelKafkaConnectionConfig(**current_data)

        return self

    # === Health Check Support ===

    def can_perform_health_check(self) -> bool:
        """Check if health check can be performed with this configuration."""
        # Basic requirement: at least one bootstrap server
        return bool(self.get_bootstrap_server_list())

    def get_health_check_timeout_ms(self) -> int:
        """Get recommended timeout for health check operations."""
        # Health checks should be faster than normal operations
        return min(self.timeout_ms, 5000)

    # === Factory Methods ===

    @classmethod
    def create_local_development(cls, port: int = 9092) -> "ModelKafkaConnectionConfig":
        """Create configuration for local development."""
        return cls(
            bootstrap_servers=f"localhost:{port}",
            security_protocol="PLAINTEXT",
            timeout_ms=5000,
            consumer_group="onex-dev",
        )

    @classmethod
    def create_production_ssl(
        cls,
        servers: str,
        ssl_keyfile: str,
        ssl_certfile: str,
        ssl_cafile: str,
        consumer_group: str = "onex-prod",
    ) -> "ModelKafkaConnectionConfig":
        """Create secure production configuration with SSL."""
        return cls(
            bootstrap_servers=servers,
            security_protocol="SSL",
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            ssl_cafile=ssl_cafile,
            timeout_ms=15000,  # Higher timeout for production
            consumer_group=consumer_group,
        )

    @classmethod
    def create_sasl_ssl(
        cls,
        servers: str,
        username: str,
        password: str,
        ssl_cafile: str,
        consumer_group: str = "onex-sasl",
    ) -> "ModelKafkaConnectionConfig":
        """Create SASL+SSL configuration for enterprise authentication."""
        return cls(
            bootstrap_servers=servers,
            security_protocol="SASL_SSL",
            sasl_username=username,
            sasl_password=SecretStr(password),
            ssl_cafile=ssl_cafile,
            timeout_ms=20000,  # Higher timeout for SASL+SSL
            consumer_group=consumer_group,
        )
