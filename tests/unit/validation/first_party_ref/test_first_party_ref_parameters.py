# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Every rule parameter is exercised by a behavior-changing mutation.

Effect dependencies are tested through a deterministic process boundary: invalid
backend arguments or unavailable tags change a clean verdict into a blocking one.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.models.validation.model_first_party_ref_input import (
    ModelFirstPartyRefInput,
)
from omnibase_core.models.validation.model_first_party_tag_inventory_request import (
    ModelFirstPartyTagInventoryRequest,
)
from omnibase_core.models.validation.model_sibling_stale_parameters import (
    ModelSiblingStaleParameters,
)
from omnibase_core.nodes.node_first_party_tag_inventory_effect.handler import (
    NodeFirstPartyTagInventoryEffect,
)
from omnibase_core.validation.checker_first_party_ref import (
    check_first_party_refs,
    load_rule_parameters,
)
from omnibase_core.validation.validator_first_party_ref import ValidatorFirstPartyRef

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parents[3] / "fixtures/validation/first_party_ref"
TAG = "dev-20261018024445-b6ee996befa1"
SHA = "a" * 40
ORG = "OmniNode-ai"
CONTRACT = ValidatorFirstPartyRef().contract
CASES = [(row.rule_id, key) for row in CONTRACT.rules for key in row.parameters]
EFFECT_KEYS = {
    "url_template",
    "github_org",
    "git_binary",
    "timeout_seconds",
    "tag_arguments",
    "tag_prefix",
    "peeled_suffix",
}


def fixture(rule, prefix="violation"):
    return ModelFirstPartyRefInput.model_validate(
        json.loads((FIXTURES / f"{prefix}_{rule}.json").read_text())
    )


def changed(rule, key, value, contract=CONTRACT):
    rows = tuple(
        row.model_copy(update={"parameters": {**row.parameters, key: value}})
        if row.rule_id == rule
        else row
        for row in contract.rules
    )
    return contract.model_copy(update={"rules": rows})


def facts(source, path=".github/workflows/ci.yml", inventories=()):
    return ModelFirstPartyRefInput.model_validate(
        {"files": [{"path": path, "source": source}], "dev_tags": inventories}
    )


def verdict(data, contract, rule):
    return [
        issue.model_dump(mode="json")
        for issue in check_first_party_refs(data, contract)
        if issue.code == rule
    ]


def source_ref(rule, value):
    if rule == "first_party_source_not_dev_tag":
        return facts(
            f'[tool.uv.sources]\ntools={{git="https://github.com/{ORG}/tools.git", tag="{value}"}}',
            "pyproject.toml",
        )
    if rule == "cross_repo_ref_not_dev_tag":
        return facts(
            f"cross_repo_ref: {ORG}/tools@{value}", ".github/required-checks.yaml"
        )
    return facts(f"uses: {ORG}/tools@{value}")


