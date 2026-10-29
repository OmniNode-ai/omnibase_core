# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic version-floor consumer validator tests (OMN-19998, OMN-21503).

The positive fixture is the 2026-10-15 stall: omnimarket raised its
omnibase-core floor from 0.47.39 to 0.47.44 while omnibase_infra still pinned
0.47.39, so the merge queue of omnibase_infra failed for 6.5 hours.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.version_drift.model_consumer_pyproject import (
    ModelConsumerPyproject,
)
from omnibase_core.models.version_drift.model_version_floor_check_input import (
    ModelVersionFloorCheckInput,
)
from omnibase_core.validation import checker_version_floor_consumers as checker
from omnibase_core.validation import validator_version_floor_consumers as cli
from omnibase_core.validation.checker_version_floor_consumers import (
    check_version_floor_consumers,
    declared_floors,
    parse_version,
)
from omnibase_core.validation.validator_version_floor_consumers import (
    ValidatorVersionFloorConsumers,
    load_layer_map,
)

pytestmark = pytest.mark.unit

LAYER_MAP = load_layer_map()
ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "validation" / "version_floor_consumers"


def _contract() -> ModelValidatorSubcontract:
    return ValidatorVersionFloorConsumers().contract


def _rules(
    contract: ModelValidatorSubcontract | None = None,
) -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in (contract or _contract()).rules}


def _market(core_spec: str, infra_spec: str = ">=0.38.72,<0.39.0") -> str:
    return (
        '[project]\nname = "omnimarket"\nversion = "0.4.315"\n'
        f'dependencies = [\n  "omnibase-core{core_spec}",\n'
        f'  "omnibase-infra{infra_spec}",\n  "pydantic>=2",\n]\n'
    )


def _infra(range_spec: str, exact: str | None) -> str:
    text = (
        '[project]\nname = "omnibase-infra"\n'
        f'dependencies = ["omnibase-core{range_spec}"]\n'
    )
    if exact is not None:
        text += f'\n[tool.uv]\noverride-dependencies = ["omnibase-core=={exact}"]\n'
    return text


def _with_market(name: str, core_spec: str) -> str:
    return (
        f'[project]\nname = "{name}"\n'
        f'dependencies = ["omnibase-core{core_spec}", "omnimarket>=0.4"]\n'
    )


def _run(
    base: str | None,
    head: str,
    consumers: tuple[ModelConsumerPyproject, ...],
    repo: str = "omnimarket",
) -> tuple[str, list[str]]:
    issues = check_version_floor_consumers(
        ModelVersionFloorCheckInput(
            repo=repo,
            layer_map=LAYER_MAP,
            base_pyproject=base,
            head_pyproject=head,
            consumers=consumers,
        ),
        _rules(),
    )
    status = (
        "ERROR"
        if any(i.code != checker.RULE_FLOOR for i in issues)
        else "FAIL"
        if issues
        else "PASS"
    )
    return status, [i.message for i in issues]


def _consumer(repo: str, text: str | None) -> ModelConsumerPyproject:
    return ModelConsumerPyproject(repo=repo, ref="origin/dev", pyproject=text)


def test_floor_raise_ahead_of_a_pinned_consumer_fails_and_names_it() -> None:
    status, messages = _run(
        _market(">=0.47.39,<0.48.0"),
        _market(">=0.47.44,<0.48.0"),
        (_consumer("omnibase_infra", _infra(">=0.47.31,<0.48.0", "0.47.39")),),
    )
    assert status == "FAIL"
    assert len(messages) == 1
    assert "omnibase_infra" in messages[0]
    assert "omnibase-core" in messages[0]
    assert "0.47.44" in messages[0]
    assert "0.47.39" in messages[0]


def test_floor_raise_passes_once_every_consumer_pins_at_least_it() -> None:
    status, messages = _run(
        _market(">=0.47.39,<0.48.0"),
        _market(">=0.47.44,<0.48.0"),
        (_consumer("omnibase_infra", _infra(">=0.47.31,<0.48.0", "0.47.44")),),
    )
    assert (status, messages) == ("PASS", [])


