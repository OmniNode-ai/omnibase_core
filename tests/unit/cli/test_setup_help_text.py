# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21311 AC5, core half: one job per command, and the quickstart is onex setup.

``onex setup`` itself ships from omnimarket (an ``onex.cli`` entry point), so
this module checks the three core commands it overlapped with: ``init``,
``bootstrap`` and ``install`` each state one job no other of them claims, none
claims the machine setup that ``onex setup`` owns, each sends a new developer
to ``onex setup``, and the root help's quickstart command is ``onex setup``.
"""

from __future__ import annotations

import re

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli

# How each command's help states its job. A phrase must appear in its owner's
# help and in no other command's help.
_JOBS = {
    "init": "scaffold a new onex project",
    "bootstrap": "piped in from stdin",
    "install": "install an onex contract package",
}
# The job onex setup owns; none of the core commands may claim it.
_SETUP_JOB = "set up this machine"


def _help(*args: str) -> str:
    result = CliRunner().invoke(cli, [*args, "--help"])
    assert result.exit_code == 0, result.output
    return " ".join(result.output.split())


@pytest.mark.unit
class TestSetupHelpText:
    def test_each_job_is_claimed_by_exactly_one_command(self) -> None:
        helps = {name: _help(name).lower() for name in _JOBS}
        for owner, phrase in _JOBS.items():
            claimants = [name for name, text in helps.items() if phrase in text]
            assert claimants == [owner], (phrase, claimants)

    def test_no_core_command_claims_machine_setup(self) -> None:
        for name in _JOBS:
            assert _SETUP_JOB not in _help(name).lower(), name

    @pytest.mark.parametrize("name", sorted(_JOBS))
    def test_each_command_sends_a_new_developer_to_onex_setup(self, name: str) -> None:
        assert "onex setup" in _help(name), f"{name} help does not point to onex setup"

    def test_root_quickstart_command_is_onex_setup(self) -> None:
        result = CliRunner().invoke(cli, ["--help"])
        assert result.exit_code == 0, result.output
        quickstart = re.search(
            r"Quickstart.*?\n\s+(onex \S+)", result.output, re.DOTALL
        )
        assert quickstart, result.output
        assert quickstart.group(1) == "onex setup"
