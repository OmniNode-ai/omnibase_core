# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""``onex --help`` does not import an extension to print its help line (OMN-26615).

An extension package declares its command's one-line help in a second entry-point
group, ``onex.cli.help`` (entry name = command name, value = the help text), so the
page reads package metadata and imports nothing.

Failure modes pinned here (enumerated before the fix was written):
  help_imports_every_extension
      Rendering the command list called ``get_command`` for every extension, which
      imports the module behind it (omnibase_infra, omnimarket: seconds) just to
      read one help line.
  help_text_changes
      Serving a line from metadata must print exactly what the loading path
      prints, at every terminal width.
  command_no_longer_runs
      The stand-in used for the page must not replace the real command: running it
      still imports the real module and runs it.
  no_metadata_breaks
      An extension that declares no help entry still loads and prints as before.
  entry_for_an_unknown_command
      A help entry that names no registered extension is ignored.
  slow_without_a_terminal
      Without a terminal the entry point prints the page in under 1 s (median of
      five) while an extension import costs 1.5 s.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import statistics
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import (
    _CLI_EXTENSION_GROUP,
    _LazyCoreCommandGroup,
    register_lazy_cli_extensions,
)

pytestmark = pytest.mark.unit

SWITCH = "ONEX_CLI_SHOW_ALL_COMMANDS"
MODULE = "omn26615_ext"
HELP_GROUP = "onex.cli.help"
WITH_HELP = "omn26615-ext"
WITHOUT_HELP = "omn26615-plain"
LONG_HELP = (
    "Serve this install's projection exposures to the local runtime and print what "
    "it found. A second sentence that only the wide terminals can show."
)
PLAIN_HELP = "A command whose package declares no help entry."
HIDDEN = "omn26615-hidden"
DEPRECATED = "omn26615-old"

SLEEP_FILE = "omn26615_sleep.txt"

_SOURCE = f"""\
import time
from pathlib import Path

import click

_sleep = Path(__file__).with_name("{SLEEP_FILE}")
time.sleep(float(_sleep.read_text()) if _sleep.exists() else 0.0)


@click.command(name="{WITH_HELP}", help={LONG_HELP!r})
def cmd() -> None:
    click.echo("ran-with-help")
"""

_PLAIN_SOURCE = f"""\
import click


@click.command(name="{WITHOUT_HELP}", help={PLAIN_HELP!r})
def plain_cmd() -> None:
    click.echo("ran-plain")


@click.command(name="{HIDDEN}", help="A hidden command.", hidden=True)
def hidden_cmd() -> None:
    click.echo("ran-hidden")


@click.command(name="{DEPRECATED}", help="An old command.", deprecated=True)
def old_cmd() -> None:
    click.echo("ran-old")
"""


