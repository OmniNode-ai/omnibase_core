# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RULING 2026-10-29T01:50:26Z: first-party iteration requires dev-merge tags."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_dev_tag_lineage_facts import (
    ModelDevTagLineageFacts,
)
from omnibase_core.nodes.node_dev_tag_lineage_effect.runtime_dev_tag_lineage import run
from omnibase_core.validation.checker_dev_tag_lineage import check_dev_tag_invariants
from omnibase_core.validation.validator_dev_tag_lineage import ValidatorDevTagLineage

pytestmark = pytest.mark.unit
_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/validation/dev_tag_lineage"
_FORMS = [
    ("clean_first_party_dev_tag", []),
    ("violation_first_party_sha_rev", ["first_party_not_dev_tag"]),
    ("violation_first_party_branch", ["first_party_not_dev_tag"]),
    ("violation_first_party_release_tag", ["first_party_not_dev_tag"]),
    ("violation_first_party_path", ["first_party_not_dev_tag"]),
    ("violation_first_party_url", ["first_party_not_dev_tag"]),
    ("violation_first_party_index", ["first_party_not_dev_tag"]),
    ("violation_first_party_direct_sha", ["first_party_not_dev_tag"]),
    ("violation_first_party_override", ["first_party_version_override"]),
    ("violation_first_party_project_exact", ["first_party_version_override"]),
    ("violation_first_party_release_only", ["first_party_release_only"]),
]


def _rules(phase: str) -> tuple[str, ...]:
    return tuple(
        rule.rule_id
        for rule in ValidatorDevTagLineage().contract.rules
        if (rule.parameters or {})["phase"] == phase
    )


def _text(fixture: str) -> str:
    return (_FIXTURES / fixture / "pyproject.toml.txt").read_text()


@pytest.mark.parametrize(("fixture", "expected"), _FORMS)
def test_planted_invariant_forms(fixture: str, expected: list[str]) -> None:
    issues = check_dev_tag_invariants(
        Path("pyproject.toml"), _text(fixture), ValidatorDevTagLineage().contract
    )
    assert [issue.rule_name for issue in issues] == expected
    assert all(issue.suggestion for issue in issues)


@pytest.mark.parametrize(
    "channel",
    [
        "project.dependencies",
        "project.optional-dependencies",
        "dependency-groups",
        "tool.uv.override-dependencies",
        "tool.uv.constraint-dependencies",
        "tool.uv.dev-dependencies",
    ],
)
@pytest.mark.parametrize("exact", ["==2.3.4", "===2.3.4", ">=2.3.0,==2.3.4"])
def test_exact_version_is_refused_in_every_channel(channel: str, exact: str) -> None:
    text = '[project]\nname="consumer"\nversion="1.0.0"\n'
    requirement = f'"omnibase-core{exact}"'
    if channel == "project.dependencies":
        text += f"dependencies=[{requirement}]\n"
    elif channel == "project.optional-dependencies":
        text += f"[project.optional-dependencies]\nfeature=[{requirement}]\n"
    elif channel == "dependency-groups":
        text += f'[dependency-groups]\ntest=[{requirement}]\nfull=[{{include-group="test"}}]\n'
    else:
        text += f"[tool.uv]\n{channel.rsplit('.', 1)[1]}=[{requirement}]\n"
    text += '[tool.uv.sources]\nomnibase-core={git="https://example.test/core.git",tag="dev-20261029143607-aaaaaaaaaaaa"}\n'
    issues = check_dev_tag_invariants(
        Path("pyproject.toml"), text, ValidatorDevTagLineage().contract
    )
    assert [issue.rule_name for issue in issues] == ["first_party_version_override"]


@pytest.mark.parametrize(
    "ref", ["dev-20261029143607-aaaaaaaaaaaa", "v2.3.4", "dev", "a" * 40, ""]
)
def test_direct_git_requirements_require_a_dev_tag(ref: str) -> None:
    suffix = "@" + ref if ref else ""
    text = f'[project]\nname="consumer"\nversion="1.0.0"\ndependencies=["Omnibase_Core @ git+ssh://git@example.test/core.git{suffix}#subdirectory=pkg"]\n'
    issues = check_dev_tag_invariants(
        Path("pyproject.toml"), text, ValidatorDevTagLineage().contract
    )
    assert [issue.rule_name for issue in issues] == (
        [] if ref.startswith("dev-2026") else ["first_party_not_dev_tag"]
    )


@pytest.mark.parametrize("fixture", [name for name, _ in _FORMS])
def test_own_package_is_never_judged(fixture: str) -> None:
    text = (
        _text(fixture)
        .replace('name = "consumer"', 'name = "Omnibase_Core"')
        .replace('name="consumer"', 'name="Omnibase_Core"')
    )
    assert not check_dev_tag_invariants(
        Path("pyproject.toml"), text, ValidatorDevTagLineage().contract
    )


def test_non_first_party_is_ignored_and_package_filter_is_normalized() -> None:
    text = (
        _text("violation_first_party_sha_rev")
        + 'omnibase-spi={path="../spi"}\nthird-party={branch="main",git="https://example.test/third.git"}\n'
    )
    contract = ValidatorDevTagLineage().contract
    assert len(check_dev_tag_invariants(Path("pyproject.toml"), text, contract)) == 2
    issues = check_dev_tag_invariants(
        Path("pyproject.toml"), text, contract, "OMNIBASE.CORE"
    )
    assert len(issues) == 1 and issues[0].message.startswith("omnibase-core:")
    assert not check_dev_tag_invariants(
        Path("pyproject.toml"), text, contract, "third-party"
    )


def test_invariant_only_validation_needs_no_git_resolver(tmp_path: Path) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text(_text("violation_first_party_override"))
    validator = ValidatorDevTagLineage(root=tmp_path, rules=_rules("invariant"))
    assert [issue.rule_name for issue in validator.validate_file(project).issues] == [
        "first_party_version_override"
    ]
    filtered = ValidatorDevTagLineage(
        root=tmp_path, package="omnibase-spi", rules=_rules("invariant")
    )
    assert filtered.validate_file(project).is_valid


def test_identity_rule_selection_keeps_release_overrides_out_of_findings(
    tmp_path: Path,
) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text(_text("violation_first_party_override"))
    calls = []

    def resolve(request):
        calls.append(request)
        return ModelDevTagLineageFacts(
            tag_exists=True,
            commit="a" * 40,
            version="2.3.4",
            on_branch=True,
            detail="ok",
        )

    all_rules = ValidatorDevTagLineage(root=tmp_path, resolver=resolve)
    assert [issue.rule_name for issue in all_rules.validate_file(project).issues] == [
        "first_party_version_override"
    ]
    assert len(calls) == 1
    calls.clear()
    identity = ValidatorDevTagLineage(
        root=tmp_path, resolver=resolve, rules=_rules("identity")
    )
    assert identity.validate_file(project).is_valid and len(calls) == 1


def test_cli_rule_subset_and_unknown_rule_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text(_text("violation_first_party_sha_rev"))
    assert (
        run(
            [
                str(project),
                "--rules",
                "first_party_release_only",
                "--report-json",
                str(tmp_path / "report.json"),
            ]
        )
        == 0
    )
    assert (
        run(
            [
                str(project),
                "--rules",
                "first_party_not_dev_tag",
                "--package",
                "omnibase-spi",
                "--report-json",
                str(tmp_path / "filtered.json"),
            ]
        )
        == 0
    )
    assert run([str(project), "--rules", "not_a_contract_rule"]) == 1
    output = capsys.readouterr().out
    assert "runtime error" in output and "not_a_contract_rule" in output
