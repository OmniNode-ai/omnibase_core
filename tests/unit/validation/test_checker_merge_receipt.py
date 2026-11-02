# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the report-only merge-side receipt checker, validator and fact gathering (OMN-21926).

Every cause has a planted fixture and a paired clean one. The rules live in
``validation/contracts/merge_receipt.validation.yaml``; the falsifier tests change one declared
value and assert the verdict changes with no code change.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_check_input import (
    ModelMergeReceiptCheckInput,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_check_result import (
    ModelMergeReceiptCheckResult,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_gather_input import (
    ModelMergeReceiptGatherInput,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_pr import (
    ModelMergeReceiptPr,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_record import (
    ModelMergeReceiptRecord,
)
from omnibase_core.nodes.node_merge_receipt_check_compute.handler import (
    NodeMergeReceiptCheckCompute,
)
from omnibase_core.nodes.node_merge_receipt_gather_effect.facts_merge_receipt import (
    percentile,
    slot_seconds,
    watcher_facts,
)
from omnibase_core.nodes.node_merge_receipt_gather_effect.handler import (
    NodeMergeReceiptGatherEffect,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_merge_receipt import check_merge_receipt
from omnibase_core.validation.validator_merge_receipt import ValidatorMergeReceipt
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

CONTRACT_PATH = (
    Path(validator_base.__file__).parent / "contracts" / "merge_receipt.validation.yaml"
)
REPO_ROOT = Path(__file__).resolve().parents[3]
HEAD = "a" * 40
EARLIER = "b" * 40
SOURCE = "lab-proof-receipt"


def _contract_data() -> dict[str, Any]:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    assert isinstance(data, dict)
    return data


def _contract(data: dict[str, Any] | None = None) -> ModelValidatorSubcontract:
    return ModelValidatorSubcontract.model_validate(data or _contract_data())


def _pr(**fields: Any) -> ModelMergeReceiptPr:
    base: dict[str, Any] = {
        "repo": "omnimarket",
        "number": 7,
        "head_sha": HEAD,
        "head_ref": "omn-1-x",
        "body": "",
        "changed_paths": ("src/omnimarket/nodes/node_x/handler.py",),
        "receipts": (),
    }
    base.update(fields)
    return ModelMergeReceiptPr(**base)


def _receipt(sha: str = HEAD, **fields: Any) -> ModelMergeReceiptRecord:
    base: dict[str, Any] = {
        "source": SOURCE,
        "sha": sha,
        "repo": "omnimarket",
        "pr_number": 7,
        "branch": "omn-1-x",
    }
    base.update(fields)
    return ModelMergeReceiptRecord(**base)


def _check(
    *prs: ModelMergeReceiptPr, contract: ModelValidatorSubcontract | None = None
) -> ModelMergeReceiptCheckResult:
    return check_merge_receipt(
        ModelMergeReceiptCheckInput(
            source_name="facts.merge-receipt-facts.json",
            pull_requests=prs,
            contract=contract or _contract(),
        )
    )


def test_no_receipt_is_would_refuse() -> None:
    result = _check(_pr())
    assert (result.examined, result.would_refuse) == (1, 1)
    assert result.verdicts[0].causes == ("receipt_missing",)


def test_receipt_at_exact_head_is_not_refused() -> None:
    result = _check(_pr(receipts=(_receipt(),)))
    assert (result.examined, result.would_refuse) == (1, 0)
    assert result.issues == ()


def test_report_only_never_fails() -> None:
    """Every planted violation is reported as a warning and the exit code stays zero."""
    result = _check(
        _pr(),
        _pr(number=8, body="Lab: host x, lane y, ran it"),
        _pr(number=9, receipts=(_receipt(EARLIER, pr_number=9),)),
    )
    assert result.would_refuse == 3
    assert result.issues
    assert all(not issue.severity.is_error_or_above() for issue in result.issues)
    assert result.exit_code == 0
    contract = _contract()
    assert contract.fail_on_error is False
    assert contract.fail_on_warning is False


def test_report_only_never_fails_through_the_validator_entry(tmp_path: Path) -> None:
    facts = {"pull_requests": [_pr().model_dump(mode="json")]}
    path = tmp_path / "open.merge-receipt-facts.json"
    path.write_text(json.dumps(facts), encoding="utf-8")
    validator = ValidatorMergeReceipt()
    result = validator.validate(path)
    assert any(issue.code == "receipt_missing" for issue in result.issues)
    assert validator.get_exit_code(result) == 0


def test_hand_typed_line_not_counted() -> None:
    """A Lab line in the body names the cause and never satisfies the check."""
    typed = "Lab: host h051, lane prepr-1, command ran, observed running at the head"
    result = _check(_pr(body=f"Summary\n\n{typed}\n"))
    assert result.would_refuse == 1
    assert result.verdicts[0].causes == ("receipt_missing", "lab_line_not_receipt")
    clean = _check(_pr(body="Summary only\n"))
    assert clean.verdicts[0].causes == ("receipt_missing",)


def test_hand_typed_line_not_counted_even_when_it_names_the_head() -> None:
    result = _check(_pr(body=f"Lab: slot proof receipt at {HEAD}"))
    assert result.would_refuse == 1


def test_receipt_from_an_undeclared_source_is_not_counted() -> None:
    result = _check(_pr(receipts=(_receipt(source="typed-by-hand"),)))
    assert result.would_refuse == 1


def test_stale_head_receipt() -> None:
    """A receipt whose sha is an earlier head of the same pull request is not counted."""
    result = _check(_pr(receipts=(_receipt(EARLIER),)))
    assert result.would_refuse == 1
    assert result.verdicts[0].causes == ("receipt_missing", "receipt_stale_head")
    assert EARLIER in result.issues[1].message


def test_stale_head_receipt_matched_by_branch_alone() -> None:
    result = _check(_pr(receipts=(_receipt(EARLIER, pr_number=0),)))
    assert "receipt_stale_head" in result.verdicts[0].causes


def test_receipt_of_another_pull_request_is_not_stale_evidence() -> None:
    other = _receipt(EARLIER, pr_number=99, branch="other")
    result = _check(_pr(receipts=(other,)))
    assert result.verdicts[0].causes == ("receipt_missing",)


def test_receipt_of_another_repository_is_not_counted() -> None:
    result = _check(_pr(receipts=(_receipt(repo="omnibase_infra"),)))
    assert result.would_refuse == 1


def test_owner_qualified_repository_receipt_is_counted() -> None:
    result = _check(_pr(receipts=(_receipt(repo="OmniNode-ai/omnimarket"),)))
    assert result.would_refuse == 0


@pytest.mark.parametrize(
    "paths",
    [
        ("docs/guide.md",),
        ("tests/unit/test_x.py",),
        ("src/pkg/README.md",),
        ("src/pkg/tests/test_y.py",),
        (),
    ],
)
def test_docs_and_tests_only_change_is_not_examined(paths: tuple[str, ...]) -> None:
    result = _check(_pr(changed_paths=paths))
    assert (result.examined, result.would_refuse, result.skipped) == (0, 0, 1)


@pytest.mark.parametrize(
    "path",
    [
        "src/omnimarket/x.py",
        "docker/compose.yml",
        "deploy/k8s/a.yaml",
        "Dockerfile",
        "docker/Dockerfile.runtime",
    ],
)
def test_runtime_paths_are_examined(path: str) -> None:
    assert _check(_pr(changed_paths=(path, "docs/a.md"))).examined == 1


def test_declared_runtime_path_changes_the_verdict_without_a_code_change() -> None:
    pr = _pr(changed_paths=("scripts/run.sh",))
    assert _check(pr).examined == 0
    data = copy.deepcopy(_contract_data())
    row = next(r for r in data["rules"] if r["rule_id"] == "runtime_paths")
    row["parameters"]["runtime_path_patterns"].append("^scripts/")
    assert _check(pr, contract=_contract(data)).examined == 1


def test_declared_machine_source_changes_the_verdict_without_a_code_change() -> None:
    pr = _pr(receipts=(_receipt(source="other-writer"),))
    assert _check(pr).would_refuse == 1
    data = copy.deepcopy(_contract_data())
    row = next(r for r in data["rules"] if r["rule_id"] == "receipt_sources")
    row["parameters"]["machine_sources"].append("other-writer")
    assert _check(pr, contract=_contract(data)).would_refuse == 0


def test_declared_cause_text_and_enabled_flag_change_the_output() -> None:
    data = copy.deepcopy(_contract_data())
    row = next(r for r in data["rules"] if r["rule_id"] == "receipt_missing")
    row["parameters"]["message"] = "custom {repo}#{number}"
    assert (
        _check(_pr(), contract=_contract(data)).issues[0].message
        == "custom omnimarket#7"
    )
    row["enabled"] = False
    muted = _check(_pr(), contract=_contract(data))
    assert muted.issues == ()
    assert muted.would_refuse == 1


def test_contract_missing_a_required_parameter_is_refused() -> None:
    data = copy.deepcopy(_contract_data())
    row = next(r for r in data["rules"] if r["rule_id"] == "lab_line_not_receipt")
    del row["parameters"]["lab_line_pattern"]
    with pytest.raises(ModelOnexError):
        _check(_pr(), contract=_contract(data))


def test_node_handler_returns_the_checker_result() -> None:
    request = ModelMergeReceiptCheckInput(
        source_name="facts.merge-receipt-facts.json",
        pull_requests=(_pr(),),
        contract=_contract(),
    )
    assert NodeMergeReceiptCheckCompute().handle(request) == check_merge_receipt(
        request
    )


def _state(**ci: Any) -> dict[str, Any]:
    return {
        "prs": {
            "omnimarket#7": {
                "facts": {
                    "repo": "omnimarket",
                    "number": 7,
                    "state": "OPEN",
                    "base": "dev",
                    "head_sha": HEAD,
                    "head_ref": "omn-1-x",
                    "body": "Lab: typed",
                },
                "ci": ci or None,
            },
            "omnimarket#8": {
                "facts": {"repo": "omnimarket", "number": 8, "state": "MERGED"},
                "ci": None,
            },
            "omniclaude#9": {
                "facts": {"repo": "omniclaude", "number": 9, "state": "OPEN"},
                "ci": None,
            },
        }
    }


def _paths(*_: Any) -> tuple[str, ...]:
    return ("src/a.py",)


def test_watcher_facts_reads_a_passing_receipt_check_at_the_state_sha() -> None:
    state = _state(
        sha=HEAD, detail=[[SOURCE, "1", "t"], ["CI Summary", "2", "t"]], red=[]
    )
    facts, unreadable = watcher_facts(state, ["omnimarket"], [SOURCE], _paths)
    assert unreadable == ()
    assert [f.number for f in facts] == [7]
    assert _check(*facts).would_refuse == 0


def test_watcher_facts_does_not_count_a_failed_receipt_check() -> None:
    state = _state(sha=HEAD, detail=[[SOURCE, "1", "t"]], red=[SOURCE])
    facts, _ = watcher_facts(state, ["omnimarket"], [SOURCE], _paths)
    assert facts[0].receipts == ()
    assert _check(*facts).would_refuse == 1


def test_watcher_facts_state_sha_other_than_head_is_a_stale_receipt() -> None:
    state = _state(sha=EARLIER, detail=[[SOURCE, "1", "t"]], red=[])
    facts, _ = watcher_facts(state, ["omnimarket"], [SOURCE], _paths)
    assert _check(*facts).verdicts[0].causes == (
        "receipt_missing",
        "receipt_stale_head",
        "lab_line_not_receipt",
    )


def test_watcher_facts_names_pull_requests_whose_paths_cannot_be_read() -> None:
    facts, unreadable = watcher_facts(
        _state(), ["omnimarket"], [SOURCE], lambda *_: None
    )
    assert facts == ()
    assert unreadable == ("omnimarket#7",)


LEDGER = [
    "2026-11-02T00:00:00Z | HOLD | lane=a | id=h1 | surface=prepr-1-201 | until=x | text",
    "2026-11-02T00:10:00Z | RELEASE | lane=a | re=h1 | surface=prepr-1-201 | result=PASS | text",
    "2026-11-02T01:00:00Z | HOLD | lane=b | id=h2 | until=x | text",
    "2026-11-02T01:30:00Z | RELEASE | lane=b | re=h2 | surface=prepr-2-201 | text",
    "2026-11-02T02:00:00Z | HOLD | lane=c | id=h3 | surface=prepr-slots-201 | text",
    "2026-11-02T03:00:00Z | RELEASE | lane=c | re=h3 | surface=prepr-slots-201 | text",
    "2026-11-02T04:00:00Z | HOLD | lane=d | id=h4 | surface=dev-lane | text",
    "2026-11-02T04:05:00Z | RELEASE | lane=d | re=h4 | surface=dev-lane | text",
    "2026-11-02T05:00:00Z | HOLD | lane=e | id=h5 | surface=prepr-1-201 | text",
    "2026-11-02T06:00:00Z | RELEASE | lane=zz | re=missing | surface=prepr-1-201 | text",
]


def test_slot_seconds_pairs_hold_and_release_on_a_declared_surface() -> None:
    row = next(r for r in _contract_data()["rules"] if r["rule_id"] == "slot_time")
    pattern = row["parameters"]["surface_pattern"]
    assert slot_seconds(LEDGER, pattern) == [600.0, 1800.0]


def test_slot_surface_is_a_declared_value() -> None:
    assert slot_seconds(LEDGER, "^dev-lane$") == [300.0]


def test_percentile_is_nearest_rank() -> None:
    values = [float(n) for n in range(1, 11)]
    assert percentile(values, 0.5) == 5.0
    assert percentile(values, 0.9) == 9.0
    assert percentile([7.0], 0.9) == 7.0


def test_no_required_context_changed() -> None:
    """Neither the required-check manifest nor any workflow names the report-only check."""
    manifest = yaml.safe_load(
        (REPO_ROOT / ".github" / "required-checks.yaml").read_text("utf-8")
    )
    required = [g for g in manifest["gates"] if g.get("mode") == "REQUIRED"]
    assert required
    forbidden = ("merge_receipt", "merge-receipt", "MergeReceipt")
    assert not [g for g in required if any(word in json.dumps(g) for word in forbidden)]
    for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        assert not any(w in path.read_text("utf-8") for w in forbidden), path.name
    for name in (".pre-commit-config.yaml", ".github/required-checks.yaml"):
        assert not any(w in (REPO_ROOT / name).read_text("utf-8") for w in forbidden), (
            name
        )


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env(),
    )
    return done.stdout.strip()


def test_gather_effect_reads_state_ledger_and_clone_then_check_reports(
    tmp_path: Path,
) -> None:
    """Drive the EFFECT node over a real git clone and the COMPUTE node over its output."""
    clone = tmp_path / "clones" / "omnimarket"
    clone.mkdir(parents=True)
    _git(clone, "init", "-q", "-b", "dev")
    _git(clone, "config", "user.email", "t@example.invalid")
    _git(clone, "config", "user.name", "t")
    (clone / "README.md").write_text("x", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "-m", "base")
    _git(clone, "update-ref", "refs/remotes/origin/dev", "HEAD")
    (clone / "src").mkdir()
    (clone / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "-m", "change")
    head = _git(clone, "rev-parse", "HEAD")
    state = _state(sha=head, detail=[], red=[])
    state["prs"]["omnimarket#7"]["facts"]["head_sha"] = head
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    ledger = tmp_path / "ledger.md"
    ledger.write_text("\n".join(LEDGER), encoding="utf-8")
    output = NodeMergeReceiptGatherEffect().handle(
        ModelMergeReceiptGatherInput(
            state_path=state_path,
            clone_root=tmp_path / "clones",
            ledger_paths=(ledger,),
            repos=("omnimarket",),
            check_names=(SOURCE,),
            surface_pattern="^prepr-[0-9]+-201$",
        )
    )
    assert output.unreadable == ()
    assert output.pull_requests[0].changed_paths == ("src/a.py",)
    assert output.slot_seconds == (600.0, 1800.0)
    report = NodeMergeReceiptCheckCompute().handle(
        ModelMergeReceiptCheckInput(
            source_name="open.merge-receipt-facts.json",
            pull_requests=output.pull_requests,
            contract=_contract(),
        )
    )
    assert (report.examined, report.would_refuse) == (1, 1)


def test_gather_effect_names_an_unknown_head_as_unreadable(tmp_path: Path) -> None:
    clone = tmp_path / "clones" / "omnimarket"
    clone.mkdir(parents=True)
    _git(clone, "init", "-q", "-b", "dev")
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(_state()), encoding="utf-8")
    ledger = tmp_path / "ledger.md"
    ledger.write_text("", encoding="utf-8")
    output = NodeMergeReceiptGatherEffect().handle(
        ModelMergeReceiptGatherInput(
            state_path=state_path,
            clone_root=tmp_path / "clones",
            ledger_paths=(ledger,),
            repos=("omnimarket",),
            check_names=(SOURCE,),
            surface_pattern="^prepr-[0-9]+-201$",
        )
    )
    assert output.unreadable == ("omnimarket#7",)
    assert output.pull_requests == ()
