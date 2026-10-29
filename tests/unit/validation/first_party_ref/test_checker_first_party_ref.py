# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""First-party reference invariants, including the action-parser bypass corpus."""

from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_first_party_ref_input import (
    ModelFirstPartyRefInput,
)
from omnibase_core.validation.checker_first_party_ref import check_first_party_refs
from omnibase_core.validation.validator_first_party_ref import ValidatorFirstPartyRef

pytestmark = pytest.mark.unit
TAG = "dev-20261018024445-b6ee996befa1"
ORG = "OmniNode-ai"
SHA = "a" * 40


def judge(source: str, path: str = ".github/workflows/ci.yml"):
    validator = ValidatorFirstPartyRef()
    return check_first_party_refs(
        ModelFirstPartyRefInput(files=(ModelSourceFile(path=path, source=source),)),
        validator.contract,
    )


@pytest.mark.parametrize(
    "source",
    [
        f"uses: {ORG}/core@{SHA}",
        f'"uses": {ORG}/core@main',
        f"- {{uses: {ORG}/core@v1.2.3}}",
        f"uses: {ORG}/core@{TAG}#suffix",
    ],
)
def test_first_party_is_always_dev_tag(source):
    assert [i.code for i in judge(source)] == ["first_party_not_dev_tag"]


@pytest.mark.parametrize(
    "source",
    [
        f"uses: {ORG}/core@{TAG} # comment",
        f"- 'uses': '{ORG}/core@{TAG}'",
        f"- {{uses: {ORG}/core@{TAG}}}",
        f"# uses: {ORG}/core@main",
        "uses: ./local",
        f"uses: actions/checkout@{SHA.upper()}",
    ],
)
def test_clean_parser_cases(source):
    assert judge(source) == ()


def test_checker_is_pure():
    contract = ValidatorFirstPartyRef().contract
    facts = ModelFirstPartyRefInput(
        files=(
            ModelSourceFile(
                path=".github/workflows/ci.yml", source=f"uses: {ORG}/core@main"
            ),
        )
    )
    with (
        patch("builtins.open", side_effect=AssertionError("I/O")),
        patch.object(Path, "read_text", side_effect=AssertionError("I/O")),
        patch.object(Path, "exists", side_effect=AssertionError("I/O")),
    ):
        assert len(check_first_party_refs(facts, contract)) == 1


FIXTURES = Path(__file__).parents[3] / "fixtures/validation/first_party_ref"


@pytest.mark.parametrize(
    "rule",
    [
        "first_party_not_dev_tag",
        "third_party_not_sha",
        "cross_repo_ref_not_dev_tag",
        "first_party_source_not_dev_tag",
        "first_party_ref_two_homes",
        "brief_names_release_version",
        "missing_source",
        "wrong_repo",
        "release_pin",
        "stale_pin",
    ],
)
def test_each_rule_fixture_has_exactly_one_issue(rule):
    import json

    contract = ValidatorFirstPartyRef().contract
    bad = ModelFirstPartyRefInput.model_validate(
        json.loads((FIXTURES / f"violation_{rule}.json").read_text())
    )
    good = ModelFirstPartyRefInput.model_validate(
        json.loads((FIXTURES / f"clean_{rule}.json").read_text())
    )
    assert [issue.code for issue in check_first_party_refs(bad, contract)] == [rule]
    assert check_first_party_refs(good, contract) == ()


@pytest.mark.parametrize(("prefix", "count"), [("violation", 1), ("clean", 0)])
def test_planted_git_url_in_workflow(prefix, count):
    issues = judge((FIXTURES / f"{prefix}_workflow_git.yml").read_text())
    assert len(issues) == count
    if issues:
        assert issues[0].code == "cross_repo_ref_not_dev_tag"


@pytest.mark.parametrize(("prefix", "count"), [("violation", 1), ("clean", 0)])
def test_precommit_rev(prefix, count):
    assert (
        len(
            judge(
                (FIXTURES / f"{prefix}_precommit.yaml").read_text(),
                ".pre-commit-config.yaml",
            )
        )
        == count
    )


@pytest.mark.parametrize(
    "ref", ["v4", "main", "1.2.3", SHA[:39], SHA[:7], SHA + "0", TAG, ""]
)
def test_third_party_cases_are_ported(ref):
    assert [issue.code for issue in judge(f"uses: actions/checkout@{ref}")] == [
        "third_party_not_sha"
    ]


@pytest.mark.parametrize("ref", [SHA, "main"])
def test_greedy_tag_policy_does_not_admit_sha_or_main(ref):
    validator = ValidatorFirstPartyRef()
    rules = tuple(
        rule.model_copy(update={"parameters": {**rule.parameters, "tag_pattern": ".*"}})
        if rule.rule_id == "first_party_not_dev_tag"
        else rule
        for rule in validator.contract.rules
    )
    contract = validator.contract.model_copy(update={"rules": rules})
    facts = ModelFirstPartyRefInput(
        files=(
            ModelSourceFile(
                path=".github/workflows/ci.yml", source=f"uses: {ORG}/core@{ref}"
            ),
        )
    )
    assert [issue.code for issue in check_first_party_refs(facts, contract)] == [
        "first_party_not_dev_tag"
    ]


