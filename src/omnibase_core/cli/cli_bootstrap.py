# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex bootstrap apply`` — read config from stdin and write to ~/.onex/config.yaml."""

from __future__ import annotations

import sys

import click

from omnibase_core.cli.cli_user_config import (
    normalize_user_config,
    parse_user_config_text,
    user_config_path,
    write_user_config,
)
from omnibase_core.errors.model_onex_error import ModelOnexError


@click.group("bootstrap")
def bootstrap() -> None:  # stub-ok
    """Bootstrap commands for ONEX standalone configuration."""


@bootstrap.command("apply")
def bootstrap_apply() -> None:
    """Read configuration from stdin and write to ~/.onex/config.yaml.

    Reads YAML content from stdin and persists it as the ONEX configuration
    file. Creates the ~/.onex/ directory if it does not exist.

    The piped content is normalized onto the current config schema before it is
    written, so piping a legacy-shaped file cannot reintroduce the schema drift
    the other writers were unified to remove (OMN-16037). Values supplied on
    stdin win; missing managed sections are filled with defaults; sections ONEX
    does not manage are preserved verbatim.

    \b
    Example:
        cat config.yaml | onex bootstrap apply
        echo "kafka:\\n  bootstrap_servers: broker:9092" | onex bootstrap apply
    """
    content = click.get_text_stream("stdin").read()

    if not content.strip():
        click.echo("Error: empty input on stdin", err=True)
        sys.exit(1)

    try:
        parsed = parse_user_config_text(content, "stdin")
        normalized, _ = normalize_user_config(parsed)
    except ModelOnexError as exc:
        # boundary-ok: CLI surface — refuse to persist an unusable config.
        click.echo(f"Error: stdin is not a usable ONEX config: {exc}", err=True)
        sys.exit(1)

    config_file = user_config_path()
    write_user_config(config_file, normalized)

    click.echo(f"Configuration written to {config_file}")
