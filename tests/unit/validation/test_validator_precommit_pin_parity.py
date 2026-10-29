# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-driven pin parity, including the consumer line-13 regression.

No Redpanda overlay pair exists for this validator runtime yet.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from omnibase_core.models.precommit_pins.model_precommit_pin_parity_input import (
    ModelPrecommitPinParityInput,
)
from omnibase_core.models.precommit_pins.model_precommit_pin_rules import (
    ModelPrecommitPinRules,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time import (
    ModelPrecommitRevTime,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time_result import (
    ModelPrecommitRevTimeResult,
)
from omnibase_core.nodes.node_precommit_rev_time_effect.runtime_precommit_pin_parity import (
    build_container,
    run,
)
from omnibase_core.validation.checker_precommit_pin_parity import (
    check_precommit_pin_parity,
    extract_pins,
)
from omnibase_core.validation.validator_precommit_pin_parity import (
    ValidatorPrecommitPinParity,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parents[2] / "fixtures/validation/precommit_pin_parity"
ROOT = Path(__file__).parents[3]
CORE = "https://github.com/OmniNode-ai/omnibase_core"


def rules():
    return ModelPrecommitPinRules.from_contract(
        ValidatorPrecommitPinParity(MemoryRevTimes().handle).contract
    )


def facts(source, times=None):
    pins = extract_pins(source)
    if times is None:
        times = tuple(
            ModelPrecommitRevTime(repo=p.repo, rev=p.rev, committed_at=i + 1)
            for i, p in enumerate(pins)
        )
    return ModelPrecommitPinParityInput(
        rules=rules(), path=".pre-commit-config.yaml", source=source, rev_times=times
    )


@pytest.mark.parametrize("rule_id", ["older_than_newest_pin", "unresolved_rev_time"])
@pytest.mark.parametrize("violation", [True, False])
def test_pure_fixtures(rule_id, violation):
    source = (
        FIXTURES / f"{'violation' if violation else 'clean'}_{rule_id}.yaml"
    ).read_text()
    request = facts(
        source, () if rule_id == "unresolved_rev_time" and violation else None
    )
    if rule_id == "unresolved_rev_time" and violation:
        request = request.model_copy(
            update={
                "rev_times": (
                    ModelPrecommitRevTime(repo=CORE, rev="new", committed_at=2),
                )
            }
        )
    with (
        patch("builtins.open", side_effect=AssertionError("I/O")),
        patch.object(Path, "read_text", side_effect=AssertionError("I/O")),
        patch.object(Path, "exists", side_effect=AssertionError("I/O")),
    ):
        issues = check_precommit_pin_parity(request)
    assert [i.code for i in issues] == ([rule_id] if violation else [])


def test_ac2_consumer():
    stale = (FIXTURES / "consumer_line13_d7ed23f1.yaml").read_text()
    pins = extract_pins(stale)
    assert pins[0].rev.startswith("d7ed23f1")
    times = tuple(
        ModelPrecommitRevTime(repo=p.repo, rev=p.rev, committed_at=i)
        for i, p in enumerate(pins)
    )
    [issue] = check_precommit_pin_parity(facts(stale, times))
    assert issue.line_number == 13
    assert issue.code == "older_than_newest_pin"
    assert not check_precommit_pin_parity(
        facts((FIXTURES / "consumer_line13_current_pin.yaml").read_text(), times)
    )


def test_hook_entry():
    for filename in (".pre-commit-config.yaml", ".pre-commit-hooks.yaml"):
        data = yaml.safe_load((ROOT / filename).read_text())
        hooks = (
            [h for r in data["repos"] for h in r["hooks"]]
            if isinstance(data, dict)
            else data
        )
        [hook] = [h for h in hooks if h["id"] == "check-precommit-pin-parity"]
        assert (
            "python -m omnibase_core.nodes.node_precommit_rev_time_effect.runtime_precommit_pin_parity"
            in hook["entry"]
        )
        assert hook["pass_filenames"] is True


class MemoryRevTimes:
    def handle(self, request):
        return ModelPrecommitRevTimeResult(
            rev_times=tuple(
                ModelPrecommitRevTime(
                    repo=p.repo, rev=p.rev, committed_at={"old": 1, "new": 2}[p.rev]
                )
                for p in request.pins
            )
        )


def test_runtime_container_and_golden(tmp_path):
    source = (FIXTURES / "violation_older_than_newest_pin.yaml").read_text()
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text(source)
    container = build_container(rev_time_source=MemoryRevTimes())
    resolutions = []
    original = container.get_service

    def resolve(token, service_name=None):
        resolutions.append(token.__name__)
        return original(token, service_name)

    with patch.object(container, "get_service", side_effect=resolve):
        out = tmp_path / "report.json"
        assert run([str(config), "--report-json", str(out)], container=container) == 1
    assert resolutions == [
        "NodePrecommitRevTimeEffect",
        "NodeValidationReportWriteEffect",
    ]
    report = json.loads(out.read_text())
    report["report_id"] = "<run_id>"
    report["provenance"]["generated_at"] = "<timestamp>"
    for finding in report["findings"]:
        finding["location"] = finding["location"].replace(str(tmp_path), "<root>")
        finding["message"] = finding["message"].replace(str(tmp_path), "<root>")
    assert report == json.loads((FIXTURES / "golden_report.json").read_text())


def _contract_data():
    return yaml.safe_load(
        (
            ROOT
            / "src/omnibase_core/validation/contracts/precommit_pin_parity.validation.yaml"
        ).read_text()
    )["validation"]


PARAMETERS = [
    (row["rule_id"], key)
    for row in _contract_data()["rules"]
    for key in row["parameters"]
]


@pytest.mark.parametrize(("rule_id", "key"), PARAMETERS)
def test_every_contract_parameter_controls_behavior(
    rule_id, key, tmp_path, monkeypatch
):
    """Mutate every YAML parameter; an inert/dead parameter must fail this test."""
    import sqlite3

    from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
        ModelValidatorSubcontract,
    )
    from omnibase_core.models.precommit_pins.model_precommit_rev_time_request import (
        ModelPrecommitRevTimeRequest,
    )
    from omnibase_core.nodes.node_precommit_rev_time_effect.handler import (
        NodePrecommitRevTimeEffect,
    )

    data = _contract_data()
    baseline = ModelPrecommitPinRules.from_contract(
        ModelValidatorSubcontract.model_validate(data)
    )
    row = next(row for row in data["rules"] if row["rule_id"] == rule_id)
    replacements = {
        "hook_repos": ["https://example.invalid/other"],
        "remediation": "changed remediation",
        "older_message": "changed older message",
        "unresolved_message": "changed unresolved message",
        "git_timeout_seconds": 0.001,
        "cache_home_default": str(tmp_path / "absent"),
        "cache_index_file": "absent.db",
        "cache_index_table": "absent_table",
        "cache_repo_column": "absent_repo",
        "cache_ref_column": "absent_ref",
        "cache_path_column": "absent_path",
        "history_repo": str(tmp_path / "absent_repo"),
    }
    row["parameters"][key] = replacements[key]
    changed = ModelPrecommitPinRules.from_contract(
        ModelValidatorSubcontract.model_validate(data)
    )
    source = (FIXTURES / "violation_older_than_newest_pin.yaml").read_text()
    request = facts(source)
    if rule_id == "rev_time_lookup":
        monkeypatch.setenv("HOME", str(tmp_path))
        home = Path(baseline.lookup.cache_home_default).expanduser()
        home.mkdir(parents=True)
        with sqlite3.connect(home / baseline.lookup.cache_index_file) as db:
            db.execute("CREATE TABLE repos(repo TEXT, ref TEXT, path TEXT)")
            db.executemany(
                "INSERT INTO repos VALUES (?, ?, ?)",
                [(CORE, rev, rev) for rev in ("old", "new")],
            )

        def stamp(repo, rev, timeout):
            return (
                {"old": 1, "new": 2}.get(repo.name)
                if timeout == baseline.lookup.git_timeout_seconds
                else None
            )

        node = NodePrecommitRevTimeEffect()
        monkeypatch.setattr(node, "_commit_time", stamp)

        def evaluate(policy):
            result = node.handle(
                ModelPrecommitRevTimeRequest(
                    pins=extract_pins(source), parameters=policy.lookup
                )
            )
            return check_precommit_pin_parity(
                request.model_copy(
                    update={"rules": policy, "rev_times": result.rev_times}
                )
            )

        before, after = evaluate(baseline), evaluate(changed)
    else:
        if key == "unresolved_message" or rule_id == "unresolved_rev_time":
            request = request.model_copy(
                update={
                    "rev_times": (
                        ModelPrecommitRevTime(repo=CORE, rev="new", committed_at=2),
                    )
                }
            )
        before = check_precommit_pin_parity(
            request.model_copy(update={"rules": baseline})
        )
        after = check_precommit_pin_parity(
            request.model_copy(update={"rules": changed})
        )
    assert before != after


@pytest.mark.parametrize(("rule_id", "key"), PARAMETERS)
@pytest.mark.parametrize("invalid", ["missing", "unknown"])
def test_invalid_parameters_fail_at_contract_load(rule_id, key, invalid):
    from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
        ModelValidatorSubcontract,
    )

    data = _contract_data()
    row = next(row for row in data["rules"] if row["rule_id"] == rule_id)
    if invalid == "missing":
        del row["parameters"][key]
    else:
        row["parameters"]["unknown_parameter"] = "invalid"
    contract = ModelValidatorSubcontract.model_validate(data)
    with pytest.raises(ValueError):
        ValidatorPrecommitPinParity(MemoryRevTimes().handle, contract)


@pytest.mark.parametrize(
    "source",
    ["", "- a\n- b\n", "repos: 3\n", "repos: [\n", "repos: [3]", "repos: [{repo: x}]"],
)
def test_malformed_configs_fail_closed(source):
    from omnibase_core.errors.model_onex_error import ModelOnexError

    with pytest.raises(ModelOnexError):
        extract_pins(source)


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ("repos: [{repo: local}, {repo: meta}]", 0),
        (f"repos: [{{repo: {CORE}, rev: old}}]", 0),
        (f"repos: [{{repo: {CORE}.git/, rev: old}}, {{repo: {CORE}, rev: new}}]", 1),
        ("repos: [{repo: other, rev: old}, {repo: other, rev: new}]", 0),
        (f"repos: [{{repo: {CORE}, rev: new}}, {{repo: {CORE}, rev: old}}]", 1),
    ],
)
def test_grouping_and_order(source, count):
    times = tuple(
        ModelPrecommitRevTime(repo=CORE, rev=r, committed_at=t)
        for r, t in [("old", 1), ("new", 2)]
    )
    assert len(check_precommit_pin_parity(facts(source, times))) == count


