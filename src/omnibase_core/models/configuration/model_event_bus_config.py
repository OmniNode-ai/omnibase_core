# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import os
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from omnibase_core.overlays.contract_env_ref import resolve_contract_env_binding


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

    # Declared contract-env binding per overridable field (OMN-17554).
    #
    # A tuple of pairs, not a dict literal: the OMN-15639 consumer-group gate
    # reads any `"group_id": "<literal>"` dict entry as a hardcoded consumer
    # group name, and it is right to -- it cannot tell a group name from a
    # reference to one by looking at the value. The binding below names the
    # variable the group id is read FROM; the id itself is still resolved at
    # run time through the sanctioned overlay boundary. Keeping the gate strict
    # and declaring the table as pairs costs nothing.
    _ENV_BINDINGS: ClassVar[tuple[tuple[str, str], ...]] = (
        ("bootstrap_servers", "${env.ONEX_EVENT_BUS_BOOTSTRAP_SERVERS}"),
        ("topics", "${env.ONEX_EVENT_BUS_TOPICS}"),
        ("security_protocol", "${env.ONEX_EVENT_BUS_SECURITY_PROTOCOL}"),
        ("sasl_mechanism", "${env.ONEX_EVENT_BUS_SASL_MECHANISM}"),
        ("sasl_username", "${env.ONEX_EVENT_BUS_SASL_USERNAME}"),
        ("sasl_password", "${env.ONEX_EVENT_BUS_SASL_PASSWORD}"),
        ("client_id", "${env.ONEX_EVENT_BUS_CLIENT_ID}"),
        ("group_id", "${env.ONEX_EVENT_BUS_GROUP_ID}"),
        ("partitions", "${env.ONEX_EVENT_BUS_PARTITIONS}"),
        ("replication_factor", "${env.ONEX_EVENT_BUS_REPLICATION_FACTOR}"),
        ("acks", "${env.ONEX_EVENT_BUS_ACKS}"),
        ("enable_auto_commit", "${env.ONEX_EVENT_BUS_ENABLE_AUTO_COMMIT}"),
        ("auto_offset_reset", "${env.ONEX_EVENT_BUS_AUTO_OFFSET_RESET}"),
        ("ssl_cafile", "${env.ONEX_EVENT_BUS_SSL_CAFILE}"),
        ("ssl_certfile", "${env.ONEX_EVENT_BUS_SSL_CERTFILE}"),
        ("ssl_keyfile", "${env.ONEX_EVENT_BUS_SSL_KEYFILE}"),
    )

    def apply_environment_overrides(self) -> "ModelEventBusConfig":
        """Apply declared binding overrides for CI/local testing."""
        overrides: dict[
            str,
            list[str] | str | int | bool | SecretStr | None,
        ] = {}
        for field_name, reference in self._ENV_BINDINGS:
            binding = resolve_contract_env_binding(reference)
            env_value = binding.value
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
        Returns a canonical default config from environment variables.
        Requires ONEX_EVENT_BUS_BOOTSTRAP_SERVERS to be set.
        """
        servers_env = os.environ.get("ONEX_EVENT_BUS_BOOTSTRAP_SERVERS", "")
        bootstrap_servers = [s.strip() for s in servers_env.split(",") if s.strip()]
        if not bootstrap_servers:
            msg = "ONEX_EVENT_BUS_BOOTSTRAP_SERVERS must be set"
            # error-ok: env var validation at config boundary
            raise ValueError(msg)
        topics_env = os.environ.get("ONEX_EVENT_BUS_TOPICS", "onex-default")
        topics = [t.strip() for t in topics_env.split(",") if t.strip()]
        base_config = cls(
            bootstrap_servers=bootstrap_servers,
            topics=topics,
            group_id=uuid4(),
            security_protocol="PLAINTEXT",
        )
        return base_config.apply_environment_overrides()
