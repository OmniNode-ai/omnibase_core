# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallPolicy: every detector input and the whole set of sanctioned packages (OMN-20295)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDirectModelCallPolicy"]


class ModelDirectModelCallPolicy(BaseModel):
    """Every detector input and the whole set of sanctioned packages.

    Lives in ``policy.yaml`` inside this package, so a consumer repository
    cannot widen it: an exception is a reviewed change to omnibase_core.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Policy schema version")
    sanctioned_packages: dict[str, tuple[str, ...]] = Field(
        description=(
            "Repository name -> repository-relative globs of the sanctioned "
            "delegation node packages. A repository absent here has none."
        )
    )
    model_sdk_modules: tuple[str, ...] = Field(
        description="Top-level dotted module prefixes of model provider SDKs"
    )
    model_clis: tuple[str, ...] = Field(
        description="Program basenames that are model CLIs whatever their arguments"
    )
    print_mode_clis: tuple[str, ...] = Field(
        description="Program basenames that are model CLIs only with a print flag"
    )
    print_flags: tuple[str, ...] = Field(
        description="Flags that put a print_mode_cli into one-shot model mode"
    )
    http_clis: tuple[str, ...] = Field(
        description="Program basenames that send an HTTP request (curl, wget)"
    )
    command_wrappers: tuple[str, ...] = Field(
        description="Programs that run their first non-option argument (env, timeout)"
    )
    shells: tuple[str, ...] = Field(
        description="Programs whose -c argument is a shell command line"
    )
    python_programs: tuple[str, ...] = Field(
        description="Interpreter basenames whose script argument is executed"
    )
    http_client_modules: tuple[str, ...] = Field(
        description="Modules whose import makes a .post/.request call an HTTP send"
    )
    model_api_path_pattern: str = Field(
        description="Regex over a resolved URL text: a model API path"
    )
    provider_host_pattern: str = Field(
        description="Regex over a resolved URL text: a model provider host"
    )
    base_url_identifier_pattern: str = Field(
        description="Regex over an identifier, attribute or key naming a model base URL"
    )
    generic_base_url_identifier_pattern: str = Field(
        description=(
            "Regex over a plain base-URL identifier; a URL from one is a model "
            "call only in a file that already holds a model call"
        )
    )
    model_env_key_pattern: str = Field(
        description="Regex over an environment-variable name holding a model endpoint"
    )
    payload_keys: tuple[str, ...] = Field(
        description="A request body with any of these keys is a model request"
    )
    payload_model_companions: tuple[str, ...] = Field(
        description="A body with 'model' and any of these keys is a model request"
    )
    required_ticket_by_target: dict[str, str] = Field(
        default_factory=dict,
        description="Baseline entries for this target must name this ticket",
    )