def test_a_consumer_of_the_raising_repository_with_a_lower_floor_fails() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (
            _consumer(
                "omniclaude", _with_market("omninode-claude", ">=0.47.31,<0.48.0")
            ),
        ),
    )
    assert status == "FAIL"
    assert "0.47.31" in messages[0]
    assert "installs the raising repository" in messages[0]


def test_a_range_that_admits_the_raise_passes_for_a_non_consumer_of_it() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (_consumer("omnibase_infra", _infra(">=0.47.31,<0.48.0", None)),),
    )
    assert (status, messages) == ("PASS", [])


@pytest.mark.parametrize("spec", ["<0.47.44", "<=0.47.43", "~=0.47.39.0", "==0.47.*"])
def test_an_upper_bound_below_the_raise_fails(spec: str) -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44" if spec != "==0.47.*" else ">=0.48.1"),
        (_consumer("omnibase_infra", _infra(f">=0.47.0,{spec}", None)),),
    )
    assert status == "FAIL"
    assert "below the new floor" in messages[0]


def test_no_floor_raise_needs_no_consumer() -> None:
    status, messages = _run(
        _market(">=0.47.44"),
        _market(">=0.47.44,<0.48.0"),
        (_consumer("omnibase_infra", None),),
    )
    assert (status, messages) == ("PASS", [])


def test_a_lowered_floor_is_not_a_raise() -> None:
    status, _ = _run(
        _market(">=0.47.44"),
        _market(">=0.47.40"),
        (_consumer("omnibase_infra", _infra(">=0.47.31", None)),),
    )
    assert status == "PASS"


def test_an_unreadable_consumer_is_never_assumed_compatible() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (_consumer("omnibase_infra", None),),
    )
    assert status == "FAIL"
    assert "could not be read" in messages[0]


def test_a_consumer_that_does_not_install_the_package_is_not_counted() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (
            _consumer(
                "omnidash", '[project]\nname = "omnidash"\ndependencies = ["httpx"]\n'
            ),
        ),
    )
    assert (status, messages) == ("PASS", [])


def test_the_changing_repository_is_not_its_own_consumer() -> None:
    status, _ = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (_consumer("omnimarket", _market(">=0.47.39")),),
    )
    assert status == "PASS"


def test_a_newly_declared_sibling_dependency_counts_as_a_raise() -> None:
    base = '[project]\nname = "omnimarket"\ndependencies = []\n'
    status, messages = _run(
        base,
        _market(">=0.47.44"),
        (_consumer("omnibase_infra", _infra(">=0.47.31", "0.47.39")),),
    )
    assert status == "FAIL"
    assert "omnibase_infra" in messages[0]


def test_a_consumer_with_no_lower_bound_fails() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (
            _consumer(
                "omniclaude",
                '[project]\nname = "omninode-claude"\n'
                'dependencies = ["omnibase-core", "omnimarket"]\n',
            ),
        ),
    )
    assert status == "FAIL"
    assert "no lower bound" in messages[0]


def test_every_failing_consumer_is_named() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (
            _consumer("omnibase_infra", _infra(">=0.47.31", "0.47.39")),
            _consumer(
                "omniclaude",
                '[project]\nname = "omninode-claude"\n'
                'dependencies = ["omnibase-core>=0.47.40", "omnimarket"]\n',
            ),
            _consumer(
                "omnibase_internal",
                '[project]\nname = "omnibase-internal"\n'
                '[dependency-groups]\ndev = ["omnibase-core>=0.47.50", "omnimarket"]\n',
            ),
        ),
    )
    assert status == "FAIL"
    named = sorted(m.split(":", 1)[0] for m in messages)
    assert named == ["omnibase_infra", "omniclaude"]


def test_a_third_party_floor_raise_is_not_checked() -> None:
    status, _ = _run(
        '[project]\nname = "omnimarket"\ndependencies = ["pydantic>=2.0"]\n',
        '[project]\nname = "omnimarket"\ndependencies = ["pydantic>=2.12"]\n',
        (_consumer("omnibase_infra", _infra(">=0.47.31", None)),),
    )
    assert status == "PASS"