def _make_dist(root: Path, *, declare_help: bool, extra_help: str = "") -> None:
    (root / f"{MODULE}.py").write_text(_SOURCE, encoding="utf-8")
    (root / f"{MODULE}_plain.py").write_text(_PLAIN_SOURCE, encoding="utf-8")
    info = root / f"{MODULE}-1.0.dist-info"
    info.mkdir(exist_ok=True)
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {MODULE}\nVersion: 1.0\n", encoding="utf-8"
    )
    lines = [
        f"[{_CLI_EXTENSION_GROUP}]",
        f"{WITH_HELP} = {MODULE}:cmd",
        f"{WITHOUT_HELP} = {MODULE}_plain:plain_cmd",
        f"{HIDDEN} = {MODULE}_plain:hidden_cmd",
        f"{DEPRECATED} = {MODULE}_plain:old_cmd",
    ]
    if declare_help:
        lines += [f"[{HELP_GROUP}]", f"{WITH_HELP} = {LONG_HELP}"]
        if extra_help:
            lines.append(extra_help)
    (info / "entry_points.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def ext(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "site"
    root.mkdir()
    _make_dist(root, declare_help=True)
    monkeypatch.syspath_prepend(str(root))
    monkeypatch.setenv(SWITCH, "1")
    importlib.invalidate_caches()
    sys.modules.pop(MODULE, None)
    yield root
    sys.modules.pop(MODULE, None)


def _group() -> _LazyCoreCommandGroup:
    group = _LazyCoreCommandGroup(name="onex", help="root")
    eps = [
        e
        for e in importlib.metadata.entry_points(group=_CLI_EXTENSION_GROUP)
        if e.name.startswith("omn26615")
    ]
    assert eps, "the fixture distribution was not found"
    register_lazy_cli_extensions(group, eps)
    return group


def _render(width: int = 80) -> str:
    result = CliRunner().invoke(_group(), ["--help"], terminal_width=width)
    assert result.exit_code == 0, result.output
    return result.output


def test_help_page_does_not_import_a_declared_extension(ext: Path) -> None:
    page = _render()
    assert WITH_HELP in page
    assert MODULE not in sys.modules, (
        "--help imported the extension module only to read its help line"
    )


@pytest.mark.parametrize("width", [40, 60, 80, 120])
def test_page_text_is_identical_to_the_loading_path(ext: Path, width: int) -> None:
    served = _render(width)
    assert MODULE not in sys.modules
    _make_dist(ext, declare_help=False)
    importlib.invalidate_caches()
    loaded = _render(width)
    assert MODULE in sys.modules, "without metadata the page must load the module"
    assert served == loaded


def test_a_command_with_no_help_entry_still_loads_and_prints(ext: Path) -> None:
    page = _render()
    assert WITHOUT_HELP in page
    assert PLAIN_HELP.split(".")[0] in page


def test_hidden_and_deprecated_commands_keep_their_flags_beside_a_declared_one(
    ext: Path,
) -> None:
    """A package declares no entry for a hidden or deprecated command (its own
    drift test enforces that), so the page still hides one and labels the other,
    while the declared neighbour is served from metadata."""
    page = _render()
    assert HIDDEN not in page
    assert DEPRECATED in page
    assert "DEPRECATED" in page
    assert MODULE not in sys.modules


def test_the_real_command_still_runs_after_the_page(ext: Path) -> None:
    group = _group()
    CliRunner().invoke(group, ["--help"], terminal_width=80)
    assert MODULE not in sys.modules
    result = CliRunner().invoke(group, [WITH_HELP])
    assert result.exit_code == 0, result.output
    assert "ran-with-help" in result.output
    assert MODULE in sys.modules


def test_a_help_entry_for_an_unregistered_command_is_ignored(ext: Path) -> None:
    _make_dist(ext, declare_help=True, extra_help="omn26615-ghost = Not a command.")
    importlib.invalidate_caches()
    page = _render()
    assert "omn26615-ghost" not in page


def _timed_help(site: Path, monkeypatch: pytest.MonkeyPatch) -> float:
    (site / SLEEP_FILE).write_text("1.5", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(site), *sys.path]))
    started = time.perf_counter()
    done = subprocess.run(
        [sys.executable, "-m", "omnibase_core.cli.cli_commands", "--help"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    assert done.returncode == 0, done.stderr.decode()
    assert WITH_HELP.encode() in done.stdout
    return elapsed


def test_without_a_terminal_help_is_under_one_second(
    ext: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The extension's 1.5 s import is not paid on the help page.

    The page time is compared with the same command run with no help entry,
    measured back to back on the same machine. A fixed 1.0 s bound failed on a
    two-core CI runner under ``-n 4`` (median 1.07 s, and 1.64 s with the
    process pinned to two cores) because interpreter start-up alone then costs
    more than that; the 1.5 s the extension adds does not depend on the load.
    """
    with_entry = statistics.median(_timed_help(ext, monkeypatch) for _ in range(5))
    _make_dist(ext, declare_help=False)
    without_entry = statistics.median(_timed_help(ext, monkeypatch) for _ in range(3))
    assert with_entry < without_entry - 1.0, (
        f"with a help entry {with_entry:.2f}s, without {without_entry:.2f}s"
    )


def test_the_harness_measures_the_import_cost(
    ext: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Positive control: with no help entry the 1.5 s import shows in the timing."""
    _make_dist(ext, declare_help=False)
    assert _timed_help(ext, monkeypatch) >= 1.5