def mutation_case(rule, key):
    data = fixture(rule)
    contract = CONTRACT
    if key == "file_globs":
        value = ["unmatched/**"]
    elif key == "remediation":
        value = "Changed remedy."
    elif key == "github_org":
        value = (
            "actions"
            if rule == "third_party_not_sha"
            else ("other" if rule == "wrong_repo" else "another-org")
        )
    elif key == "patterns":
        value = ["$^"]
        if rule == "cross_repo_ref_not_dev_tag":
            data = facts(
                f"run: pip install git+https://github.com/{ORG}/tools.git@{SHA}"
            )
        if rule == "first_party_source_not_dev_tag":
            data = facts(
                f'[project]\nname="consumer"\ndependencies=["tools @ git+https://github.com/{ORG}/tools.git@{SHA}"]',
                "pyproject.toml",
            )
    elif key in {"brief_globs", "brief_patterns"}:
        value = ["unmatched/**"] if key == "brief_globs" else ["$^"]
        data = facts(f"Deploy {ORG}/tools@{SHA}", "briefs/deploy-brief.md")
    elif key == "structured_globs":
        value = ["unmatched/**"]
        if rule == "first_party_not_dev_tag":
            data = facts(
                f"repos:\n- repo: https://github.com/{ORG}/tools.git\n  rev: main\n",
                ".pre-commit-config.yaml",
            )
        elif rule == "cross_repo_ref_not_dev_tag":
            data = facts(
                f"repo: https://github.com/{ORG}/tools.git\nref: main\n",
                "lab/deploy.yaml",
            )
    elif key == "literal_ref_keys":
        value = ["unrecognized"]
        data = facts(
            f'"cross_repo_ref": "{ORG}/tools@main"', ".github/required-checks.yaml"
        )
    elif key in {"repository_keys", "ref_keys"}:
        value = ["unrecognized"]
        data = facts(
            f"repo: https://github.com/{ORG}/tools.git\nref: main\n", "lab/deploy.yaml"
        )
    elif key == "sha_pattern":
        value = "$^"
        if rule != "third_party_not_sha":
            contract = changed(rule, "tag_pattern", ".*")
            data = source_ref(rule, SHA)
        else:
            data = fixture(rule, "clean")
    elif key == "forbidden_refs":
        value = []
        contract = changed(rule, "tag_pattern", ".*")
        data = source_ref(rule, "main")
    elif key == "tag_pattern":
        value = ".*" if rule == "brief_names_release_version" else "$^"
        if rule in {
            "first_party_not_dev_tag",
            "first_party_source_not_dev_tag",
            "cross_repo_ref_not_dev_tag",
        }:
            data = fixture(rule, "clean")
    elif key == "release_pattern":
        value = "$^"
    elif key == "max_files":
        value = 2
    elif key == "repository_pattern":
        value = r"(?P<org>[^/]+)/(?P<repo>[^/]+)"
    elif key == "siblings":
        value = ["another=another"]
    elif key in {"name_pattern", "normalize_pattern"}:
        value = "$^"
        # Direct requirements exercise discovery independently of uv source keys.
        if rule in {"wrong_repo", "stale_pin"}:
            url_org = "other" if rule == "wrong_repo" else ORG
            source = f'[project]\nname="consumer"\ndependencies=["omnibase-core @ git+https://github.com/{url_org}/omnibase_core.git@{TAG}"]'
            inventories = [
                {
                    "repo": "omnibase_core",
                    "tags": [TAG, "dev-20261023024445-aaaaaaaaaaaa"],
                }
            ]
            data = facts(source, "pyproject.toml", inventories)
        if key == "normalize_pattern":
            data = data.model_copy(
                update={
                    "files": tuple(
                        file.model_copy(
                            update={
                                "source": file.source.replace(
                                    "omnibase-core", "omnibase_core"
                                )
                            }
                        )
                        for file in data.files
                    )
                }
            )
    elif key == "url_template":
        value = "https://github.com/other/{repo}.git"
    elif key == "exact_pattern":
        value = "$^"
    elif key == "max_trailing_merges":
        bound = load_rule_parameters(CONTRACT)[rule].max_trailing_merges
        start = datetime.strptime(TAG.split("-")[1], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        tags = [TAG] + [
            f"dev-{(start + timedelta(seconds=i)).strftime('%Y%m%d%H%M%S')}-aaaaaaaaaaaa"
            for i in range(1, bound + 2)
        ]
        data = fixture(rule, "clean").model_copy(
            update={
                "dev_tags": tuple(
                    type(inventory)(repo=inventory.repo, tags=tuple(tags))
                    for inventory in fixture(rule, "clean").dev_tags
                )
            }
        )
        value = bound + 1
    elif key == "max_trailing_hours":
        value = 1000
    elif key in {"timestamp_pattern", "timestamp_format"}:
        data = fixture(rule, "clean")
        value = r"^unknown-(.*)" if key == "timestamp_pattern" else "%Y"
    else:
        raise AssertionError(f"missing mutation fixture for {rule}.{key}")
    return data, contract, value


@pytest.mark.parametrize(
    ("rule", "key"), CASES, ids=[f"{rule}.{key}" for rule, key in CASES]
)
def test_every_parameter_changes_its_verdict(rule, key):
    if rule == "stale_pin" and key in EFFECT_KEYS:
        effect_parameter_changes_verdict(key)
        return
    data, contract, value = mutation_case(rule, key)
    before = verdict(data, contract, rule)
    after = verdict(data, changed(rule, key, value, contract), rule)
    assert before != after, (rule, key, before, after)


def effect_parameter_changes_verdict(key):
    policy = load_rule_parameters(CONTRACT)["stale_pin"]
    assert isinstance(policy, ModelSiblingStaleParameters)
    data = fixture("stale_pin", "clean")
    replacements = {
        "url_template": "https://missing.invalid/{repo}",
        "github_org": "other",
        "git_binary": "missing-git",
        "timeout_seconds": 1,
        "tag_arguments": ["invalid"],
        "tag_prefix": "other/",
        "peeled_suffix": TAG[-12:],
    }
    expected_url = policy.url_template.format(
        org=policy.github_org, repo="omnibase_core"
    )
    expected_argv = [
        policy.git_binary,
        *(arg.format(url=expected_url) for arg in policy.tag_arguments),
    ]

    def backend(argv, *, check, capture_output, text, timeout, env):
        assert check and capture_output and text
        if argv != expected_argv:
            raise subprocess.CalledProcessError(1, argv)
        if timeout < policy.timeout_seconds:
            raise subprocess.TimeoutExpired(argv, timeout)
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=f"{SHA}\t{policy.tag_prefix}{TAG}\n{SHA}\t{policy.tag_prefix}{TAG}{policy.peeled_suffix}\n",
        )

    def evaluate(candidate):
        with patch(
            "omnibase_core.nodes.node_first_party_tag_inventory_effect.handler.subprocess.run",
            backend,
        ):
            try:
                inventory = NodeFirstPartyTagInventoryEffect().handle(
                    ModelFirstPartyTagInventoryRequest(
                        repo="omnibase_core", policy=candidate
                    )
                )
            except subprocess.SubprocessError:
                return "ERROR"
        return verdict(
            data.model_copy(update={"dev_tags": (inventory,)}), CONTRACT, "stale_pin"
        )

    assert evaluate(policy) == []
    assert evaluate(policy.model_copy(update={key: replacements[key]})) != []


