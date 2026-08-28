# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex config`` — read and initialize ~/.onex/config.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

from omnibase_core.cli.cli_user_config import (
    bootstrap_user_config,
    migrate_user_config_file,
    read_user_config,
    user_config_path,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializableValue

_ONEX_HOME_OPTION = click.option(
    "--onex-home",
    "onex_home",
    type=click.Path(path_type=Path),
    default=None,
    hidden=True,
    help="Override ~/.onex location (for testing).",
)


@click.group("config")
def config_group() -> None:  # stub-ok
    """Manage ONEX configuration."""


@config_group.command("init")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Rewrite an existing config onto the current schema, keeping its values.",
)
@_ONEX_HOME_OPTION
def config_init(force: bool, onex_home: Path | None) -> None:
    """Scaffold ~/.onex/config.yaml with default placeholders.

    Creates the starter configuration file shared with ``onex init
    --user-config``. If the file already exists, --force migrates it onto the
    current schema in place: existing values, unmanaged sections and hand-added
    keys are preserved, missing sections are filled with defaults, and a legacy
    ``mode: standalone`` file is converted to ``mode: local``.
    """
    config_file = user_config_path(onex_home)

    if config_file.exists():
        if not force:
            click.echo(
                f"Error: {config_file} already exists. Use --force to overwrite.",
                err=True,
            )
            sys.exit(1)
        try:
            migrated = migrate_user_config_file(config_file)
        except ModelOnexError as exc:
            # boundary-ok: CLI surface — report the unusable file, do not rewrite it.
            click.echo(f"Error: {config_file} cannot be migrated: {exc}", err=True)
            sys.exit(1)
        if migrated:
            click.echo(f"Configuration migrated to the current schema at {config_file}")
        else:
            click.echo(f"Configuration already current at {config_file}")
        return

    bootstrap_user_config(config_file)
    click.echo(f"Configuration initialized at {config_file}")


@config_group.command("get")
@click.argument("key")
@_ONEX_HOME_OPTION
def config_get(key: str, onex_home: Path | None) -> None:
    """Read a value from ~/.onex/config.yaml.

    Supports dotted keys for nested access (e.g. kafka.bootstrap_servers).
    """
    config_file = user_config_path(onex_home)

    if not config_file.exists():
        click.echo(
            f"Error: config file not found at {config_file}. "
            "Run 'onex config init' first.",
            err=True,
        )
        sys.exit(1)

    try:
        data = read_user_config(config_file)
    except ModelOnexError as exc:
        # boundary-ok: CLI surface — report an unreadable config, do not guess.
        click.echo(f"Error: {config_file} is not readable: {exc}", err=True)
        sys.exit(1)

    if data is None:
        click.echo("Error: config file is empty", err=True)
        sys.exit(1)

    parts = key.split(".")
    value: SerializableValue = data
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            click.echo(f"Error: key '{key}' not found in config", err=True)
            sys.exit(1)
        value = value[part]

    if isinstance(value, dict):
        click.echo(yaml.dump(value, default_flow_style=False).rstrip())
    else:
        click.echo(str(value))
