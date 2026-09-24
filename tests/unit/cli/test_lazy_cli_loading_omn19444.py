# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-19444: onex delegate --help returns fast because subcommands load lazily.

AC1: onex delegate --help on a clean install returns in under 1 second.
AC2: importing the delegate subcommand does not import omnibase_infra.gateway,
qdrant_client or fastapi.

omnibase_core never depends on omnibase_infra (repo layering, CLAUDE.md rule
7), so the ``delegate``/``kafka`` onex.cli entry points cannot exist inside
this repo's own test venv -- they only exist once omnibase_infra is
co-installed (the "dispatch venv"). These tests instead pin the two
in-repo, testable mechanisms the fix actually delivers:

1. Every BUILT-IN core command (doctor, compliance, contract, ...) imports
   its own module lazily, on first ``get_command`` resolution, instead of
   eagerly at ``cli_commands`` import time -- verified by asserting
   ``importlib.import_module`` is not called for any of them during
   ``list_commands`` and is called with the right target during
   ``get_command``.
2. ``validate()`` is the only consumer of ``emit_log_event_sync``
   (``omnibase_core.logging.logging_structured``), and that import is no
   longer a module-level import of ``cli_commands`` -- verified via AST, so
   the assertion survives refactors that reorder the file.

The onex.cli EXTENSION loader (``load_cli_extensions``, OMN-16967) is
deliberately untouched by this ticket: its eager, fail-loud-at-import-time
contract is a dated, ticketed operator ruling, pinned by
``tests/unit/cli/test_cli_extension_loader_fail_loud_omn16967.py``, and nothing
here weakens it.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from unittest.mock import patch

import click
import pytest

from omnibase_core.cli.cli_commands import _LAZY_BUILTIN_COMMANDS, cli

pytestmark = pytest.mark.unit

_CLI_COMMANDS_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "omnibase_core"
    / "cli"
    / "cli_commands.py"
)


def test_every_registered_onex_command_has_a_lazy_builtin_entry() -> None:
    """The lazy table is non-trivial and covers the documented CLI surface.

    A regression that silently reverted to eager imports (by re-adding a
    module-level ``from omnibase_core.cli.cli_X import Y`` and
    ``cli.add_command(Y)``) would leave this table empty or stale; pin a
    lower bound so that regression cannot pass silently.
    """
    assert len(_LAZY_BUILTIN_COMMANDS) >= 18
    for name, (module_path, attr_name) in _LAZY_BUILTIN_COMMANDS.items():
        assert module_path.startswith("omnibase_core.cli.")
        assert attr_name
        assert name


def test_list_commands_does_not_import_any_lazy_builtin() -> None:
    """Rendering the command listing (e.g. root --help) must not import them."""
    ctx = click.Context(cli)
    with patch("importlib.import_module", wraps=importlib.import_module) as mock:
        names = cli.list_commands(ctx)
        called_modules = {c.args[0] for c in mock.call_args_list}
    for name, (module_path, _attr) in _LAZY_BUILTIN_COMMANDS.items():
        assert name in names
        assert module_path not in called_modules, (
            f"list_commands imported {module_path} eagerly for {name!r}"
        )


def test_get_command_imports_only_the_requested_builtin() -> None:
    """Resolving one command name imports only that command's own module.

    Uses a throwaway group sharing the production lazy table, rather than
    the module-level ``cli`` singleton: other tests in this suite invoke
    ``cli`` via ``CliRunner`` and permanently populate its ``commands`` cache
    for the rest of the process, which would make this assertion depend on
    test order.
    """
    from omnibase_core.cli.cli_commands import _LazyCoreCommandGroup

    probe = _LazyCoreCommandGroup(name="probe", lazy_commands=_LAZY_BUILTIN_COMMANDS)
    ctx = click.Context(probe)
    name, (module_path, attr_name) = next(iter(_LAZY_BUILTIN_COMMANDS.items()))

    with patch("importlib.import_module", wraps=importlib.import_module) as mock:
        command = probe.get_command(ctx, name)
        called_modules = [c.args[0] for c in mock.call_args_list]

    assert command is not None
    assert isinstance(command, (click.Command, click.Group))
    assert command.name == name
    assert called_modules == [module_path]

    module = importlib.import_module(module_path)
    assert getattr(module, attr_name) is command


