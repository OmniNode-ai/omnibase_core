# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex refresh-credentials`` — re-pull secrets from AWS Secrets Manager."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml


def _config_path() -> Path:
    return Path.home() / ".onex" / "config.yaml"


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
    config_file = _config_path()

    if not config_file.exists():
        click.echo(
            f"Error: config file not found at {config_file}. "
            "Run 'onex config init' first.",
            err=True,
        )
        sys.exit(1)

    with open(config_file) as f:
        config = yaml.safe_load(
            f
        )  # yaml-ok: user config file, no internal Pydantic model for free-form AWS config

    if not config or "aws" not in config:
        click.echo(
            "Error: no 'aws' section in config. "
            "Add aws.secret_name and aws.region to your config.",
            err=True,
        )
        sys.exit(1)

    aws_config = config["aws"]
    secret_name = aws_config.get("secret_name")
    region = aws_config.get("region", "us-east-1")

    if not secret_name:
        click.echo("Error: aws.secret_name not set in config", err=True)
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
            section = config
            for part in config_path[:-1]:
                section = section.setdefault(part, {})
            section[config_path[-1]] = secrets[secret_key]
            updated_keys.append(secret_key)

    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    if updated_keys:
        click.echo(f"Credentials updated: {', '.join(updated_keys)}")
    else:
        click.echo("No matching credential keys found in secret")
