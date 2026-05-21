# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strongly typed operational configuration for contract config blocks (OMN-11430)."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ModelOperationalConfig(BaseModel):
    """Operational configuration: credentials and integration keys."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    linear_api_key: SecretStr | None = Field(default=None, description="Linear API key")
    # string-id-ok: Linear team IDs are string slugs (e.g. 'OmniNode'), not UUIDs
    linear_team_id: str | None = Field(
        default=None, description="Linear team ID (string slug, e.g. 'OmniNode')"
    )
    github_token: SecretStr | None = Field(
        default=None, description="GitHub personal access token"
    )
    slack_webhook_url: str | None = Field(
        default=None, description="Slack incoming webhook URL"
    )
