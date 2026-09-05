# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from omnibase_core.models.configuration.model_env_overlay_binding import (
    ModelEnvOverlayBinding,
)
from omnibase_core.overlays.contract_env_ref import resolve_overlay_binding

# Declared overlay bindings (OMN-17554).
#
# This env-var -> field table used to be a bare dict literal inside
# ``apply_environment_overrides``, read back from the process environment on
# the loop variable. A read keyed on a loop variable is dynamic: nothing can
# enumerate what this model binds, and no static gate can attribute the read to
# a name. The table is now typed and validated by ``ModelEnvOverlayBinding``,
# and every value resolves through the single sanctioned overlay authority in
# ``omnibase_core.overlays.contract_env_ref``. This model performs no
# environment read of its own.
# The two bindings ``default()`` needs by themselves. These two reads were NOT
# part of the ten dynamic reads OMN-17554 counts — they are constant-keyed and
# already on the allowlist — but leaving them as the last direct environment
# access in a module whose stated invariant is "no environment read of its own"
# would make that invariant untrue, and untestable.
_BOOTSTRAP_SERVERS_BINDING = ModelEnvOverlayBinding(
    env_var="ONEX_EVENT_BUS_BOOTSTRAP_SERVERS", field_name="bootstrap_servers"
)
_TOPICS_BINDING = ModelEnvOverlayBinding(
    env_var="ONEX_EVENT_BUS_TOPICS", field_name="topics"
)

_ENV_OVERLAY_BINDINGS: tuple[ModelEnvOverlayBinding, ...] = (
    _BOOTSTRAP_SERVERS_BINDING,
    _TOPICS_BINDING,
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_SECURITY_PROTOCOL", field_name="security_protocol"
    ),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_SASL_MECHANISM", field_name="sasl_mechanism"
    ),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_SASL_USERNAME", field_name="sasl_username"
    ),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_SASL_PASSWORD", field_name="sasl_password"
    ),
    ModelEnvOverlayBinding(env_var="ONEX_EVENT_BUS_CLIENT_ID", field_name="client_id"),
    ModelEnvOverlayBinding(env_var="ONEX_EVENT_BUS_GROUP_ID", field_name="group_id"),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_PARTITIONS", field_name="partitions"
    ),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_REPLICATION_FACTOR", field_name="replication_factor"
    ),
    ModelEnvOverlayBinding(env_var="ONEX_EVENT_BUS_ACKS", field_name="acks"),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_ENABLE_AUTO_COMMIT", field_name="enable_auto_commit"
    ),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_AUTO_OFFSET_RESET", field_name="auto_offset_reset"
    ),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_SSL_CAFILE", field_name="ssl_cafile"
    ),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_SSL_CERTFILE", field_name="ssl_certfile"
    ),
    ModelEnvOverlayBinding(
        env_var="ONEX_EVENT_BUS_SSL_KEYFILE", field_name="ssl_keyfile"
    ),
)


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
        """Apply the declared overlay bindings for CI/local testing."""
        overrides: dict[
            str,
            list[str] | str | int | bool | SecretStr | None,
        ] = {}
        for binding in _ENV_OVERLAY_BINDINGS:
            field_name = binding.field_name
            env_value = resolve_overlay_binding(binding)
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
        servers_env = resolve_overlay_binding(_BOOTSTRAP_SERVERS_BINDING) or ""
        bootstrap_servers = [s.strip() for s in servers_env.split(",") if s.strip()]
        if not bootstrap_servers:
            msg = "ONEX_EVENT_BUS_BOOTSTRAP_SERVERS must be set"
            # error-ok: env var validation at config boundary
            raise ValueError(msg)
        topics_env = resolve_overlay_binding(_TOPICS_BINDING) or "onex-default"
        topics = [t.strip() for t in topics_env.split(",") if t.strip()]
        base_config = cls(
            bootstrap_servers=bootstrap_servers,
            topics=topics,
            group_id=uuid4(),
            security_protocol="PLAINTEXT",
        )
        return base_config.apply_environment_overrides()
