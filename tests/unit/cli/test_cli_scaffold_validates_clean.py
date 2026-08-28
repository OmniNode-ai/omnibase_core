# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-16680: a freshly scaffolded ONEX project must pass `onex validate`.

`onex init` -> `onex new node` -> `onex validate` is the documented
getting-started flow and every one of those three commands is a stable
external SDK surface (``omnibase_core/CLAUDE.md`` -> External SDK Surface).
A new user's first ``onex validate`` therefore runs against code they did not
write, and it must come back clean.

These tests are the AC2 anti-drift guard: the scaffold templates in
``cli_new.py`` and the validators in ``omnibase_core.validation`` cannot drift
apart again without one of them going red.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli

NODE_TYPES = ("compute", "effect", "reducer", "orchestrator")


def _scaffold_project(runner: CliRunner, workdir: Path) -> Path:
    """Run `onex init` + `onex new node` for all four archetypes.

    Args:
        runner: Click test runner.
        workdir: Directory to create the project inside.

    Returns:
        Path to the generated project root.
    """
    result = runner.invoke(cli, ["init", "demo_pkg", "--path", str(workdir)])
    assert result.exit_code == 0, f"onex init failed: {result.output}"

    project = workdir / "demo_pkg"
    for node_type in NODE_TYPES:
        result = runner.invoke(
            cli,
            [
                "new",
                "node",
                f"n-{node_type}",
                "--type",
                node_type,
                "--project-root",
                str(project),
            ],
        )
        assert result.exit_code == 0, (
            f"onex new node {node_type} failed: {result.output}"
        )
    return project


@pytest.mark.unit
def test_onex_validate_exits_zero_on_a_clean_tree(tmp_path: Path) -> None:
    """`onex validate` must exit 0 when nothing is wrong.

    Regression guard for the swallowed-``ctx.exit`` defect: ``ctx.exit()``
    raises ``click.exceptions.Exit``, which subclasses ``RuntimeError`` and was
    therefore caught by the command's broad ``except Exception`` handler and
    re-raised as ``ClickException("Unexpected error: EnumCLIExitCode.SUCCESS")``.
    That made exit code 1 the ONLY reachable outcome of `onex validate`, on any
    input, so AC1 was unreachable no matter what the scaffold emitted.
    """
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(tmp_path / "src")])

    assert result.exit_code == 0, f"clean tree did not exit 0: {result.output}"
    assert "Unexpected error" not in result.output


@pytest.mark.unit
def test_scaffolded_project_passes_onex_validate(tmp_path: Path) -> None:
    """AC1: init -> new node (all four archetypes) -> validate exits 0."""
    runner = CliRunner()
    project = _scaffold_project(runner, tmp_path)

    result = runner.invoke(cli, ["validate", str(project / "src")])

    assert result.exit_code == 0, f"onex validate failed:\n{result.output}"
    assert "[FAIL]" not in result.output


@pytest.mark.unit
def test_scaffolded_project_has_zero_validation_issues(tmp_path: Path) -> None:
    """AC1 (strict): every validator reports zero issues, not merely `is_valid`.

    The `patterns` validator only flips ``is_valid`` under ``--strict``, so a
    plain exit-0 assertion would let pattern drift accumulate silently. This
    asserts the stronger, drift-proof property directly against the suite.
    """
    from omnibase_core.services.service_validation_suite import ServiceValidationSuite

    runner = CliRunner()
    project = _scaffold_project(runner, tmp_path)

    results = ServiceValidationSuite().run_all_validations(project / "src", strict=True)
    offenders = {
        name: result.errors for name, result in results.items() if result.errors
    }
    assert offenders == {}, f"scaffold trips validators: {offenders}"


@pytest.mark.unit
def test_scaffolded_contract_node_type_is_a_real_enum_member(tmp_path: Path) -> None:
    """Drift 1: `node_type` must name an actual `EnumNodeType` member.

    ``ModelYamlContract.validate_node_type`` matches the YAML string against
    ``EnumNodeType`` by name or value **case-insensitively** (it upper-cases the
    input first). So the scaffold's ``COMPUTE`` and the lowercase ``compute``
    used by several in-repo contracts fail identically — neither is a member.
    The generic archetype members are ``<ARCHETYPE>_GENERIC``, so that is the
    only spelling that resolves.
    """
    from omnibase_core.enums.enum_node_type import EnumNodeType
    from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract

    runner = CliRunner()
    project = _scaffold_project(runner, tmp_path)

    for node_type in NODE_TYPES:
        expected = f"{node_type.upper()}_GENERIC"
        contract = (
            project / "src" / "demo_pkg" / "nodes" / f"n_{node_type}" / "contract.yaml"
        ).read_text()
        assert f"node_type: {expected}" in contract
        # The value the scaffold writes must round-trip through the same
        # validator `onex validate` uses, not merely look plausible.
        assert ModelYamlContract.validate_node_type(expected) is EnumNodeType[expected]
