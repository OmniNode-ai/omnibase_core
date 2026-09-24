# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI module for omnibase_core.

The command-line interface for omnibase_core,
including the onex entry point and runtime-host-dev command.

Usage:
    onex --help
    onex --version
    onex validate <path>
    onex contract --help
    onex demo --help

    omninode-runtime-host-dev CONTRACT.yaml  # Dev/test only
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from omnibase_core.cli.cli_commands import cli

if TYPE_CHECKING:
    from omnibase_core.cli.cli_contract import contract as contract
    from omnibase_core.cli.cli_demo import demo as demo
    from omnibase_core.cli.cli_runtime_host import main as runtime_host_dev_main

__all__ = ["cli", "contract", "demo", "runtime_host_dev_main"]

# PEP 562 lazy module attributes (OMN-19444).
#
# ``contract``, ``demo`` and ``runtime_host_dev_main`` used to be imported
# eagerly above. Python always runs a package's ``__init__.py`` before any of
# its submodules, so that made importing ANY submodule of ``omnibase_core.cli``
# -- including ``cli_commands``, which the ``onex`` console script
# (``pyproject.toml``: ``onex = "omnibase_core.cli.cli_commands:cli"``) imports
# directly -- pay for ``cli_contract``'s and ``cli_demo``'s own transitive
# import trees first, whether or not either command was ever invoked.
# Deferring them to first attribute access keeps
# ``from omnibase_core.cli import contract`` (and ``omnibase_core.cli.contract``)
# working exactly as before; only the timing changes. ``cli`` itself stays
# eager: every consumer of this package needs it, so deferring it buys nothing
# and would only complicate the one attribute every entry point actually reads.
_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "contract": ("omnibase_core.cli.cli_contract", "contract"),
    "demo": ("omnibase_core.cli.cli_demo", "demo"),
    "runtime_host_dev_main": ("omnibase_core.cli.cli_runtime_host", "main"),
}


def __getattr__(name: str) -> object:
    target = _LAZY_ATTRS.get(name)
    if target is None:
        # PEP 562 module __getattr__ must raise AttributeError, not a domain
        # error, or attribute-lookup protocols (hasattr, getattr with a
        # default, dir(), IDE/typing tooling) break.
        # error-ok: PEP 562 requires AttributeError from module __getattr__
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr_name = target
    value = getattr(importlib.import_module(module_path), attr_name)
    globals()[name] = value  # cache: subsequent access skips __getattr__
    return value
