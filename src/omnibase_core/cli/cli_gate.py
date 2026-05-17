# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Thin OmniGate CLI surface owned by omnibase_core."""

from __future__ import annotations

import importlib
import inspect
import json
import subprocess
from pathlib import Path

import click
import yaml
from pydantic import ValidationError

from omnibase_core.gate import (
    compute_config_hash,
    compute_pr_diff_hash,
    compute_staged_diff_hash,
    discover_omnigate_config,
    load_omnigate_config,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

_CONFIG_NAME = ".omnigate.yaml"
_HOOK_NAME = "pre-push"
_INFRA_SERVICES_MODULE = "omnibase_infra.gate.cli_services"


def _json_echo(payload: dict[str, object]) -> None:
    click.echo(json.dumps(payload, sort_keys=True))


def _click_error_from_exception(exc: Exception) -> click.ClickException:
    if isinstance(exc, ModelOnexError):
        return click.ClickException(str(exc))
    if isinstance(exc, ValidationError):
        return click.ClickException(str(exc))
    return click.ClickException(f"{type(exc).__name__}: {exc}")


def _resolve_config_path(repo: Path, config: Path | None) -> Path:
    if config is not None:
        return config

    discovered = discover_omnigate_config(repo)
    if discovered is None:
        raise click.ClickException(
            f"OmniGate config not found under {repo}. Run `onex gate install` first."
        )
    return discovered


_CLI_ERROR_TYPES = (
    ModelOnexError,
    ValidationError,
    OSError,
    ValueError,
    yaml.YAMLError,
    subprocess.CalledProcessError,
)


def _default_config(
    repo: Path,
    project_name: str | None,
    project_url: str | None,
) -> dict[str, object]:
    resolved_project_name = project_name or repo.resolve().name
    resolved_project_url = (
        project_url or f"https://github.com/example/{resolved_project_name}"
    )
    return {
        "version": {"major": 1, "minor": 0, "patch": 0},
        "project_name": resolved_project_name,
        "project_url": resolved_project_url,
        "checks": [
            {
                "name": "unit",
                "run": "pytest -q",
            }
        ],
        "gate": {
            "scope": "forks-only",
            "on_missing_receipt": "auto-close",
            "grace_period_minutes": 10,
        },
        "receipt": {
            "max_age_minutes": 120,
            "require_diff_binding": True,
            "signing": "sigstore",
            "allow_unsigned": False,
            "advisory_blocks": False,
        },
    }


def _hook_content() -> str:
    return """#!/bin/sh
# OmniGate pre-push hook. Installed by `onex gate install`.
exec onex gate run "$@"
"""


def _resolve_hooks_dir(repo: Path) -> Path:
    git_path = repo / ".git"
    if git_path.is_dir():
        return git_path / "hooks"

    if git_path.is_file():
        first_line = git_path.read_text(encoding="utf-8").splitlines()[0]
        prefix = "gitdir: "
        if first_line.startswith(prefix):
            git_dir = Path(first_line.removeprefix(prefix))
            if not git_dir.is_absolute():
                git_dir = (repo / git_dir).resolve()
            return git_dir / "hooks"

    raise click.ClickException(
        f"Git metadata not found under {repo}. Run this inside a Git repository."
    )


def _load_infra_services() -> object:
    try:
        return importlib.import_module(_INFRA_SERVICES_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name is not None and exc.name.startswith("omnibase_infra"):
            raise click.ClickException(
                "OmniGate command requires omnibase_infra. "
                "Install omnibase_infra or the omnigate distribution package."
            ) from exc
        raise
    except ImportError as exc:
        raise click.ClickException(
            f"Failed to import {_INFRA_SERVICES_MODULE}: {exc}"
        ) from exc


def _delegate_to_infra(command_name: str, args: tuple[str, ...]) -> None:
    services = _load_infra_services()
    try:
        handler = getattr(services, command_name)
    except AttributeError as exc:
        raise click.ClickException(
            f"{_INFRA_SERVICES_MODULE} does not expose `{command_name}`."
        ) from exc

    signature = inspect.signature(handler)
    if "args" in signature.parameters:
        result = handler(args=list(args))
    else:
        result = handler(*args)

    if result is not None:
        click.echo(result)


@click.group()
def gate() -> None:
    """OmniGate PR quality gate commands."""
    click.get_current_context().ensure_object(dict)


@gate.command()
@click.option(
    "--repo",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(),
    show_default=True,
    help="Repository root to scaffold.",
)
@click.option("--project-name", help="Project name for generated config.")
@click.option("--project-url", help="Project URL for generated config.")
@click.option("--force", is_flag=True, help="Overwrite existing OmniGate files.")
def install(
    repo: Path,
    project_name: str | None,
    project_url: str | None,
    *,
    force: bool,
) -> None:
    """Scaffold `.omnigate.yaml` and a pre-push hook without running checks."""
    repo = repo.resolve()
    config_path = repo / _CONFIG_NAME
    hook_path = _resolve_hooks_dir(repo) / _HOOK_NAME

    if config_path.exists() and not force:
        raise click.ClickException(f"Config already exists: {config_path}")
    if hook_path.exists() and not force:
        raise click.ClickException(f"Pre-push hook already exists: {hook_path}")

    config_data = _default_config(repo, project_name, project_url)
    config_text = yaml.safe_dump(config_data, sort_keys=False)
    from omnibase_core.gate.config_loader import from_yaml_omnigate_config

    from_yaml_omnigate_config(config_text, config_path=config_path)

    config_path.write_text(config_text, encoding="utf-8")
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(_hook_content(), encoding="utf-8")
    hook_path.chmod(0o755)

    click.echo(f"Wrote {config_path}")
    click.echo(f"Wrote {hook_path}")


@gate.command("validate-config")
@click.option(
    "--repo",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(),
    show_default=True,
    help="Repository root used for config discovery.",
)
@click.option(
    "--config",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Explicit OmniGate config path.",
)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON.")
def validate_config(repo: Path, config: Path | None, *, json_output: bool) -> None:
    """Validate an OmniGate config file against ModelOmniGateConfig."""
    try:
        config_path = _resolve_config_path(repo.resolve(), config)
        loaded = load_omnigate_config(config_path)
    except click.ClickException as exc:
        if json_output:
            _json_echo({"valid": False, "error": exc.message})
            raise click.exceptions.Exit(1)
        raise
    except _CLI_ERROR_TYPES as exc:
        if json_output:
            _json_echo({"valid": False, "error": str(exc)})
            raise click.exceptions.Exit(1)
        raise _click_error_from_exception(exc)

    payload = {
        "valid": True,
        "config_path": str(config_path),
        "project_name": loaded.project_name,
        "checks": len(loaded.checks),
        "validators": len(loaded.validators),
        "config_hash": compute_config_hash(config_path),
    }
    if json_output:
        _json_echo(payload)
        return

    click.echo(f"valid: {payload['valid']}")
    click.echo(f"config_path: {payload['config_path']}")
    click.echo(f"project_name: {payload['project_name']}")
    click.echo(f"checks: {payload['checks']}")
    click.echo(f"validators: {payload['validators']}")
    click.echo(f"config_hash: {payload['config_hash']}")


@gate.command("diff-hash")
@click.option(
    "--repo",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(),
    show_default=True,
    help="Repository root.",
)
@click.option("--base-ref", help="Base ref/SHA for PR diff hashing.")
@click.option("--head-ref", help="Head ref/SHA for PR diff hashing.")
@click.option("--allow-empty", is_flag=True, help="Allow empty diffs.")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON.")
def diff_hash(
    repo: Path,
    base_ref: str | None,
    head_ref: str | None,
    *,
    allow_empty: bool,
    json_output: bool,
) -> None:
    """Compute the deterministic OmniGate diff hash."""
    try:
        if base_ref is not None or head_ref is not None:
            if base_ref is None or head_ref is None:
                raise click.ClickException(
                    "--base-ref and --head-ref must be provided together."
                )
            diff_hash_value = compute_pr_diff_hash(
                repo.resolve(),
                base_sha=base_ref,
                head_sha=head_ref,
                allow_empty=allow_empty,
            )
            mode = "pr"
        else:
            diff_hash_value = compute_staged_diff_hash(
                repo.resolve(),
                allow_empty=allow_empty,
            )
            mode = "staged"
    except click.ClickException:
        raise
    except _CLI_ERROR_TYPES as exc:
        raise _click_error_from_exception(exc)

    if json_output:
        _json_echo({"diff_hash": diff_hash_value, "mode": mode})
        return
    click.echo(diff_hash_value)


@gate.command()
@click.option(
    "--repo",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(),
    show_default=True,
    help="Repository root used for config discovery.",
)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON.")
def status(repo: Path, *, json_output: bool) -> None:
    """Report local OmniGate config and hook status."""
    repo = repo.resolve()
    config_path = discover_omnigate_config(repo)
    hooks_dir = _resolve_hooks_dir(repo)
    hook_path = hooks_dir / _HOOK_NAME
    payload: dict[str, object] = {
        "repo": str(repo),
        "config_found": config_path is not None,
        "config_path": str(config_path) if config_path else None,
        "pre_push_hook_installed": hook_path.is_file(),
        "pre_push_hook_path": str(hook_path),
    }

    if config_path is not None:
        try:
            loaded = load_omnigate_config(config_path)
            payload.update(
                {
                    "config_valid": True,
                    "project_name": loaded.project_name,
                    "checks": len(loaded.checks),
                    "validators": len(loaded.validators),
                    "config_hash": compute_config_hash(config_path),
                }
            )
        except _CLI_ERROR_TYPES as exc:
            payload.update({"config_valid": False, "error": str(exc)})
    else:
        payload["config_valid"] = False

    if json_output:
        _json_echo(payload)
        return

    click.echo(f"repo: {payload['repo']}")
    click.echo(f"config_found: {payload['config_found']}")
    click.echo(f"config_valid: {payload['config_valid']}")
    if payload["config_path"]:
        click.echo(f"config_path: {payload['config_path']}")
    if "project_name" in payload:
        click.echo(f"project_name: {payload['project_name']}")
        click.echo(f"checks: {payload['checks']}")
        click.echo(f"validators: {payload['validators']}")
        click.echo(f"config_hash: {payload['config_hash']}")
    click.echo(f"pre_push_hook_installed: {payload['pre_push_hook_installed']}")
    click.echo(f"pre_push_hook_path: {payload['pre_push_hook_path']}")


@gate.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.pass_context
def run(ctx: click.Context) -> None:
    """Run OmniGate checks via omnibase_infra."""
    _delegate_to_infra("run", tuple(ctx.args))


@gate.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.pass_context
def sign(ctx: click.Context) -> None:
    """Sign an OmniGate receipt via omnibase_infra."""
    _delegate_to_infra("sign", tuple(ctx.args))


@gate.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.pass_context
def verify(ctx: click.Context) -> None:
    """Verify an OmniGate receipt via omnibase_infra."""
    _delegate_to_infra("verify", tuple(ctx.args))


__all__ = ["gate"]