def test_an_undeclared_repository_is_an_error() -> None:
    status, _ = _run(None, _market(">=0.47.44"), (), repo="not_a_registry_repo")
    assert status == "ERROR"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0.47.44", (0, 47, 44)),
        ("0.48.0", (0, 48)),
        ("1.0rc1", (1,)),
        ("v2.3", (2, 3)),
    ],
)
def test_parse_version(text: str, expected: tuple[int, ...]) -> None:
    assert parse_version(text) == expected


def test_declared_floors_take_the_highest_lower_bound_across_tables() -> None:
    floors = declared_floors(
        _infra(">=0.47.31,<0.48.0", "0.47.39"), _rules()[checker.RULE_FLOOR]
    )
    assert floors["omnibase-core"].floor == (0, 47, 39)


# --- planted violations, clean twins, every parameter ------------------------

FIXTURE_CASES = {
    rule: (f"violation_{rule}.yaml", f"clean_{rule}.yaml")
    for rule in (checker.RULE_FLOOR, checker.RULE_REPO, checker.RULE_UNPARSABLE)
}


def _facts(fixture: str) -> ModelVersionFloorCheckInput:
    return ModelVersionFloorCheckInput.model_validate(
        yaml.safe_load((FIXTURES / fixture).read_text())
    )


def _fixture_issues(
    fixture: str, contract: ModelValidatorSubcontract | None = None
) -> tuple[checker.ModelValidationIssue, ...]:
    return check_version_floor_consumers(_facts(fixture), _rules(contract))


@pytest.mark.parametrize(("rule_id", "files"), sorted(FIXTURE_CASES.items()))
def test_planted_violation_yields_exactly_one_issue_and_clean_yields_none(
    rule_id: str, files: tuple[str, str]
) -> None:
    violation, clean = files
    assert [i.code for i in _fixture_issues(violation)] == [rule_id]
    assert _fixture_issues(clean) == ()


@pytest.mark.parametrize("rule_id", sorted(FIXTURE_CASES))
def test_disabling_a_rule_row_clears_its_fixture(rule_id: str) -> None:
    contract = _contract()
    rows = [
        r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
        for r in contract.rules
    ]
    disabled = contract.model_copy(update={"rules": rows})
    assert _fixture_issues(FIXTURE_CASES[rule_id][0], disabled) == ()


# Every parameter has a control: operators and patterns clear a finding;
# remediation and message templates change the emitted issue's public verdict.
CONTROLS: dict[tuple[str, str], object] = {
    (checker.RULE_FLOOR, "name_pattern"): "(?!)",
    (checker.RULE_FLOOR, "clause_pattern"): "(?!)",
    (checker.RULE_FLOOR, "lower_operators"): [],
    (checker.RULE_FLOOR, "upper_operators"): [],
    (checker.RULE_FLOOR, "remediation"): "Land the consumer change first.",
    (checker.RULE_REPO, "message_template"): "Unknown repository: {repo}",
    (checker.RULE_UNPARSABLE, "message_template"): "Invalid TOML: {repo}: {error}",
}


def test_every_parameter_of_every_rule_row_has_a_control() -> None:
    assert {
        (r.rule_id, key) for r in _contract().rules for key in (r.parameters or {})
    } == set(CONTROLS)


@pytest.mark.parametrize(("rule_id", "key"), sorted(CONTROLS))
def test_mutating_a_parameter_changes_the_verdict(rule_id: str, key: str) -> None:
    contract = _contract()
    rows = [
        r.model_copy(
            update={
                "parameters": {**(r.parameters or {}), key: CONTROLS[(rule_id, key)]}
            }
        )
        if r.rule_id == rule_id
        else r
        for r in contract.rules
    ]
    mutated = contract.model_copy(update={"rules": rows})
    fixture = FIXTURE_CASES[rule_id][0]
    before = _fixture_issues(fixture)
    after = _fixture_issues(fixture, mutated)
    assert len(before) == 1
    assert before != after
    if key in ("name_pattern", "clause_pattern", "lower_operators", "upper_operators"):
        assert after == ()
    elif key == "remediation":
        assert after[0].suggestion == CONTROLS[(rule_id, key)]
    else:
        assert before[0].message != after[0].message