@pytest.mark.parametrize(("rule", "key"), CASES)
def test_missing_parameter_is_rejected(rule, key):
    row = next(row for row in CONTRACT.rules if row.rule_id == rule)
    params = dict(row.parameters)
    del params[key]
    rows = tuple(
        item.model_copy(update={"parameters": params}) if item.rule_id == rule else item
        for item in CONTRACT.rules
    )
    with pytest.raises(ValidationError):
        load_rule_parameters(CONTRACT.model_copy(update={"rules": rows}))


@pytest.mark.parametrize("rule", [row.rule_id for row in CONTRACT.rules])
def test_unknown_parameter_is_rejected(rule):
    with pytest.raises(ValidationError):
        load_rule_parameters(changed(rule, "unknown", "not admitted"))


def test_invalid_contract_file_fails_at_load(tmp_path):
    validator = ValidatorFirstPartyRef()
    document = yaml.safe_load(validator._get_contract_path().read_text())
    del document["validation"]["rules"][0]["parameters"]["remediation"]
    target = tmp_path / "first_party_ref.validation.yaml"
    target.write_text(yaml.safe_dump(document))
    with (
        patch.object(ValidatorFirstPartyRef, "_get_contract_path", return_value=target),
        pytest.raises(ValidationError),
    ):
        _contract = ValidatorFirstPartyRef().contract