@pytest.mark.parametrize(
    "source",
    [
        'core = {git="https://github.com/OmniNode-ai/omnibase_core.git", rev="'
        + TAG
        + '"}',
        'core = {git="https://github.com/OmniNode-ai/omnibase_core.git", branch="dev"}',
        'core = {git="https://github.com/OmniNode-ai/omnibase_core.git"}',
    ],
)
def test_every_uv_source_key_is_judged(source):
    assert [
        issue.code for issue in judge("[tool.uv.sources]\n" + source, "pyproject.toml")
    ] == ["first_party_source_not_dev_tag"]


@pytest.mark.parametrize(
    "channel",
    [
        '[project]\nname="consumer"\ndependencies=["omnibase-core"]',
        '[project.optional-dependencies]\nspi=["omnibase-core"]',
        '[dependency-groups]\ndev=["omnibase-core", {include-group="other"}]',
        '[tool.uv]\noverride-dependencies=["omnibase-core"]',
        '[tool.uv]\nconstraint-dependencies=["omnibase-core"]',
        '[tool.uv]\ndev-dependencies=["omnibase-core"]',
    ],
)
def test_every_sibling_requirement_channel_needs_source(channel):
    assert [issue.code for issue in judge(channel, "pyproject.toml")] == [
        "missing_source"
    ]


def test_own_distribution_and_external_packages_are_not_siblings():
    assert (
        judge(
            '[project]\nname="omnibase_core"\ndependencies=["omnibase-core==1.0", "pydantic==2.11"]',
            "pyproject.toml",
        )
        == ()
    )


def test_each_additional_file_is_one_issue_and_same_file_repeats_are_clean():
    contract = ValidatorFirstPartyRef().contract

    def file(name):
        return ModelSourceFile(
            path=f".github/workflows/{name}.yml",
            source=f"uses: {ORG}/core@{TAG}\nuses: {ORG}/core@{TAG}",
        )

    assert [
        issue.code
        for issue in check_first_party_refs(
            ModelFirstPartyRefInput(files=(file("a"), file("b"), file("c"))), contract
        )
    ] == ["first_party_ref_two_homes"] * 2


@pytest.mark.parametrize("ref", [SHA, "main", "v1.2.3"])
def test_structured_lab_deploy_refs_are_dev_tags(ref):
    issues = judge(
        f"repository: https://github.com/{ORG}/tools.git\nref: {ref}\n",
        "lab/deploy.yaml",
    )
    assert [issue.code for issue in issues] == ["cross_repo_ref_not_dev_tag"]


def test_brief_refs_participate_in_the_single_home_invariant():
    contract = ValidatorFirstPartyRef().contract
    files = (
        ModelSourceFile(
            path="briefs/deploy-brief.md", source=f"Deploy {ORG}/tools@{TAG}"
        ),
        ModelSourceFile(
            path=".github/workflows/ci.yml", source=f"uses: {ORG}/tools@{TAG}"
        ),
    )
    assert [
        issue.code
        for issue in check_first_party_refs(
            ModelFirstPartyRefInput(files=files), contract
        )
    ] == ["first_party_ref_two_homes"]


def test_known_sha_exception_and_main_warning_parameters_are_not_admitted():
    from pydantic import ValidationError

    contract = ValidatorFirstPartyRef().contract
    for key, value in (("known_exceptions", []), ("first_party_main", "warn")):
        rules = tuple(
            rule.model_copy(update={"parameters": {**rule.parameters, key: value}})
            if rule.rule_id == "first_party_not_dev_tag"
            else rule
            for rule in contract.rules
        )
        with pytest.raises(ValidationError):
            check_first_party_refs(
                ModelFirstPartyRefInput(files=()),
                contract.model_copy(update={"rules": rules}),
            )


def test_markdown_brief_heading_is_prose_not_a_yaml_comment():
    assert [
        issue.code
        for issue in judge("# Deploy core v1.2.3\n", "briefs/deploy-brief.md")
    ] == ["brief_names_release_version"]


@pytest.mark.parametrize(
    "text",
    [
        '"cross_repo_ref": "OmniNode-ai/tools@main"',
        "{cross_repo_ref: OmniNode-ai/tools@main}",
    ],
)
def test_structured_required_checks_keys(text):
    assert [issue.code for issue in judge(text, ".github/required-checks.yaml")] == [
        "cross_repo_ref_not_dev_tag"
    ]


def test_non_git_sibling_direct_url_is_rejected():
    assert [
        issue.code
        for issue in judge(
            '[project]\nname="consumer"\ndependencies=["omnibase-core @ https://packages.example.org/core.whl"]',
            "pyproject.toml",
        )
    ] == ["first_party_source_not_dev_tag"]


@pytest.mark.parametrize(
    "url",
    [
        "HTTPS://GITHUB.COM/OmniNode-ai/tools.git",
        "https://user@github.com/OmniNode-ai/tools.git",
        "git@github.com:OmniNode-ai/tools.git",
    ],
)
def test_first_party_url_forms_cannot_bypass_dev_tag(url):
    assert [
        issue.code
        for issue in judge(
            f"repos:\n- repo: {url}\n  rev: main\n", ".pre-commit-config.yaml"
        )
    ] == ["first_party_not_dev_tag"]


def test_precommit_yaml_merge_cannot_hide_first_party_repo():
    text = f"defaults: &repository\n  repo: https://github.com/{ORG}/tools.git\nrepos:\n- <<: *repository\n  rev: main\n"
    assert [issue.code for issue in judge(text, ".pre-commit-config.yaml")] == [
        "first_party_not_dev_tag"
    ]
