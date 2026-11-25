# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""An onex command group declares its surface; the default view lists only customer groups (OMN-26518).

Failure modes pinned here, one test family per ticket falsifier:
  command_surface_declared
      A group that is registered with no declaration must fail a test; it is never
      defaulted to a surface silently.
  command_surface_default_customer
      ``onex --help``, ``list_commands`` and shell completion list only customer
      groups; ``get_command`` resolves a hidden internal group only with the
      operator switch on.
  command_surface_operator_switch
      The operator switch lists and resolves every group.
  command_surface_audit_reads_declaration
      The customer-surface parameter audit reads the same declaration as the
      listing, so a group declared internal is never audited as customer.
  command_surface_seed
      The seeded customer set is exactly the operator proposal's 14 groups, and
      the 16 unclear groups are internal until the operator decides.
"""

from __future__ import annotations

from types import ModuleType

import click
import pytest
from click.shell_completion import ShellComplete
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import (
    _CLI_EXTENSION_GROUP,
    _LAZY_BUILTIN_COMMANDS,
    _entry_points,
    _LazyCoreCommandGroup,
    cli,
    register_lazy_cli_extensions,
)

pytestmark = pytest.mark.unit

SWITCH = "ONEX_CLI_SHOW_ALL_COMMANDS"

CUSTOMER_14 = frozenset(
    {
        "validate",
        "info",
        "health",
        "doctor",
        "init",
        "new",
        "delegate",
        "node",
        "skill",
        "metering",
        "cloud",
        "local",
        "dashboard",
        "secret",
    }
)

UNCLEAR_16 = frozenset(
    {
        "contract",
        "demo",
        "registry",
        "install",
        "uninstall",
        "run",
        "run-node",
        "config",
        "auth",
        "profile",
        "market",
        "tui",
        "models",
        "setup",
        "delegation",
        "plugins",
    }
)


def _surface() -> ModuleType:
    # imported late so each test fails on its own
    from omnibase_core.models.cli import model_cli_command_surface

    return model_cli_command_surface


@pytest.fixture
def switch_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SWITCH, raising=False)


def _listed(group: click.Group) -> list[str]:
    return group.list_commands(click.Context(group))


def _registered_names() -> set[str]:
    names = set(_LAZY_BUILTIN_COMMANDS) | set(cli.commands) | set(cli._lazy_extensions)
    names |= {ep.name for ep in _entry_points(group=_CLI_EXTENSION_GROUP)}
    return names


def _probe_group_with_undeclared_extension() -> _LazyCoreCommandGroup:
    from importlib.metadata import EntryPoint

    probe = _LazyCoreCommandGroup(name="probe", lazy_commands=_LAZY_BUILTIN_COMMANDS)
    register_lazy_cli_extensions(
        probe,
        [
            EntryPoint(
                name="brand-new-extension",
                # A loadable target: a hidden extension that fails to load is named
                # to the caller (OMN-26044), a healthy one stays hidden.
                value="omnibase_core.cli.cli_registry:registry",
                group=_CLI_EXTENSION_GROUP,
            )
        ],
    )
    return probe


# --------------------------------------------------------------------------
# command_surface_declared
# --------------------------------------------------------------------------


def test_command_surface_declared_every_registered_group_has_a_declaration() -> None:
    """Every group this repo registers, built-in or onex.cli, declares a surface."""
    missing = _surface().undeclared_command_names(sorted(_registered_names()))
    assert missing == [], (
        f"registered with no surface declaration: {missing}. Declare each as "
        "customer or internal; a group is never defaulted silently."
    )


def test_command_surface_declared_positive_control_reports_an_undeclared_group() -> (
    None
):
    """A zero must come from a check that can see a miss."""
    surface = _surface()
    assert surface.undeclared_command_names(["validate", "brand-new-extension"]) == [
        "brand-new-extension"
    ]
    assert surface.declared_surface("brand-new-extension") is None


def test_command_surface_declared_undeclared_extension_is_hidden_not_defaulted_customer(
    switch_off: None,
) -> None:
    """An extension another package registers with no declaration is internal at runtime."""
    probe = _probe_group_with_undeclared_extension()
    assert "brand-new-extension" not in _listed(probe)
    assert probe.get_command(click.Context(probe), "brand-new-extension") is None


def test_command_surface_declared_the_declaration_values_are_the_two_surfaces() -> None:
    surface = _surface()
    values = set(surface.CLI_COMMAND_SURFACES.values())
    assert values == {
        surface.EnumCliCommandSurface.CUSTOMER,
        surface.EnumCliCommandSurface.INTERNAL,
    }


# --------------------------------------------------------------------------
# command_surface_default_customer
# --------------------------------------------------------------------------


def test_command_surface_default_customer_list_commands_hides_internal_groups(
    switch_off: None,
) -> None:
    listed = set(_listed(cli))
    assert listed, "the default view must not be empty"
    assert listed <= CUSTOMER_14, (
        f"internal groups in the default view: {listed - CUSTOMER_14}"
    )
    # the core-registered customer groups are all present
    assert {"validate", "info", "health", "doctor", "init", "new"} <= listed


def test_command_surface_default_customer_help_lists_only_customer_groups(
    switch_off: None,
) -> None:
    output = CliRunner().invoke(cli, ["--help"]).output
    for hidden in (
        "compliance",
        "composition-report",
        "bootstrap",
        "hooks",
        "run-node",
    ):
        assert f"\n  {hidden} " not in output, f"{hidden} leaked into onex --help"
    assert "\n  validate " in output


def test_command_surface_default_customer_shell_completion_lists_only_customer_groups(
    switch_off: None,
) -> None:
    completer = ShellComplete(cli, {}, "onex", "_ONEX_COMPLETE")
    names = {item.value for item in completer.get_completions([], "")}
    assert names, "completion must offer the customer groups"
    assert names <= CUSTOMER_14, (
        f"internal groups offered by completion: {names - CUSTOMER_14}"
    )


def test_command_surface_default_customer_get_command_refuses_internal_group(
    switch_off: None,
) -> None:
    ctx = click.Context(cli)
    assert cli.get_command(ctx, "compliance") is None
    assert cli.get_command(ctx, "validate") is not None


def test_command_surface_default_customer_invocation_by_name_fails_without_switch(
    switch_off: None,
) -> None:
    result = CliRunner().invoke(cli, ["compliance", "--help"])
    assert result.exit_code != 0
    assert "No such command" in result.output


def test_command_surface_default_customer_bare_onex_still_finds_the_tui(
    switch_off: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare `onex` in a terminal opens tui (OMN-23413 AC16) though tui is not a listed group."""
    from omnibase_core.cli import cli_commands

    opened: list[bool] = []

    @click.command("tui")
    def fake_tui() -> None:
        opened.append(True)

    monkeypatch.setitem(cli.commands, "tui", fake_tui)
    monkeypatch.setattr(cli_commands, "_interactive_terminal", lambda: True)
    assert "tui" not in _listed(cli)
    assert cli.get_command(click.Context(cli), "tui") is None
    result = CliRunner().invoke(cli, [])
    assert result.exit_code == 0, result.output
    assert opened == [True]


