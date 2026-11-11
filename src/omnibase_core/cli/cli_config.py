# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex config`` — read and initialize ~/.onex/config.yaml."""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path

import click
import yaml

from omnibase_core.cli.cli_commands import (
    _LazyCoreCommandGroup,
    register_lazy_cli_extensions,
)
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


@click.group("config", cls=_LazyCoreCommandGroup)
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
            raise click.ClickException(
                f"{config_file} already exists. Use --force to overwrite."
            )
        try:
            migrated = migrate_user_config_file(config_file)
        except ModelOnexError as exc:
            # boundary-ok: CLI surface — report the unusable file, do not rewrite it.
            raise click.ClickException(
                f"{config_file} cannot be migrated: {exc}"
            ) from exc
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
        raise click.ClickException(
            f"config file not found at {config_file}. Run 'onex config init' first."
        )

    try:
        data = read_user_config(config_file)
    except ModelOnexError as exc:
        # boundary-ok: CLI surface — report an unreadable config, do not guess.
        raise click.ClickException(f"{config_file} is not readable: {exc}") from exc

    if data is None:
        raise click.ClickException("config file is empty")

    value: SerializableValue = data
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise click.ClickException(f"key '{key}' not found in config")
        value = value[part]

    if isinstance(value, dict):
        click.echo(yaml.dump(value, default_flow_style=False).rstrip())
    else:
        click.echo(str(value))


# Config remains owned by core. Installed capability packages contribute named
# subcommands through the same lazy, collision-refusing registry as onex.cli.
register_lazy_cli_extensions(config_group, entry_points(group="onex.config"))