@pytest.mark.parametrize(("rule_id", "key"), sorted(CONTROLS))
def test_invalid_contract_fails_instead_of_passing(rule_id: str, key: str) -> None:
    rules = _rules()
    rules[rule_id] = rules[rule_id].model_copy(update={"parameters": {}})
    with pytest.raises(ModelOnexError, match="parameters"):
        check_version_floor_consumers(_facts(FIXTURE_CASES[rule_id][0]), rules)


def test_checker_is_pure_over_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("checker performed I/O")

    request = _facts(FIXTURE_CASES[checker.RULE_FLOOR][0])
    rules = _rules()
    with monkeypatch.context() as patched:
        patched.setattr("builtins.open", refuse)
        patched.setattr(Path, "read_text", refuse)
        patched.setattr(subprocess, "run", refuse)
        issues = check_version_floor_consumers(request, rules)
    assert [i.code for i in issues] == [checker.RULE_FLOOR]


@pytest.mark.parametrize("which", ["head_pyproject", "base_pyproject"])
def test_unparsable_changed_repository_is_an_error(which: str) -> None:
    request = _facts(FIXTURE_CASES[checker.RULE_FLOOR][1])
    request = request.model_copy(update={which: "[project"})
    [issue] = check_version_floor_consumers(request, _rules())
    assert issue.code == checker.RULE_UNPARSABLE
    assert "does not parse" in issue.message


def test_unparsable_consumer_blocks_a_raise() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (_consumer("omnibase_infra", "[project"),),
    )
    assert status == "FAIL"
    assert "has a pyproject.toml that does not parse" in messages[0]


def test_missing_base_pyproject_counts_as_a_raise() -> None:
    assert (
        _run(None, _market(">=0.47.44"), (_consumer("omnibase_infra", None),))[0]
        == "FAIL"
    )


def test_sibling_owner_is_not_its_own_consumer() -> None:
    assert _run(
        _market(">=0.47.39"), _market(">=0.47.44"), (_consumer("omnibase_core", None),)
    ) == ("PASS", [])


@pytest.mark.parametrize(
    "table",
    [
        "[project]\ndependencies = [\"OmniBase_Core[extra]>=0.47.44; python_version > '3'\"]",
        '[project.optional-dependencies]\nextra = ["omnibase-core>=0.47.44"]',
        '[dependency-groups]\ndev = [{include-group = "other"}, "omnibase-core>=0.47.44"]',
        '[tool.uv]\ndev-dependencies = ["omnibase-core>=0.47.44"]',
        '[tool.uv]\noverride-dependencies = ["omnibase-core>=0.47.44"]',
        '[tool.uv]\nconstraint-dependencies = ["omnibase-core>=0.47.44"]',
    ],
)
def test_declared_floors_cover_every_requirement_table(table: str) -> None:
    assert declared_floors(table, _rules()[checker.RULE_FLOOR])[
        "omnibase-core"
    ].floor == (0, 47, 44)


@pytest.mark.parametrize(
    ("specifier", "version", "expected"),
    [
        ("===0.47.44", "0.47.44", True),
        ("===0.47.39", "0.47.44", False),
        ("==0.47.*", "0.47.44", True),
        ("==0.47.*", "0.48.1", False),
        ("<=0.47.44", "0.47.44", True),
        ("<0.47.44", "0.47.44", False),
        ("~=0.47.39", "0.47.44", True),
        ("~=0.47.39", "0.48.1", False),
        ("~=1", "2", True),
        ("<=garbage", "1", True),
        ("!=0.47.44", "0.47.44", True),
        (">0.47.44", "0.47.44", True),
    ],
)
def test_admits_preserves_existing_upper_bound_semantics(
    specifier: str, version: str, expected: bool
) -> None:
    assert (
        checker._admits(specifier, parse_version(version), _rules()[checker.RULE_FLOOR])
        is expected
    )


