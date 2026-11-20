# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A paired repository names one tag in its hook rev and its CI workflow together (OMN-26065).

The pre-commit hook rev and the CI workflow tag literal of a repository are one derived
home for the paired repository: the same tag in both reads no finding, the same tag in a
third file reads one, and two literals that differ (drift) read one.
"""

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_first_party_ref_input import (
    ModelFirstPartyRefInput,
)
from omnibase_core.validation.checker_first_party_ref import check_first_party_refs
from omnibase_core.validation.validator_first_party_ref import ValidatorFirstPartyRef

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parents[3] / "fixtures/validation/first_party_ref"
TAG = "dev-20261018024445-b6ee996befa1"
OTHER_TAG = "dev-20261023024445-aaaaaaaaaaaa"
RULE = "first_party_ref_two_homes"


def load(name: str) -> ModelFirstPartyRefInput:
    return ModelFirstPartyRefInput.model_validate(
        json.loads((FIXTURES / name).read_text())
    )


def judge(*files: tuple[str, str]):
    facts = ModelFirstPartyRefInput(
        files=tuple(ModelSourceFile(path=path, source=src) for path, src in files)
    )
    return check_first_party_refs(facts, ValidatorFirstPartyRef().contract)


def hook(repo: str, tag: str) -> tuple[str, str]:
    return (
        ".pre-commit-config.yaml",
        f"repos:\n  - repo: https://github.com/OmniNode-ai/{repo}\n    rev: {tag}\n",
    )


def ci(repo: str, tag: str, name: str = "ci") -> tuple[str, str]:
    return (
        f".github/workflows/{name}.yml",
        f"jobs:\n  a:\n    uses: OmniNode-ai/{repo}/.github/workflows/x.yml@{tag}\n",
    )


def test_hook_rev_and_ci_tag_naming_the_same_core_tag_read_no_finding():
    issues = check_first_party_refs(
        load("clean_first_party_ref_two_homes.json"), ValidatorFirstPartyRef().contract
    )
    assert [i.code for i in issues] == []


def test_the_same_core_tag_in_a_third_file_reads_one_finding():
    issues = check_first_party_refs(
        load("violation_first_party_ref_two_homes.json"),
        ValidatorFirstPartyRef().contract,
    )
    assert [i.code for i in issues] == [RULE]


def test_a_core_tag_that_differs_between_hook_rev_and_ci_reads_one_finding():
    issues = check_first_party_refs(
        load("violation_first_party_ref_drift.json"),
        ValidatorFirstPartyRef().contract,
    )
    assert [i.code for i in issues] == [RULE]
    assert str(issues[0].file_path) == ".github/workflows/ci.yml"
    assert OTHER_TAG in issues[0].message
    assert TAG in issues[0].message


def test_the_same_core_tag_in_two_workflows_and_the_hook_reads_one_finding():
    issues = judge(
        hook("omnibase_core", TAG),
        ci("omnibase_core", TAG, "a"),
        ci("omnibase_core", TAG, "b"),
    )
    assert [i.code for i in issues] == [RULE]


def test_the_same_core_tag_in_a_brief_and_the_hook_reads_one_finding():
    issues = judge(
        hook("omnibase_core", TAG),
        ("briefs/deploy-brief.md", f"Deploy OmniNode-ai/omnibase_core@{TAG}"),
    )
    assert [i.code for i in issues] == [RULE]


def test_two_hook_configs_naming_the_same_core_tag_read_one_finding():
    issues = judge(
        hook("omnibase_core", TAG),
        ("sub/.pre-commit-config.yaml", hook("omnibase_core", TAG)[1]),
    )
    assert [i.code for i in issues] == [RULE]


def test_a_repository_that_is_not_paired_keeps_one_home():
    issues = judge(hook("omnibase_infra", TAG), ci("omnibase_infra", TAG))
    assert [i.code for i in issues] == [RULE]


def test_a_workflow_only_pin_with_no_hook_is_one_home_and_never_drift():
    assert judge(ci("omnibase_core", TAG)) == ()
    assert (
        judge(ci("omnibase_core", OTHER_TAG, "a"), ci("omnibase_core", TAG, "b")) == ()
    )
