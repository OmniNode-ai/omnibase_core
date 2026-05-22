# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strongly typed storage configuration for contract config blocks (OMN-11430)."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ModelStorageConfig(BaseModel):
    """Storage connection parameters declared in contract config."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    postgres_host: str | None = Field(default=None, description="PostgreSQL host")
    postgres_port: int | None = Field(default=None, description="PostgreSQL port")
    postgres_database: str | None = Field(
        default=None, description="PostgreSQL database name"
    )
    postgres_user: str | None = Field(default=None, description="PostgreSQL user")
    postgres_password: SecretStr | None = Field(
        default=None, description="PostgreSQL password"
    )
    kafka_bootstrap_servers: str | None = Field(
        default=None, description="Kafka bootstrap servers"
    )
    redpanda_admin_host: str | None = Field(
        default=None, description="Redpanda admin host"
    )
    redpanda_admin_port: int | None = Field(
        default=None, description="Redpanda admin port"
    )
