# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex bootstrap apply`` — read config from stdin and write to ~/.onex/config.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import click


def _config_path() -> Path:
    return Path.home() / ".onex" / "config.yaml"


@click.group("bootstrap")
def bootstrap() -> None:  # stub-ok
    """Bootstrap commands for ONEX standalone configuration."""


@bootstrap.command("apply")
def bootstrap_apply() -> None:
    """Read configuration from stdin and write to ~/.onex/config.yaml.

    Reads YAML content from stdin and persists it as the ONEX configuration
    file. Creates the ~/.onex/ directory if it does not exist.

    \b
    Example:
        cat config.yaml | onex bootstrap apply
        echo "kafka:\\n  bootstrap_servers: broker:9092" | onex bootstrap apply
    """
    content = click.get_text_stream("stdin").read()

    if not content.strip():
        click.echo("Error: empty input on stdin", err=True)
        sys.exit(1)

    config_file = _config_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(content)

    click.echo(f"Configuration written to {config_file}")
