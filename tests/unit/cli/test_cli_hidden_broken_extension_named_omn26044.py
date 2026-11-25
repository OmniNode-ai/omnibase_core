# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A broken ``onex.cli`` entry point is named to a customer even while hidden (OMN-26044).

OMN-26518 hides every group that is not declared CUSTOMER, and ``get_command``
answered a hidden name with ``None``: click then prints "No such command". A
broken extension (the OMN-16967 fail-loud case) fell into that and vanished, so
a customer whose install shipped a broken extension was told the command did
not exist. The customer-surface check ``broken_command_named_error`` plants two
broken ``onex.cli`` entry points and wants an error that names the command.

The contract pinned here:
  * customer mode, hidden broken extension: a non-zero exit and an error that
    names the command and says it failed to load, never "No such command", and
    none of the internal detail the operator view carries (distribution name,
    target path, exception text);
  * operator switch on: the full packaging-defect error, as before;
  * a hidden extension that loads fine, and a name nobody registered, stay
    "No such command" (no new listing, no existence oracle for healthy groups);
  * the root listing never lists the broken hidden name.

The entry points are injected stubs, nothing is installed.
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
from omnibase_core.errors.model_onex_error import ModelOnexError

pytestmark = pytest.mark.unit

SWITCH = "ONEX_CLI_SHOW_ALL_COMMANDS"

_DIST_NAME = "internal-only-dist-xyzzy"
_TARGET_IMPORT = "internal_only_module_plugh:group"
_TARGET_TYPE = "json:dumps"
_IMPORT_FAILURE = "No module named 'internal_only_module_plugh'"
_LEAKS = (_DIST_NAME, "internal_only_module_plugh", _IMPORT_FAILURE, "json:dumps")


@click.command("healthy-hidden")
def _healthy() -> None:
    """A well-formed extension command that no declaration marks as customer."""


class _Dist:
    def __init__(self, name: str) -> None:
        self.name = name


class _StubEntryPoint:
    group = "onex.cli"

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
        self.dist = _Dist(_DIST_NAME)
        self._loaded = loaded
        self._raises = raises

    def load(self) -> object:
        if self._raises is not None:
            raise self._raises
        return self._loaded


def _root(*stubs: _StubEntryPoint) -> _LazyCoreCommandGroup:
    root = _LazyCoreCommandGroup(name="root")
    register_lazy_cli_extensions(root, cast(list[EntryPoint], list(stubs)))
    return root


def _broken_import(name: str = "broken-import") -> _StubEntryPoint:
    return _StubEntryPoint(
        name, _TARGET_IMPORT, raises=ModuleNotFoundError(_IMPORT_FAILURE)
    )


def _broken_type(name: str = "broken-type") -> _StubEntryPoint:
    return _StubEntryPoint(name, _TARGET_TYPE, loaded=len)


@pytest.fixture
def customer_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SWITCH, raising=False)


@pytest.mark.parametrize(
    ("stub", "name"),
    [(_broken_import(), "broken-import"), (_broken_type(), "broken-type")],
    ids=["import_error", "wrong_type"],
)
def test_customer_mode_names_a_hidden_broken_extension(
    customer_mode: None, stub: _StubEntryPoint, name: str
) -> None:
    result = CliRunner().invoke(_root(stub), [name])

    assert result.exit_code not in (0, 2), result.output
    assert name in result.output
    assert "No such command" not in result.output
    assert "failed to load" in result.output


@pytest.mark.parametrize("stub", [_broken_import(), _broken_type()])
def test_customer_mode_error_carries_no_internal_detail(
    customer_mode: None, stub: _StubEntryPoint
) -> None:
    result = CliRunner().invoke(_root(stub), [stub.name])

    for leak in _LEAKS:
        assert leak not in result.output, f"{leak!r} leaked: {result.output}"
    assert "Traceback" not in result.output


@pytest.mark.parametrize("name", ["broken-import", "broken-type"])
def test_operator_switch_keeps_the_full_packaging_defect_error(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv(SWITCH, "1")
    root = _root(_broken_import(), _broken_type())

    with pytest.raises(ModelOnexError) as excinfo:
        root.get_command(click.Context(root), name)

    message = str(excinfo.value)
    assert name in message
    assert _DIST_NAME in message


def test_customer_mode_hidden_healthy_extension_stays_no_such_command(
    customer_mode: None,
) -> None:
    root = _root(_StubEntryPoint("healthy-hidden", "pkg:cmd", loaded=_healthy))

    result = CliRunner().invoke(root, ["healthy-hidden"])

    assert result.exit_code == 2
    assert "No such command 'healthy-hidden'" in result.output


def test_customer_mode_hidden_healthy_extension_is_not_suggested_back(
    customer_mode: None,
) -> None:
    """Resolving a hidden healthy name must not leave it in the suggestion pool.

    click offers ``Did you mean`` from the group's registered commands; loading
    the extension to learn it is healthy must not register it there, or the
    typed hidden name is echoed back as a suggestion (an existence oracle).
    """
    root = _root(_StubEntryPoint("healthy-hidden", "pkg:cmd", loaded=_healthy))

    first = CliRunner().invoke(root, ["healthy-hidden"])
    second = CliRunner().invoke(root, ["healthy-hidden"])

    assert "Did you mean" not in first.output
    assert "Did you mean" not in second.output
    assert "healthy-hidden" not in root.commands


def test_customer_mode_unregistered_name_stays_no_such_command(
    customer_mode: None,
) -> None:
    result = CliRunner().invoke(_root(_broken_import()), ["never-registered"])

    assert result.exit_code == 2
    assert "No such command 'never-registered'" in result.output


def test_customer_mode_root_listing_does_not_list_the_broken_name(
    customer_mode: None,
) -> None:
    root = _root(_broken_import(), _broken_type())

    assert root.list_commands(click.Context(root)) == []
    result = CliRunner().invoke(root, ["--help"])
    assert result.exit_code == 0, result.output
    assert "broken-import" not in result.output
    assert "broken-type" not in result.output


def test_customer_mode_resolving_a_broken_hidden_name_does_not_unhide_it(
    customer_mode: None,
) -> None:
    root = _root(_broken_import())

    with pytest.raises(click.ClickException):
        root.get_command(click.Context(root), "broken-import")

    assert root.list_commands(click.Context(root)) == []


def test_operator_switch_keeps_full_error_beside_the_named_customer_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub = _broken_import()
    monkeypatch.delenv(SWITCH, raising=False)
    customer = CliRunner().invoke(_root(stub), [stub.name])
    assert "failed to load" in customer.output
    assert _DIST_NAME not in customer.output

    monkeypatch.setenv(SWITCH, "1")
    root = _root(stub)
    with pytest.raises(ModelOnexError) as excinfo:
        root.get_command(click.Context(root), stub.name)
    assert _DIST_NAME in str(excinfo.value)
