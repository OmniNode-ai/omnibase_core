# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""``onex hooks`` — manage ONEX_HOOKS_MASK bitmask for hook enable/disable."""

from __future__ import annotations

import difflib
import os
import tempfile
from pathlib import Path

import click

from omnibase_core.enums.enum_hook_bit import _DEFAULT_MASK, EnumHookBit

_ENV_VAR = "OMNIBASE_ENV_FILE"
_MASK_KEY = "ONEX_HOOKS_MASK"
_NAMES = {m.name.lower(): m for m in EnumHookBit}


def _env_path() -> Path:
    raw = os.environ.get(_ENV_VAR)
    if raw:
        return Path(raw)
    return Path.home() / ".omnibase" / ".env"


def _read_mask(path: Path) -> int:
    if not path.exists():
        return _DEFAULT_MASK
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(_MASK_KEY + "="):
            raw = stripped.split("=", 1)[1].strip()
            try:
                val = int(raw, 0)
                return val if val >= 0 else _DEFAULT_MASK
            except ValueError:
                return _DEFAULT_MASK
    return _DEFAULT_MASK


def _write_mask(path: Path, mask: int) -> None:
    lines: list[str]
    if path.exists():
        lines = path.read_text().splitlines()
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = []

    mask_line = f"{_MASK_KEY}=0x{mask:x}"
    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith(_MASK_KEY + "="):
            lines[i] = mask_line
            replaced = True
            break
    if not replaced:
        lines.append(mask_line)

    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".env_tmp_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(lines) + "\n")
        Path(tmp).replace(path)
    except BaseException:
        try:
            Path(tmp).unlink()
        except OSError:
            pass
        raise


def _resolve_name(name: str) -> EnumHookBit:
    lower = name.lower()
    if lower in _NAMES:
        return _NAMES[lower]
    matches = difflib.get_close_matches(lower, _NAMES.keys(), n=1, cutoff=0.6)
    hint = f" Did you mean {matches[0].upper()}?" if matches else ""
    click.echo(f"Unknown hook '{name}'.{hint}", err=True)
    raise SystemExit(2)  # error-ok: CLI usage error, exit 2 per spec


@click.group("hooks")
def hooks_group() -> None:  # stub-ok
    """Manage ONEX hook bitmask (enable/disable individual hooks)."""


@hooks_group.command("list")
def hooks_list() -> None:
    """Show every hook and its current ON/OFF state."""
    path = _env_path()
    mask = _read_mask(path)
    for m in EnumHookBit:
        state = (
            click.style("ON", fg="green")
            if (mask & int(m))
            else click.style("OFF", fg="red")
        )
        click.echo(f"  {m.name:<50s} {state}")


@hooks_group.command("mask")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["hex", "dec", "bin"]),
    default="hex",
    help="Output format (default: hex).",
)
def hooks_mask(fmt: str) -> None:
    """Print the current effective mask value."""
    path = _env_path()
    mask = _read_mask(path)
    if fmt == "hex":
        click.echo(f"0x{mask:x}")
    elif fmt == "dec":
        click.echo(str(mask))
    else:
        click.echo(f"0b{mask:b}")


@hooks_group.command("disable")
@click.argument("name")
def hooks_disable(name: str) -> None:
    """Disable a hook by clearing its bit in ONEX_HOOKS_MASK."""
    bit = _resolve_name(name)
    path = _env_path()
    mask = _read_mask(path)
    new_mask = mask & ~int(bit)
    _write_mask(path, new_mask)
    click.echo(f"onex hooks: {bit.name} disabled (mask=0x{new_mask:x})")


@hooks_group.command("enable")
@click.argument("name")
def hooks_enable(name: str) -> None:
    """Enable a hook by setting its bit in ONEX_HOOKS_MASK."""
    bit = _resolve_name(name)
    path = _env_path()
    mask = _read_mask(path)
    new_mask = mask | int(bit)
    _write_mask(path, new_mask)
    click.echo(f"onex hooks: {bit.name} enabled (mask=0x{new_mask:x})")