def test_numeric_revs_preserved_and_hooks_named():
    source = f"repos:\n- repo: {CORE}\n  rev: 123\n  hooks: [{{id: alpha}}, {{id: gamma}}]\n- repo: {CORE}\n  rev: 456\n"
    assert extract_pins(source)[0].rev == "123"
    [issue] = check_precommit_pin_parity(facts(source))
    assert "alpha, gamma" in issue.message
    assert issue.line_number == 3


def test_equal_commit_times_pass():
    source = (FIXTURES / "violation_older_than_newest_pin.yaml").read_text()
    times = tuple(
        ModelPrecommitRevTime(repo=CORE, rev=r, committed_at=2) for r in ("old", "new")
    )
    assert not check_precommit_pin_parity(facts(source, times))


@pytest.mark.parametrize("source", [None, "repos: [\n"])
def test_runtime_errors_write_error_report(tmp_path, source):
    config = tmp_path / ".pre-commit-config.yaml"
    if source is not None:
        config.write_text(source)
    output = tmp_path / "error.json"
    assert (
        run(
            [str(config), "--report-json", str(output)],
            container=build_container(rev_time_source=MemoryRevTimes()),
        )
        == 1
    )
    assert json.loads(output.read_text())["overall_status"] == "ERROR"


def test_runtime_converged_and_unrelated_files(tmp_path):
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text((FIXTURES / "clean_older_than_newest_pin.yaml").read_text())
    assert (
        run([str(config)], container=build_container(rev_time_source=MemoryRevTimes()))
        == 0
    )
    # A file no target pattern covers is refused, never reported as a PASS.
    config = tmp_path / "other.yaml"
    config.write_text("not a config")
    output = tmp_path / "other.json"
    assert (
        run(
            [str(config), "--report-json", str(output)],
            container=build_container(rev_time_source=MemoryRevTimes()),
        )
        == 1
    )
    assert json.loads(output.read_text())["overall_status"] == "ERROR"