# --------------------------------------------------------------------------
# command_surface_operator_switch
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_command_surface_operator_switch_lists_every_group(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(SWITCH, value)
    listed = set(_listed(cli))
    assert set(_LAZY_BUILTIN_COMMANDS) <= listed
    assert {"validate", "info", "health", "discover"} <= listed
    assert "compliance" in listed


def test_command_surface_operator_switch_resolves_and_runs_internal_group_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SWITCH, "1")
    assert cli.get_command(click.Context(cli), "compliance") is not None
    result = CliRunner().invoke(cli, ["compliance", "--help"])
    assert result.exit_code == 0, result.output


def test_command_surface_operator_switch_lists_an_undeclared_extension_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SWITCH, "1")
    assert "brand-new-extension" in _listed(_probe_group_with_undeclared_extension())


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "garbage"])
def test_command_surface_operator_switch_off_values_keep_the_default_view(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(SWITCH, value)
    assert set(_listed(cli)) <= CUSTOMER_14


# --------------------------------------------------------------------------
# command_surface_audit_reads_declaration
# --------------------------------------------------------------------------


def test_command_surface_audit_reads_declaration_customer_names_match_the_listing(
    switch_off: None,
) -> None:
    """The audit's reader and the default view come from one declaration."""
    surface = _surface()
    assert set(_listed(cli)) == surface.customer_command_names() & _registered_names()


def test_command_surface_audit_reads_declaration_internal_group_is_not_audited_as_customer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _surface()
    audited = surface.customer_command_names()
    assert "compliance" not in audited
    assert "validate" in audited
    # the reader does not depend on the operator switch: the switch changes the
    # view, never the audit set
    monkeypatch.setenv(SWITCH, "1")
    assert surface.customer_command_names() == audited


def test_command_surface_audit_reads_declaration_a_reclassified_group_leaves_the_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flip one group in the declaration and both the audit and the view follow."""
    surface = _surface()
    flipped = dict(surface.CLI_COMMAND_SURFACES)
    flipped["validate"] = surface.EnumCliCommandSurface.INTERNAL
    monkeypatch.setattr(surface, "CLI_COMMAND_SURFACES", flipped)
    monkeypatch.delenv(SWITCH, raising=False)
    assert "validate" not in surface.customer_command_names()
    assert "validate" not in _listed(cli)


# --------------------------------------------------------------------------
# command_surface_seed
# --------------------------------------------------------------------------


def test_command_surface_seed_customer_set_is_exactly_the_proposals_14() -> None:
    assert _surface().customer_command_names() == CUSTOMER_14
    assert len(CUSTOMER_14) == 14


def test_command_surface_seed_unclear_16_are_internal_until_the_operator_decides() -> (
    None
):
    surface = _surface()
    assert surface.UNCLEAR_PENDING_OPERATOR_DECISION == UNCLEAR_16
    assert len(UNCLEAR_16) == 16
    assert surface.internal_command_names() >= UNCLEAR_16
    assert not UNCLEAR_16 & surface.customer_command_names()


def test_command_surface_seed_declares_all_63_groups_of_the_clean_install() -> None:
    surface = _surface()
    assert len(surface.CLI_COMMAND_SURFACES) == 63
    assert len(surface.internal_command_names()) == 49  # 33 internal + 16 unclear


def test_command_surface_seed_setup_is_internal_so_a_customer_listing_lacks_it(
    switch_off: None,
) -> None:
    surface = _surface()
    assert surface.declared_surface("setup") is surface.EnumCliCommandSurface.INTERNAL
    assert "setup" not in _listed(cli)
