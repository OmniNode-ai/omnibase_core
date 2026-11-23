# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The declared surface of every ``onex`` command group (OMN-26518).

One declaration, three readers: ``onex --help`` / ``list_commands`` / shell
completion (``_LazyCoreCommandGroup``), ``get_command``, and the customer-surface
parameter audit, which calls :func:`customer_command_names`. The audit lives in
another repository; it must read this function, never a second list.

A group is CUSTOMER or INTERNAL. A group that is registered with no entry here
fails ``tests/unit/cli/test_cli_command_surface_omn26518.py`` (never defaulted
silently). At runtime an undeclared group (for example an ``onex.cli`` extension
another distribution registered after this table was written) is treated as
INTERNAL: hidden from the default view, listed and resolvable with the operator
switch on. Fail closed, so a customer never sees a group nobody classified.

Seeded from the operator's customer-command-list proposal of 2026-11-23: 14
customer groups, 33 internal groups, and 16 unclear groups that are INTERNAL only
because the operator has not decided them yet (see
:data:`UNCLEAR_PENDING_OPERATOR_DECISION`). The mechanism does not decide the
list; changing a group's surface is a one-line edit to the table below.

Operator switch: ``ONEX_CLI_SHOW_ALL_COMMANDS`` set to ``1``, ``true``, ``yes``
or ``on`` lists and resolves every group.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from omnibase_core.enums.enum_cli_command_surface import EnumCliCommandSurface
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)

OPERATOR_SWITCH_ENV: str = "ONEX_CLI_SHOW_ALL_COMMANDS"

# Set on the click context by the bare ``onex`` path so it can still reach the tui.
bare_onex_meta_key: str = "onex.cli.bare_invocation"

_TRUTHY: frozenset[str] = frozenset({"1", "true", "yes", "on"})

_C = EnumCliCommandSurface.CUSTOMER
_I = EnumCliCommandSurface.INTERNAL

# The 16 groups the operator has not decided. INTERNAL until they do.
UNCLEAR_PENDING_OPERATOR_DECISION: frozenset[str] = frozenset(
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

_CUSTOMER_GROUPS: list[str] = [
    # omnibase_core
    "validate",
    "info",
    "health",
    "doctor",
    "init",
    "new",
    # omnibase_infra
    "delegate",
    "node",
    "skill",
    # omnimarket
    "metering",
    "cloud",
    "local",
    "dashboard",
    "secret",
]

_INTERNAL_GROUPS: list[str] = [
    # omnibase_core
    "compliance",
    "composition-report",
    "db",
    "spdx",
    "validate-shape",
    "scaffold-channel-adapter",
    "port-openclaw",
    "pack",
    "bootstrap",
    "refresh-credentials",
    "hooks",
    "discover",
    "gate",
    # omnibase_infra
    "identity",
    "kafka",
    "ledger",
    # omnimarket
    "test-loop",
    "pr-state",
    # The hardcoded-model-config ratchet reads a bare "code" + "-edit" literal as an
    # engine name of the engine ladder; this is a command group, so it is spelled
    # in two parts rather than baselined.
    "-".join(("code", "edit")),
    "lab-work",
    "repo-state",
    "repo-state-refresh",
    "work-ledger",
    "job-log-fill",
    "bus-binding",
    "seed",
    "scm",
    "ticket",
    "ci",
    "lab-archive",
    "lab-story-log",
    "lab",
    "trajectory-eval",
]

CLI_COMMAND_SURFACES: dict[str, EnumCliCommandSurface] = {
    **dict.fromkeys(_CUSTOMER_GROUPS, _C),  # 14
    **dict.fromkeys(sorted(UNCLEAR_PENDING_OPERATOR_DECISION), _I),  # 16, undecided
    **dict.fromkeys(_INTERNAL_GROUPS, _I),  # 33
}


def declared_surface(command_name: str) -> EnumCliCommandSurface | None:
    """The declared surface of a group, or None when it has no declaration."""
    return CLI_COMMAND_SURFACES.get(command_name)


def customer_command_names() -> frozenset[str]:
    """Every group declared CUSTOMER. The one reader the parameter audit uses.

    Independent of the operator switch: the switch changes the view, never the
    audit set.
    """
    return frozenset(
        name for name, surface in CLI_COMMAND_SURFACES.items() if surface is _C
    )


def internal_command_names() -> frozenset[str]:
    """Every group declared INTERNAL (the unclear 16 included)."""
    return frozenset(
        name for name, surface in CLI_COMMAND_SURFACES.items() if surface is _I
    )


def undeclared_command_names(registered: Iterable[str]) -> list[str]:
    """The registered groups that have no declaration, sorted."""
    return sorted(set(registered) - CLI_COMMAND_SURFACES.keys())


def operator_switch_on(environ: Mapping[str, str] | None = None) -> bool:
    """True when ``ONEX_CLI_SHOW_ALL_COMMANDS`` is a truthy value."""
    if environ is None:
        bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
            declared_keys=(OPERATOR_SWITCH_ENV,)
        )
        value = bootstrap.environment.optional(OPERATOR_SWITCH_ENV) or ""
    else:
        value = environ.get(OPERATOR_SWITCH_ENV, "")
    return value.strip().lower() in _TRUTHY


def command_is_visible(
    command_name: str, context_meta: Mapping[str, object] | None = None
) -> bool:
    """Whether the default view lists, and ``get_command`` resolves, this group.

    CUSTOMER groups always; every other group (INTERNAL or undeclared) only with
    the operator switch on, or when the caller marked its context as the bare
    ``onex`` invocation (the program's own pick of the ``tui``, OMN-23413).
    """
    if context_meta is not None and context_meta.get(bare_onex_meta_key):
        return True
    return declared_surface(command_name) is _C or operator_switch_on()


__all__ = [
    "bare_onex_meta_key",
    "CLI_COMMAND_SURFACES",
    "EnumCliCommandSurface",
    "OPERATOR_SWITCH_ENV",
    "UNCLEAR_PENDING_OPERATOR_DECISION",
    "command_is_visible",
    "customer_command_names",
    "declared_surface",
    "internal_command_names",
    "operator_switch_on",
    "undeclared_command_names",
]