def test_revision_times_are_scoped_to_each_repository():
    other = "https://example.invalid/second"
    source = "".join(
        [
            f"repos:\n- repo: {CORE}\n  rev: old\n- repo: {CORE}\n  rev: new\n",
            f"- repo: {other}\n  rev: old\n- repo: {other}\n  rev: new\n",
        ]
    )
    policy = rules()
    policy = policy.model_copy(
        update={"older": policy.older.model_copy(update={"hook_repos": (CORE, other)})}
    )
    times = tuple(
        ModelPrecommitRevTime(repo=repo, rev=rev, committed_at=stamp)
        for repo, rev, stamp in [
            (CORE, "old", 1),
            (CORE, "new", 2),
            (other, "old", 3),
            (other, "new", 1),
        ]
    )
    request = facts(source, times).model_copy(update={"rules": policy})
    issues = check_precommit_pin_parity(request)
    assert [issue.line_number for issue in issues] == [3, 9]


def test_custom_nested_contract_and_invalid_contract_cli(tmp_path):
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text((FIXTURES / "violation_older_than_newest_pin.yaml").read_text())
    contract = tmp_path / "custom.validation.yaml"
    data = _contract_data()
    data["rules"][0]["parameters"]["hook_repos"] = ["https://example.invalid/other"]
    contract.write_text(
        yaml.safe_dump({"contract_kind": "validation_subcontract", "validation": data})
    )
    container = build_container(rev_time_source=MemoryRevTimes())
    assert run([str(config), "--contract", str(contract)], container=container) == 0
    del data["rules"][0]["parameters"]["remediation"]
    contract.write_text(yaml.safe_dump({"validation": data}))
    out = tmp_path / "invalid.json"
    assert (
        run(
            [str(config), "--contract", str(contract), "--report-json", str(out)],
            container=container,
        )
        == 1
    )
    assert json.loads(out.read_text())["overall_status"] == "ERROR"


