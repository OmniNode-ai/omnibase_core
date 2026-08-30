# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""RATCHET — the ``onex.cli`` extension loader must fail loud (OMN-16967).

**The drift class.** The operator's diagnosis, 2026-08-29: features get built
outside entry-point registration *because nothing enforces the binding*. The
loader used to log a warning and skip on every failure mode, which made a
missing command indistinguishable from a command that was never advertised —
the CLI starts fine, the surface is simply absent, and the warning lands in a
stream nobody reads during ``pip install``.

These tests pin the three malformed shapes as fatal, and pin that the healthy
path still attaches. They drive
:func:`omnibase_core.cli.cli_commands.load_cli_extensions` with synthetic entry
points rather than installed distributions, so a broken registration never has
to be installed to be tested.
"""

from __future__ import annotations

from importlib.metadata import EntryPoint
from typing import cast

import click
import pytest

from omnibase_core.cli.cli_commands import load_cli_extensions
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

pytestmark = pytest.mark.unit


@click.group("healthy")
def _healthy_group() -> None:
    """A well-formed extension group."""


_NOT_A_COMMAND = "this string is not a click command"


class _StubEntryPoint:
    """An entry point whose ``load()`` is decided by the test, not by imports.

    A stub rather than an :class:`EntryPoint` subclass: on 3.12+ ``EntryPoint``
    is a plain class whose ``__new__`` takes no extra arguments, so subclassing
    it to inject a resolution result does not work. The loader touches exactly
    ``name``, ``value``, ``dist`` and ``load()``, all of which are provided
    here; the call sites cast, so the production signature keeps naming the real
    type.
    """

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
        self._loaded = loaded
        self._raises = raises

    def load(self) -> object:
        if self._raises is not None:
            raise self._raises
        return self._loaded


def _points(*stubs: _StubEntryPoint) -> list[EntryPoint]:
    """Present the stubs as the entry points the loader declares it takes."""
    return cast(list[EntryPoint], list(stubs))


def _root() -> click.Group:
    @click.group()
    def root() -> None:
        """A bare root CLI to attach extensions to."""

    return root


def test_a_well_formed_extension_is_attached_under_its_entry_point_name() -> None:
    root = _root()

    attached = load_cli_extensions(
        root, _points(_StubEntryPoint("cloud", "pkg.mod:grp", loaded=_healthy_group))
    )

    assert attached == ["cloud"]
    assert "cloud" in root.commands


def test_an_unloadable_target_raises_instead_of_being_skipped() -> None:
    """The command was advertised and did not arrive — that is reported, not logged."""
    root = _root()

    with pytest.raises(ModelOnexError) as excinfo:
        load_cli_extensions(
            root,
            _points(
                _StubEntryPoint(
                    "cloud",
                    "pkg.missing:grp",
                    raises=ModuleNotFoundError("No module named 'pkg.missing'"),
                )
            ),
        )

    assert excinfo.value.error_code == EnumCoreErrorCode.IMPORT_ERROR
    assert "cloud" in str(excinfo.value)
    assert "pkg.missing:grp" in str(excinfo.value)
    assert "cloud" not in root.commands


def test_a_target_that_is_not_a_click_command_raises() -> None:
    root = _root()

    with pytest.raises(ModelOnexError) as excinfo:
        load_cli_extensions(
            root,
            _points(_StubEntryPoint("cloud", "pkg.mod:thing", loaded=_NOT_A_COMMAND)),
        )

    assert excinfo.value.error_code == EnumCoreErrorCode.REGISTRY_VALIDATION_FAILED
    assert "str" in str(excinfo.value)


def test_a_name_collision_raises_rather_than_silently_shadowing() -> None:
    """Two distributions claiming one name resolve in iteration order.

    Skipping keeps the first, overwriting keeps the last, and ``entry_points``
    guarantees neither order — so either choice makes which command runs a
    property of the machine. The collision is named instead.
    """
    root = _root()
    load_cli_extensions(
        root, _points(_StubEntryPoint("cloud", "pkg.a:grp", loaded=_healthy_group))
    )

    with pytest.raises(ModelOnexError) as excinfo:
        load_cli_extensions(
            root, _points(_StubEntryPoint("cloud", "pkg.b:grp", loaded=_healthy_group))
        )

    assert excinfo.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
    assert "cloud" in str(excinfo.value)


def test_a_collision_with_a_core_command_also_raises() -> None:
    """An extension may not shadow a command omnibase_core owns."""
    root = _root()

    @root.command("validate")
    def _validate() -> None:
        """A core-owned command."""

    with pytest.raises(ModelOnexError) as excinfo:
        load_cli_extensions(
            root,
            _points(_StubEntryPoint("validate", "pkg.x:grp", loaded=_healthy_group)),
        )

    assert excinfo.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION


def test_the_live_cli_loaded_its_extensions_without_raising() -> None:
    """The real installed set must be well-formed — this is the install-time contract.

    Importing ``cli_commands`` runs the loader over the live ``onex.cli`` group.
    If any installed distribution advertised a malformed command, that import
    would now raise, and this module's other imports would never have resolved.
    Asserting on the imported ``cli`` makes that implicit success explicit.
    """
    from omnibase_core.cli.cli_commands import cli

    assert isinstance(cli, click.Group)