def test_every_lazy_builtin_resolves_to_the_correctly_named_command() -> None:
    """Every table entry resolves to a real click command under its own name."""
    ctx = click.Context(cli)
    for name in _LAZY_BUILTIN_COMMANDS:
        command = cli.get_command(ctx, name)
        assert command is not None, f"{name!r} did not resolve"
        assert command.name == name


def test_unknown_command_name_returns_none_not_an_import_error() -> None:
    ctx = click.Context(cli)
    assert cli.get_command(ctx, "definitely-not-a-real-onex-command") is None


def test_importing_the_cli_entry_point_is_well_under_a_second() -> None:
    """AC1's falsifier, scoped to what omnibase_core alone can prove.

    omnibase_core never depends on omnibase_infra (repo layering), so
    ``onex delegate --help`` cannot be exercised from this repo's own venv --
    there is no ``delegate`` command here at all. This measures the timed
    quantity that IS entirely this repo's responsibility: importing the
    ``onex`` console script's own target (``omnibase_core.cli.cli_commands:cli``,
    per ``pyproject.toml``) in a cold subprocess. Before this fix that alone
    measured ~7.4s (module-level ``emit_log_event_sync`` pulling in
    ``omnibase_core.models.core``'s whole tree, 20 built-in commands eagerly
    imported, and the package ``__init__`` eagerly importing ``cli_contract``
    and ``cli_demo``); this pins a threshold loose enough not to flake on a
    slow CI runner while still catching a regression back to that order of
    magnitude.
    """
    import subprocess
    import sys
    import time

    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-c", "from omnibase_core.cli.cli_commands import cli"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    elapsed = time.monotonic() - start

    assert result.returncode == 0, result.stdout + result.stderr
    assert elapsed < 3.0, (
        f"importing omnibase_core.cli.cli_commands took {elapsed:.2f}s in a "
        "cold subprocess; expected well under 1s, budgeted to 3s for a loaded "
        "CI runner. This is the lazy-loading regression this ticket exists "
        "to catch (OMN-19444)."
    )


def test_cli_package_init_does_not_eagerly_import_contract_or_demo() -> None:
    """``omnibase_core/cli/__init__.py`` re-exports contract/demo lazily.

    Regression guard for the actual dominant cost found while building this
    fix: the package's own ``__init__.py`` used to ``from
    omnibase_core.cli.cli_contract import contract`` (and ``cli_demo``)
    eagerly. Python always runs a package's ``__init__.py`` before any of its
    submodules, so that ran on every import of ANY ``omnibase_core.cli.*``
    submodule -- including ``cli_commands``, which the ``onex`` console
    script imports directly -- independent of the lazy built-in table above.
    A subprocess is required: the heavy modules are almost certainly already
    imported by this point in the test session otherwise.
    """
    import subprocess
    import sys

    script = (
        "import sys\n"
        "from omnibase_core.cli.cli_commands import cli\n"
        "assert 'omnibase_core.cli.cli_contract' not in sys.modules, "
        "sorted(m for m in sys.modules if 'omnibase_core' in m)\n"
        "assert 'omnibase_core.cli.cli_demo' not in sys.modules\n"
        "from omnibase_core.cli import contract, demo\n"
        "import click\n"
        "assert isinstance(contract, (click.Command, click.Group))\n"
        "assert isinstance(demo, (click.Command, click.Group))\n"
        "assert 'omnibase_core.cli.cli_contract' in sys.modules\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_logging_structured_is_not_imported_at_cli_commands_module_level() -> None:
    """``emit_log_event_sync`` is validate()-only; its heavy transitive import
    (omnibase_core.models.core and everything under it) must not run merely
    from importing cli_commands."""
    tree = ast.parse(_CLI_COMMANDS_PATH.read_text())
    for node in tree.body:  # module-level statements only, not nested in defs
        if isinstance(node, ast.ImportFrom) and node.module == (
            "omnibase_core.logging.logging_structured"
        ):
            pytest.fail(
                "omnibase_core.logging.logging_structured is imported at "
                "module level in cli_commands.py; it must be a function-local "
                "import inside validate() (OMN-19444)."
            )