CANARY_DIR = ROOT / "tests/fixtures/precommit_pin_parity"
FIXTURE_OLD = "1" * 40
FIXTURE_NEW = "2" * 40


def _git(repo: Path, *args: str, stream: str | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        input=stream,
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env(),
    ).stdout.strip()


@pytest.fixture
def history(tmp_path: Path) -> tuple[Path, str, str]:
    """A real history checkout with an older and a newer commit."""
    repo = tmp_path / "history"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    stream = "".join(
        f"commit refs/heads/dev\ncommitter t <t@example.invalid> {stamp} +0000\n"
        f"data 1\nm\nM 100644 inline f.txt\ndata {len(str(stamp))}\n{stamp}\n"
        for stamp in (1_000_000_000, 2_000_000_000)
    )
    _git(repo, "fast-import", "--quiet", stream=stream)
    return repo, _git(repo, "rev-parse", "dev~1"), _git(repo, "rev-parse", "dev")


def _hook_run(args: list[str]) -> int:
    """Run the hook entry exactly as pre-commit does: real effects, no overrides."""
    return run(args)


def test_canary_fixture_named_off_pattern_is_not_a_silent_pass(tmp_path, capsys):
    """The canary run on its own file name printed PASS having checked nothing."""
    out = tmp_path / "report.json"
    canary = CANARY_DIR / "canary_lowered_pin.yaml"
    assert _hook_run([str(canary), "--report-json", str(out)]) == 1
    assert "PASS" not in capsys.readouterr().out
    report = json.loads(out.read_text())
    assert report["overall_status"] == "ERROR"
    assert "not covered by target_patterns" in report["findings"][0]["message"]


@pytest.mark.parametrize("relative", [False, True])
def test_canary_lowered_pin_refused_with_rule_id_converged_admitted(
    tmp_path, monkeypatch, history, relative
):
    """AC3 through the real effect: the lowered pin is refused, the converged config passes."""
    repo, old, new = history
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".pre-commit-config.yaml"
    target = config.name if relative else str(config)
    base = ["--history-repo", str(repo)]

    config.write_text(
        (CANARY_DIR / "canary_lowered_pin.yaml")
        .read_text()
        .replace(FIXTURE_OLD, old)
        .replace(FIXTURE_NEW, new)
    )
    out = tmp_path / "canary.json"
    assert _hook_run([target, *base, "--report-json", str(out)]) == 1
    [finding] = json.loads(out.read_text())["findings"]
    assert finding["rule_id"] == "older_than_newest_pin"
    assert finding["location"].endswith(".pre-commit-config.yaml:6")

    config.write_text(
        (CANARY_DIR / "converged_pins.yaml").read_text().replace(FIXTURE_NEW, new)
    )
    assert _hook_run([target, *base]) == 0
