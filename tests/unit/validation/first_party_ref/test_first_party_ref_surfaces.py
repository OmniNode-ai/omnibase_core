# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One case per surface: a planted first-party sha is refused, a dev-merge tag passes (OMN-21900).

The surfaces are the ones operator ruling 2026-10-29T01:50:26Z names: pre-commit revs,
pyproject and uv git sources, workflow uses and lab deploy refs.
"""

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_first_party_ref_input import (
    ModelFirstPartyRefInput,
)
from omnibase_core.models.validation.model_first_party_tag_inventory_result import (
    ModelFirstPartyTagInventoryResult,
)
from omnibase_core.validation.checker_first_party_ref import check_first_party_refs
from omnibase_core.validation.validator_first_party_ref import ValidatorFirstPartyRef

pytestmark = pytest.mark.unit
ORG = "OmniNode-ai"
URL = f"https://github.com/{ORG}/omnibase_core.git"
TAG = "dev-20261018024445-b6ee996befa1"
SHA = "d7ed23f1" * 5

PYPROJECT_HEAD = '[project]\nname="consumer"\ndependencies=["omnibase-core>=0.1"]\n'


def _pyproject_source(ref: str) -> str:
    key = "tag" if ref == TAG else "rev"
    return (
        PYPROJECT_HEAD
        + f'[tool.uv.sources]\nomnibase-core = {{ git = "{URL}", {key} = "{ref}" }}\n'
    )


def _pyproject_direct(ref: str) -> str:
    return (
        '[project]\nname="consumer"\n'
        f'dependencies=["omnibase-core @ git+{URL}@{ref}"]\n'
    )


SURFACES = {
    "precommit_rev": (
        ".pre-commit-config.yaml",
        lambda ref: f"repos:\n- repo: {URL}\n  rev: {ref}\n",
    ),
    "pyproject_uv_source": ("pyproject.toml", _pyproject_source),
    "pyproject_direct_git_requirement": ("pyproject.toml", _pyproject_direct),
    "workflow_uses": (
        ".github/workflows/ci.yml",
        lambda ref: f"jobs:\n  a:\n    steps:\n      - uses: {ORG}/omnibase_core/.github/actions/x@{ref}\n",
    ),
    "workflow_git_url": (
        ".github/workflows/ci.yml",
        lambda ref: f"run: pip install git+{URL}@{ref}\n",
    ),
    "lab_deploy_ref": (
        "lab/deploy.yaml",
        lambda ref: f"repository: {URL}\ndeploy_ref: {ref}\n",
    ),
    "lab_nested_ref": (
        "config/lab/stack.yml",
        lambda ref: f"services:\n  - repo: {ORG}/omnibase_core\n    ref: {ref}\n",
    ),
    "deploy_file_git_ref": (
        "ops/deploy-lab.yaml",
        lambda ref: f"git: {URL}\ngit_ref: {ref}\n",
    ),
    "lab_bare_deploy_ref": ("lab/deploy.yaml", lambda ref: f"deploy_ref: {ref}\n"),
    "lab_bare_lab_deploy_ref": (
        "config/lab/stack.yaml",
        lambda ref: f"stack:\n  lab_deploy_ref: {ref}\n",
    ),
    "lab_literal_cross_repo_ref": (
        "lab/deploy.yaml",
        lambda ref: f"cross_repo_ref: {ORG}/omnibase_core@{ref}\n",
    ),
}


def judge(path: str, source: str) -> tuple[str, ...]:
    contract = ValidatorFirstPartyRef().contract
    facts = ModelFirstPartyRefInput(
        files=(ModelSourceFile(path=path, source=source),),
        dev_tags=(
            ModelFirstPartyTagInventoryResult(repo="omnibase_core", tags=(TAG,)),
        ),
    )
    return tuple(issue.code for issue in check_first_party_refs(facts, contract))


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_first_party_ref_surface_refuses_a_planted_sha(surface):
    path, plant = SURFACES[surface]
    codes = judge(path, plant(SHA))
    assert codes, f"{surface}: a planted first-party sha was not refused"
    assert "first_party_ref_two_homes" not in codes


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_first_party_ref_surface_passes_a_planted_dev_tag(surface):
    path, plant = SURFACES[surface]
    assert judge(path, plant(TAG)) == ()


@pytest.mark.parametrize("surface", sorted(SURFACES))
@pytest.mark.parametrize("ref", ["main", "dev", "master"])
def test_first_party_ref_surface_refuses_a_branch_ref(surface, ref):
    path, plant = SURFACES[surface]
    assert judge(path, plant(ref))


@pytest.mark.parametrize("value", ['""', "${DEPLOY_REF}", "${{ inputs.ref }}"])
def test_first_party_ref_empty_or_templated_bare_deploy_ref_is_not_a_literal(value):
    assert judge("lab/deploy.yaml", f"deploy_ref: {value}\n") == ()


def test_first_party_ref_bare_deploy_ref_beside_a_repository_is_one_finding():
    assert judge("lab/deploy.yaml", f"repository: {URL}\ndeploy_ref: {SHA}\n") == (
        "cross_repo_ref_not_dev_tag",
    )


def test_first_party_ref_nested_lab_directory_file_is_a_target():
    patterns = ValidatorFirstPartyRef().contract.target_patterns
    assert "**/lab/*.yaml" in patterns
    assert "**/lab/*.yml" in patterns
