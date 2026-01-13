import os
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ModelEventBusConfig(BaseModel):
    """
    Configuration model for event bus nodes.
    Defines all required connection, topic, and security options for ONEX event bus nodes.
    Sensitive fields (e.g., sasl_password, ssl_keyfile) should be injected via environment variables or a secrets manager, not hardcoded in config files or code.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    bootstrap_servers: list[str] = Field(
        default=..., description="List of event bus bootstrap servers (host:port)"
    )
    topics: list[str] = Field(
        default=..., description="List of topics to use for event bus communication"
    )
    security_protocol: str | None = Field(
        default=None,
        description="Security protocol (e.g., PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL)",
    )
    sasl_mechanism: str | None = Field(
        default=None,
        description="SASL mechanism if using SASL authentication (e.g., PLAIN, SCRAM-SHA-256)",
    )
    sasl_username: str | None = Field(
        default=None, description="SASL username for authentication"
    )
    sasl_password: SecretStr | None = Field(
        default=None,
        description="SASL password for authentication (automatically masked for security)",
    )
    client_id: UUID | None = Field(
        default=None, description="Client ID for diagnostics"
    )
    group_id: UUID | None = Field(default=None, description="Consumer group ID")
    partitions: int | None = Field(
        default=None,
        description="Number of partitions for topic creation (if applicable)",
    )
    replication_factor: int | None = Field(
        default=None,
        description="Replication factor for topic creation (if applicable)",
    )
    acks: str | None = Field(
        default="all",
        description="Producer acknowledgment policy (e.g., 'all', '1', '0')",
    )
    enable_auto_commit: bool | None = Field(
        default=True, description="Enable auto-commit for consumer"
    )
    auto_offset_reset: str | None = Field(
        default="earliest", description="Offset reset policy (earliest/latest)"
    )
    ssl_cafile: str | None = Field(
        default=None, description="Path to CA file for TLS (if using SSL/SASL_SSL)"
    )
    ssl_certfile: str | None = Field(
        default=None,
        description="Path to client certificate file for TLS (if using SSL/SASL_SSL)",
    )
    ssl_keyfile: str | None = Field(
        default=None,
        description="Path to client key file for TLS (if using SSL/SASL_SSL)",
    )

    def get_sasl_password_value(self) -> str | None:
        """Safely get the SASL password value for use in authentication."""
        if self.sasl_password is None:
            return None
        return self.sasl_password.get_secret_value()

    def apply_environment_overrides(self) -> "ModelEventBusConfig":
        """Apply environment variable overrides for CI/local testing."""
        overrides: dict[
            str,
            list[str] | str | int | bool | SecretStr | None,
        ] = {}
        env_mappings = {
            "ONEX_EVENT_BUS_BOOTSTRAP_SERVERS": "bootstrap_servers",
            "ONEX_EVENT_BUS_TOPICS": "topics",
            "ONEX_EVENT_BUS_SECURITY_PROTOCOL": "security_protocol",
            "ONEX_EVENT_BUS_SASL_MECHANISM": "sasl_mechanism",
            "ONEX_EVENT_BUS_SASL_USERNAME": "sasl_username",
            "ONEX_EVENT_BUS_SASL_PASSWORD": "sasl_password",
            "ONEX_EVENT_BUS_CLIENT_ID": "client_id",
            "ONEX_EVENT_BUS_GROUP_ID": "group_id",
            "ONEX_EVENT_BUS_PARTITIONS": "partitions",
            "ONEX_EVENT_BUS_REPLICATION_FACTOR": "replication_factor",
            "ONEX_EVENT_BUS_ACKS": "acks",
            "ONEX_EVENT_BUS_ENABLE_AUTO_COMMIT": "enable_auto_commit",
            "ONEX_EVENT_BUS_AUTO_OFFSET_RESET": "auto_offset_reset",
            "ONEX_EVENT_BUS_SSL_CAFILE": "ssl_cafile",
            "ONEX_EVENT_BUS_SSL_CERTFILE": "ssl_certfile",
            "ONEX_EVENT_BUS_SSL_KEYFILE": "ssl_keyfile",
        }
        for env_var, field_name in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                if field_name in ["bootstrap_servers", "topics"]:
                    overrides[field_name] = [
                        item.strip() for item in env_value.split(",")
                    ]
                elif field_name in ["partitions", "replication_factor"]:
                    try:
                        overrides[field_name] = int(env_value)
                    except ValueError:
                        continue
                elif field_name == "enable_auto_commit":
                    overrides[field_name] = env_value.lower() in (
                        "true",
                        "1",
                        "yes",
                        "on",
                    )
                elif field_name == "sasl_password":
                    overrides[field_name] = SecretStr(env_value)
                else:
                    overrides[field_name] = env_value
        if overrides:
            current_data = self.model_dump()
            current_data.update(overrides)
            return ModelEventBusConfig(**current_data)
        return self

    @classmethod
    def default(cls) -> "ModelEventBusConfig":
        """
        Returns a canonical default config for development, testing, and CLI fallback use.
        Applies environment variable overrides for CI/local testing.
        """
        base_config = cls(
            bootstrap_servers=["localhost:9092"],
            topics=["onex-default"],
            group_id=uuid4(),
            security_protocol="PLAINTEXT",
        )
        return base_config.apply_environment_overrides()