def test_direct_urls_and_invalid_requirements_have_no_floor() -> None:
    source = '[project]\ndependencies = ["omnibase-core @ https://example.test/core.whl", "!!!"]'
    assert (
        declared_floors(source, _rules()[checker.RULE_FLOOR])["omnibase-core"].floor
        is None
    )
    assert parse_version("unknown") == ()
    assert checker.normalize_name("OmniBase_Core.Name") == "omnibase-core-name"


# --- the entry over directories, read-only git responses and as a module -------


def _entry_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "omnimarket"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(_market(">=0.47.44"))
    return repo


@pytest.fixture
def git_reads(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Simulate origin clones without running any git command that changes state."""

    def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if args[0] == "rev-parse":
            if "--git-common-dir" in args:
                return subprocess.CompletedProcess(
                    args, 0, str(root / ".git") + "\n", ""
                )
            return subprocess.CompletedProcess(
                args, int(args[-1] == "no-such-ref^{commit}"), "", ""
            )
        if args[0] == "merge-base":
            return subprocess.CompletedProcess(args, 0, "base\n", "")
        if args[0] == "symbolic-ref":
            return subprocess.CompletedProcess(args, 0, "origin/dev\n", "")
        if args[0] == "cat-file":
            return subprocess.CompletedProcess(
                args, int(not (root / "pyproject.toml").exists()), "", ""
            )
        assert args[0] == "show"
        text = (
            _market(">=0.47.39")
            if root.name == "omnimarket"
            else (root / "pyproject.toml").read_text()
        )
        return subprocess.CompletedProcess(args, 0, text, "")

    mocked = Mock(side_effect=run)
    monkeypatch.setattr(cli, "_git", mocked)
    return mocked


def _consumers(tmp_path: Path, pin: str) -> Path:
    registry = tmp_path / "registry"
    for entry in LAYER_MAP.repos:
        (registry / entry.repo).mkdir(parents=True)
    (registry / "omnibase_infra" / "pyproject.toml").write_text(_infra(">=0.47.0", pin))
    return registry


@pytest.mark.parametrize(("pin", "code"), [("0.47.39", 1), ("0.47.44", 0)])
def test_floor_cli_checks_origin_consumers(
    tmp_path: Path,
    git_reads: Mock,
    capsys: pytest.CaptureFixture[str],
    pin: str,
    code: int,
) -> None:
    repo = _entry_repo(tmp_path)
    registry = _consumers(tmp_path, pin)
    assert (
        cli.ValidatorVersionFloorConsumers.main(
            [
                "--root",
                str(repo),
                "--repo",
                "omnimarket",
                "--base-ref",
                "base",
                "--consumers-root",
                str(registry),
            ]
        )
        == code
    )
    out = capsys.readouterr().out
    if code:
        assert (
            "FAIL: omnibase_infra: omnimarket raises its omnibase-core floor 0.47.39 -> 0.47.44"
            in out
        )
        assert "origin/dev" in out
        assert "omnidash" not in out
    else:
        assert "OK:" in out
    assert any(
        call.args[1:] == ("show", "base:pyproject.toml")
        for call in git_reads.call_args_list
    )
    assert any(
        call.args[1:] == ("show", "origin/dev:pyproject.toml")
        for call in git_reads.call_args_list
    )


def test_floor_cli_ignores_staged_files_that_are_not_pyproject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    no_io = Mock(side_effect=AssertionError("non-pyproject staged files triggered I/O"))
    monkeypatch.setattr(cli, "load_layer_map", no_io)
    monkeypatch.setattr(cli, "_git", no_io)
    assert cli.ValidatorVersionFloorConsumers.main(["--root", str(tmp_path), "src/a.py"]) == 0
    no_io.assert_not_called()


def test_floor_cli_refuses_a_missing_base_ref(
    tmp_path: Path, git_reads: Mock, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _entry_repo(tmp_path)
    assert (
        cli.ValidatorVersionFloorConsumers.main(
            ["--root", str(repo), "--repo", "omnimarket", "--base-ref", "no-such-ref"]
        )
        == 1
    )
    assert "ERROR: " in capsys.readouterr().out


def test_floor_cli_passes_without_a_pyproject(tmp_path: Path) -> None:
    assert cli.ValidatorVersionFloorConsumers.main(["--root", str(tmp_path)]) == 0


def test_entry_accepts_staged_pyproject_and_infers_repository(
    tmp_path: Path, git_reads: Mock
) -> None:
    repo = _entry_repo(tmp_path)
    registry = _consumers(tmp_path, "0.47.44")
    assert (
        cli.ValidatorVersionFloorConsumers.main(
            [
                "--root",
                str(repo),
                "--consumers-root",
                str(registry),
                "some/pyproject.toml",
            ]
        )
        == 0
    )


def test_validator_base_entry_returns_the_checker_issue(
    tmp_path: Path, git_reads: Mock
) -> None:
    repo = _entry_repo(tmp_path)
    registry = _consumers(tmp_path, "0.47.39")
    validator = ValidatorVersionFloorConsumers(
        repository="omnimarket", root=repo, base_ref="base", consumers_root=registry
    )
    result = validator.validate(repo)
    assert [i.code for i in result.issues] == [checker.RULE_FLOOR]
    assert validator.get_exit_code(result) == 1


def test_default_consumers_root_uses_canonical_clone_parent(
    tmp_path: Path, git_reads: Mock
) -> None:
    assert cli._default_consumers_root(tmp_path / "omnimarket") == tmp_path


def test_default_consumers_root_falls_back_when_git_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli, "_git", Mock(return_value=subprocess.CompletedProcess([], 1, "", ""))
    )
    assert cli._default_consumers_root(tmp_path / "omnimarket") == tmp_path


def test_base_ref_tries_each_default_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 1, "", ""),
            subprocess.CompletedProcess([], 1, "", ""),
            subprocess.CompletedProcess([], 0, "base\n", ""),
        ]
    )
    monkeypatch.setattr(cli, "_git", git)
    assert cli._base_ref(tmp_path, None) == ("base", None)
    assert [c.args[3] for c in git.call_args_list] == [
        "origin/HEAD",
        "origin/dev",
        "origin/main",
    ]


def test_base_ref_fails_when_no_merge_base_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli, "_git", Mock(return_value=subprocess.CompletedProcess([], 1, "", ""))
    )
    base, error = cli._base_ref(tmp_path, None)
    assert base is None
    assert error and "pass --base-ref" in error


@pytest.mark.parametrize(
    ("responses", "expected"),
    [
        ([(1, "")], None),
        ([(0, "")], None),
        ([(0, "origin/dev\n"), (1, "")], ""),
        ([(0, "origin/dev\n"), (0, ""), (1, "")], None),
        ([(0, "origin/dev\n"), (0, ""), (0, "text")], "text"),
    ],
)
def test_read_consumer_distinguishes_no_python_from_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    responses: list[tuple[int, str]],
    expected: str | None,
) -> None:
    (tmp_path / "consumer").mkdir()
    monkeypatch.setattr(
        cli,
        "_git",
        Mock(
            side_effect=[
                subprocess.CompletedProcess([], code, out, "")
                for code, out in responses
            ]
        ),
    )
    assert cli._read_consumer(tmp_path, "consumer").pyproject == expected


def test_read_consumer_missing_clone_is_unreadable(tmp_path: Path) -> None:
    consumer = cli._read_consumer(tmp_path, "absent")
    assert consumer.pyproject is None
    assert consumer.ref == "absent"


def _module(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_version_floor_consumers",
            *argv,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_module_passes_non_pyproject_staged_files(tmp_path: Path) -> None:
    assert _module("--root", str(tmp_path), "README.md").returncode == 0


def test_module_passes_repository_without_pyproject(tmp_path: Path) -> None:
    assert _module("--root", str(tmp_path)).returncode == 0


def test_module_fails_on_missing_base_ref(tmp_path: Path) -> None:
    repo = _entry_repo(tmp_path)
    result = _module(
        "--root", str(repo), "--repo", "omnimarket", "--base-ref", "no-such-ref"
    )
    assert result.returncode == 1
    assert "ERROR:" in result.stdout


def test_module_refuses_retired_report_json_flag() -> None:
    assert _module("--report-json", "report.json").returncode == 2
