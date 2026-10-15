# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-19444 AC1: ``onex delegate --help`` must not import every extension.

``onex delegate --help`` cost ~3 s on a co-installed omnibase_infra because
importing ``omnibase_core.cli.cli_commands`` loaded every ``onex.cli`` entry
point (auth, kafka, skill, ...) before click had resolved ``delegate``. The
extensions now register by NAME at import (collisions are still fatal at
import, decided from metadata alone) and load on first resolution of that
name. A malformed extension still raises, never skips: when click resolves it
by name, and when the root listing or ``--help`` renders every command.

These tests drive ``register_lazy_cli_extensions`` with synthetic entry points,
for the same reason the OMN-16967 ratchet does: a broken registration never has
to be installed to be tested.
"""

from __future__ import annotations

from importlib.metadata import EntryPoint
from typing import cast

import click
import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import (
    _LazyCoreCommandGroup,
    register_lazy_cli_extensions,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

pytestmark = pytest.mark.unit


@click.command("healthy")
def _healthy() -> None:
    """A well-formed extension command."""


class _StubEntryPoint:
    """An entry point whose ``load()`` is decided by the test, and counted."""

    def __init__(
        self,
        name: str,
        value: str,
        *,
        loaded: object = None,
        raises: Exception | None = None,
    ) -> None:
        self.name = name
        self.value = value
        self.dist = None
        self.load_calls = 0
        self._loaded = loaded
        self._raises = raises

    def load(self) -> object:
        self.load_calls += 1
        if self._raises is not None:
            raise self._raises
        return self._loaded


def _points(*stubs: _StubEntryPoint) -> list[EntryPoint]:
    return cast(list[EntryPoint], list(stubs))


def _root(
    lazy_commands: dict[str, tuple[str, str]] | None = None,
) -> _LazyCoreCommandGroup:
    return _LazyCoreCommandGroup(name="root", lazy_commands=lazy_commands)


def test_registration_does_not_load_any_extension() -> None:
    root = _root()
    ext_a = _StubEntryPoint("alpha", "pkg.a:grp", loaded=_healthy)
    ext_b = _StubEntryPoint("beta", "pkg.b:grp", loaded=_healthy)

    attached = register_lazy_cli_extensions(root, _points(ext_a, ext_b))

    assert attached == ["alpha", "beta"]
    assert (ext_a.load_calls, ext_b.load_calls) == (0, 0)
    assert root.list_commands(click.Context(root)) == ["alpha", "beta"]


def test_resolving_one_extension_loads_only_that_extension() -> None:
    root = _root()
    ext_a = _StubEntryPoint("alpha", "pkg.a:grp", loaded=_healthy)
    ext_b = _StubEntryPoint("beta", "pkg.b:grp", loaded=_healthy)
    register_lazy_cli_extensions(root, _points(ext_a, ext_b))

    command = root.get_command(click.Context(root), "alpha")

    assert command is _healthy
    assert (ext_a.load_calls, ext_b.load_calls) == (1, 0)

    # Cached after the first resolution, like any eagerly registered command.
    assert root.get_command(click.Context(root), "alpha") is _healthy
    assert ext_a.load_calls == 1


def test_invoking_a_subcommand_help_loads_only_that_extension() -> None:
    root = _root()
    ext_a = _StubEntryPoint("alpha", "pkg.a:grp", loaded=_healthy)
    ext_b = _StubEntryPoint("beta", "pkg.b:grp", loaded=_healthy)
    register_lazy_cli_extensions(root, _points(ext_a, ext_b))

    result = CliRunner().invoke(root, ["alpha", "--help"])

    assert result.exit_code == 0, result.output
    assert (ext_a.load_calls, ext_b.load_calls) == (1, 0)


def test_a_collision_with_an_eager_core_command_raises_without_loading() -> None:
    root = _root()

    @root.command("validate")
    def _validate() -> None:
        """A core-owned command."""

    ext = _StubEntryPoint("validate", "pkg.x:grp", loaded=_healthy)

    with pytest.raises(ModelOnexError) as excinfo:
        register_lazy_cli_extensions(root, _points(ext))

    assert excinfo.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
    assert ext.load_calls == 0


def test_a_collision_with_a_lazy_builtin_raises_without_loading() -> None:
    root = _root({"doctor": ("omnibase_core.cli.cli_doctor", "doctor")})
    ext = _StubEntryPoint("doctor", "pkg.x:grp", loaded=_healthy)

    with pytest.raises(ModelOnexError) as excinfo:
        register_lazy_cli_extensions(root, _points(ext))

    assert excinfo.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
    assert ext.load_calls == 0


def test_two_extensions_claiming_one_name_raise_without_loading() -> None:
    root = _root()
    first = _StubEntryPoint("cloud", "pkg.a:grp", loaded=_healthy)
    second = _StubEntryPoint("cloud", "pkg.b:grp", loaded=_healthy)

    with pytest.raises(ModelOnexError) as excinfo:
        register_lazy_cli_extensions(root, _points(first, second))

    assert excinfo.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
    assert "cloud" in str(excinfo.value)
    assert (first.load_calls, second.load_calls) == (0, 0)


def test_an_unloadable_extension_raises_when_resolved_not_skipped() -> None:
    root = _root()
    ext = _StubEntryPoint(
        "cloud",
        "pkg.missing:grp",
        raises=ModuleNotFoundError("No module named 'pkg.missing'"),
    )
    register_lazy_cli_extensions(root, _points(ext))

    with pytest.raises(ModelOnexError) as excinfo:
        root.get_command(click.Context(root), "cloud")

    assert excinfo.value.error_code == EnumCoreErrorCode.IMPORT_ERROR
    assert "pkg.missing:grp" in str(excinfo.value)


def test_a_non_click_extension_raises_when_resolved() -> None:
    root = _root()
    ext = _StubEntryPoint("cloud", "pkg.mod:thing", loaded="not a click command")
    register_lazy_cli_extensions(root, _points(ext))

    with pytest.raises(ModelOnexError) as excinfo:
        root.get_command(click.Context(root), "cloud")

    assert excinfo.value.error_code == EnumCoreErrorCode.REGISTRY_VALIDATION_FAILED


def test_root_help_surfaces_a_broken_extension_instead_of_hiding_it() -> None:
    """Rendering the full command listing resolves every extension, loudly."""
    root = _root()
    broken = _StubEntryPoint(
        "cloud", "pkg.missing:grp", raises=ModuleNotFoundError("pkg.missing")
    )
    register_lazy_cli_extensions(root, _points(broken))

    result = CliRunner().invoke(root, ["--help"])

    assert result.exit_code != 0
    assert isinstance(result.exception, ModelOnexError)
    assert broken.load_calls == 1


def test_unrelated_commands_do_not_load_extensions() -> None:
    root = _root()

    @root.command("local")
    def _local() -> None:
        """A core command."""

    ext = _StubEntryPoint("alpha", "pkg.a:grp", loaded=_healthy)
    register_lazy_cli_extensions(root, _points(ext))

    result = CliRunner().invoke(root, ["local"])

    assert result.exit_code == 0, result.output
    assert ext.load_calls == 0
