# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex refresh-credentials`` — re-pull secrets from AWS Secrets Manager."""

from __future__ import annotations

import json
import sys

import click

from omnibase_core.cli.cli_user_config import (
    normalize_user_config,
    read_user_config,
    user_config_path,
    write_user_config,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


def _fetch_aws_secrets(secret_name: str, region: str) -> dict[str, str]:
    """Fetch secrets from AWS Secrets Manager.

    Returns a dict of key-value pairs from the secret.
    """
    try:
        import boto3
    except ImportError as exc:
        raise ImportError(  # error-ok: CLI boundary — propagates boto3 absence as user-facing install hint
            "boto3 is required for credential refresh. Install with: pip install boto3"
        ) from exc

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return dict(json.loads(response["SecretString"]))


@click.command("refresh-credentials")
def refresh_credentials() -> None:
    """Re-pull credentials from AWS Secrets Manager and update config.

    Reads the aws.secret_name and aws.region from ~/.onex/config.yaml,
    fetches the secret from AWS Secrets Manager, and updates the config
    file with the retrieved values.
    """
    config_file = user_config_path()

    if not config_file.exists():
        click.echo(
            f"Error: config file not found at {config_file}. "
            "Run 'onex config init' first.",
            err=True,
        )
        sys.exit(1)

    try:
        config = read_user_config(config_file)
    except ModelOnexError as exc:
        # boundary-ok: CLI surface — report an unreadable config, do not rewrite it.
        click.echo(f"Error: {config_file} is not readable: {exc}", err=True)
        sys.exit(1)

    if not config or "aws" not in config:
        click.echo(
            "Error: no 'aws' section in config. "
            "Add aws.secret_name and aws.region to your config.",
            err=True,
        )
        sys.exit(1)

    aws_config = config["aws"]
    if not isinstance(aws_config, dict):
        click.echo("Error: 'aws' section must be a mapping in config", err=True)
        sys.exit(1)

    secret_name = aws_config.get("secret_name")
    region = aws_config.get("region", "us-east-1")

    if not secret_name or not isinstance(secret_name, str):
        click.echo("Error: aws.secret_name not set in config", err=True)
        sys.exit(1)
    if not isinstance(region, str):
        click.echo("Error: aws.region must be a string in config", err=True)
        sys.exit(1)

    try:
        secrets = _fetch_aws_secrets(secret_name, region)
    except (ImportError, Exception) as exc:  # noqa: BLE001  # catch-all-ok: CLI boundary, user-facing error
        click.echo(f"Error fetching secrets: {exc}", err=True)
        sys.exit(1)

    key_map = {
        "kafka_bootstrap_servers": ("kafka", "bootstrap_servers"),
    }

    updated_keys = []
    for secret_key, config_path in key_map.items():
        if secret_key in secrets:
            section: SerializedDict = config
            for part in config_path[:-1]:
                nested = section.setdefault(part, {})
                if not isinstance(nested, dict):
                    click.echo(
                        f"Error: '{part}' section must be a mapping in config", err=True
                    )
                    sys.exit(1)
                section = nested
            section[config_path[-1]] = secrets[secret_key]
            updated_keys.append(secret_key)

    # Normalize on write so a refresh against a legacy file lands on the current
    # schema instead of re-persisting the old shape (OMN-16037). The `aws:`
    # section is unmanaged and is preserved verbatim by the merge.
    try:
        normalized, _ = normalize_user_config(config)
    except ModelOnexError as exc:
        # boundary-ok: CLI surface — refuse to rewrite a file we cannot parse.
        click.echo(f"Error: {config_file} cannot be migrated: {exc}", err=True)
        sys.exit(1)

    write_user_config(config_file, normalized)

    if updated_keys:
        click.echo(f"Credentials updated: {', '.join(updated_keys)}")
    else:
        click.echo("No matching credential keys found in secret")
