# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A dated per-revision hook exemption in the dependency-pin check (OMN-23246).

The operator ruling 2026-11-09T01:57:48Z lets omnibase_infra keep its
check-public-runner-placement hook at one core revision for seven days, past the
release-count bound, while the self-hosted jobs move to hosted runners. These tests
hold the exemption to that: it covers one revision, it expires and then fails the
check, and the shipped policy lists exactly the ruled entry.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.dependency_direction.model_repo_layer import ModelRepoLayer
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.dependency_pins.model_dependency_hook_history import (
    ModelDependencyHookHistory,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_request import (
    ModelDependencyPinFactsRequest,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_result import (
    ModelDependencyPinFactsResult,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_hook_exemption import (
    ModelDependencyPinHookExemption,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_hook_repo import (
    ModelDependencyPinHookRepo,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_policy import (
    ModelDependencyPinPolicy,
)
from omnibase_core.models.dependency_pins.model_dependency_pins_input import (
    ModelDependencyPinsInput,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time import (
    ModelPrecommitRevTime,
)
from omnibase_core.validation import checker_dependency_pins as checker
from omnibase_core.validation.validator_dependency_pins import (
    ValidatorDependencyPins,
    load_dependency_pin_policy,
)

pytestmark = pytest.mark.unit

HOOK_URL = "https://example.invalid/acme/hooks"
REV = "a" * 40
OTHER_REV = "b" * 40
RULED_FULL_REV = "1c9566e2c249" + "d" * 28
RULING = "RULING 2026-01-02T03:04:05Z lane=fixture"
EXPIRES = date(2026, 3, 10)

# The one entry the shipped policy may hold, from the operator ruling
# 2026-11-09T01:57:48Z. An entry for any other revision needs its own ruling line:
# add it here with that ruling, and the entry's ruling cell must start with it.
SHIPPED_RULED = {
    (
        "https://github.com/OmniNode-ai/omnibase_core",
        "1c9566e2c249",
        date(2026, 11, 16),
        "RULING 2026-11-09T01:57:48Z",
        "OMN-22867",
    )
}


def _validator() -> ValidatorDependencyPins:
    return ValidatorDependencyPins(lambda _r: ModelDependencyPinFactsResult())


RULES = {r.rule_id: r for r in _validator().contract.rules}


def _layers() -> ModelRepoLayerMap:
    return ModelRepoLayerMap(
        github_org="acme",
        repos=(ModelRepoLayer(repo="top", layer=1, distributions=("top-pkg",)),),
    )


def _exemption(
    rev: str = REV[:12], expires: date = EXPIRES
) -> ModelDependencyPinHookExemption:
    return ModelDependencyPinHookExemption(
        url=HOOK_URL, rev=rev, expires=expires, ruling=RULING, ticket="OMN-1"
    )


def _policy(*exemptions: ModelDependencyPinHookExemption) -> ModelDependencyPinPolicy:
    return ModelDependencyPinPolicy(
        edge_tables=("project",),
        pin_style="range",
        release_tag_pattern=r"^v(?P<version>[0-9]+(?:\.[0-9]+)*)$",
        tag_inventory_url="https://example.invalid/{org}/{repo}.git",
        max_releases_behind=1,
        specifier_must_admit_newest_release=True,
        hook_repos=(ModelDependencyPinHookRepo(url=HOOK_URL, repo="top"),),
        hook_rev_max_releases_behind=14,
        hook_rev_exemptions=exemptions,
    )


def _precommit(*revs: str) -> str:
    return yaml.safe_dump(
        {
            "repos": [
                {"repo": HOOK_URL, "rev": rev, "hooks": [{"id": f"hook-{i}"}]}
                for i, rev in enumerate(revs)
            ]
        }
    )


def _history(*revs: str, behind: int = 15) -> ModelDependencyHookHistory:
    return ModelDependencyHookHistory(
        url=HOOK_URL,
        rev_times=tuple(
            ModelPrecommitRevTime(repo=HOOK_URL, rev=rev, committed_at=100)
            for rev in revs
        ),
        release_times=tuple(range(101, 101 + behind)),
    )


def _request(
    policy: ModelDependencyPinHookExemption | ModelDependencyPinPolicy,
    *revs: str,
    on: date | None,
    behind: int = 15,
) -> ModelDependencyPinsInput:
    return ModelDependencyPinsInput(
        manifest_path="pyproject.toml",
        manifest_text='[project]\nname = "top-pkg"\ndependencies = []\n',
        lock_path="uv.lock",
        precommit_path=".pre-commit-config.yaml",
        precommit_text=_precommit(*revs),
        layer_map=_layers(),
        policy=policy,
        hook_histories=(_history(*revs, behind=behind),),
        checked_on=on,
    )


def _codes(request: ModelDependencyPinsInput) -> list[str]:
    return sorted(str(i.code) for i in checker.check_dependency_pins(request, RULES))


def test_unexempted_rev_past_the_bound_is_refused() -> None:
    assert _codes(_request(_policy(), REV, on=EXPIRES)) == ["hook_rev_behind"]


def test_exempt_rev_passes_with_a_warning_until_its_expiry_day() -> None:
    policy = _policy(_exemption())
    for day in (date(2026, 3, 3), EXPIRES):
        issues = checker.check_dependency_pins(_request(policy, REV, on=day), RULES)
        assert [str(i.code) for i in issues] == ["hook_rev_exempted"]
        assert issues[0].severity == EnumSeverity.WARNING
        assert RULING in issues[0].message
        assert "OMN-1" in issues[0].message
        assert EXPIRES.isoformat() in issues[0].message


def test_expired_exemption_fails_the_check() -> None:
    request = _request(_policy(_exemption()), REV, on=date(2026, 3, 11))
    issues = checker.check_dependency_pins(request, RULES)
    assert sorted(str(i.code) for i in issues) == [
        "hook_rev_behind",
        "hook_rev_exemption_expired",
    ]
    assert {i.severity for i in issues} == {EnumSeverity.ERROR}


def test_expired_exemption_fails_even_when_the_rev_is_back_inside_the_bound() -> None:
    request = _request(_policy(_exemption()), REV, on=date(2026, 3, 11), behind=2)
    assert _codes(request) == ["hook_rev_exemption_expired"]


def test_exemption_with_no_date_to_judge_it_by_fails_closed() -> None:
    assert "hook_rev_exemption_expired" in _codes(
        _request(_policy(_exemption()), REV, on=None)
    )


def test_exemption_covers_its_revision_and_no_other() -> None:
    request = _request(_policy(_exemption()), REV, OTHER_REV, on=date(2026, 3, 3))
    issues = checker.check_dependency_pins(request, RULES)
    assert sorted(str(i.code) for i in issues) == [
        "hook_rev_behind",
        "hook_rev_exempted",
    ]
    behind = next(i for i in issues if i.code == "hook_rev_behind")
    assert OTHER_REV in behind.message


def test_exemption_never_covers_a_short_ref_or_a_tag() -> None:
    for pinned in (REV[:12], "v1.2.3", "dev-20261105190003-aaaaaaaaaaaa"):
        request = _request(_policy(_exemption()), pinned, on=EXPIRES)
        assert _codes(request) == ["hook_rev_behind"], pinned


def test_exemption_for_another_hook_repository_exempts_nothing() -> None:
    other = _exemption().model_copy(update={"url": "https://example.invalid/x/y"})
    assert _codes(_request(_policy(other), REV, on=EXPIRES)) == ["hook_rev_behind"]


@pytest.mark.parametrize(
    "update",
    [
        {"rev": REV},
        {"rev": REV[:11]},
        {"rev": "A" * 12},
        {"ruling": "the operator said so"},
        {"ruling": ""},
        {"ticket": "soon"},
        {"expires": "never"},
    ],
)
def test_exemption_entry_needs_a_full_rev_a_ruling_stamp_and_a_ticket(
    update: dict[str, object],
) -> None:
    fields: dict[str, object] = {
        "url": HOOK_URL,
        "rev": REV[:12],
        "expires": EXPIRES,
        "ruling": RULING,
        "ticket": "OMN-1",
    }
    fields.update(update)
    with pytest.raises(ValidationError):
        ModelDependencyPinHookExemption(**fields)


def test_exemption_entry_has_no_open_ended_form() -> None:
    with pytest.raises(ValidationError):
        ModelDependencyPinHookExemption.model_validate(
            {"url": HOOK_URL, "rev": REV[:12], "ruling": RULING, "ticket": "OMN-1"}
        )


def test_shipped_policy_holds_exactly_the_ruled_entry() -> None:
    held = {
        (
            e.url,
            e.rev,
            e.expires,
            e.ruling[: len("RULING 2026-11-09T01:57:48Z")],
            e.ticket,
        )
        for e in load_dependency_pin_policy().hook_rev_exemptions
    }
    assert held == SHIPPED_RULED
    assert len(load_dependency_pin_policy().hook_rev_exemptions) == len(SHIPPED_RULED)


def test_shipped_policy_ratchet_fails_on_an_added_entry() -> None:
    """Control: an entry beyond the ruled set makes the ratchet comparison fail."""
    policy = load_dependency_pin_policy()
    extra = policy.hook_rev_exemptions[0].model_copy(update={"rev": OTHER_REV[:12]})
    grown = policy.model_copy(
        update={"hook_rev_exemptions": (*policy.hook_rev_exemptions, extra)}
    )
    held = {(e.url, e.rev) for e in grown.hook_rev_exemptions}
    assert held != {(u, r) for u, r, *_ in SHIPPED_RULED}


def _shipped_run(tmp_path: Path, rev: str, today: date) -> tuple[bool, list[str]]:
    policy = load_dependency_pin_policy()
    url = policy.hook_repos[0].url
    repo = policy.hook_repos[0].repo
    layers = ModelRepoLayerMap(
        github_org="acme",
        repos=(
            ModelRepoLayer(repo=repo, layer=0, distributions=("core-pkg",)),
            ModelRepoLayer(repo="top", layer=1, distributions=("top-pkg",)),
        ),
    )
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "top-pkg"\ndependencies = []\n', "utf-8"
    )
    (root / ".pre-commit-config.yaml").write_text(
        yaml.safe_dump(
            {"repos": [{"repo": url, "rev": rev, "hooks": [{"id": "the-hook"}]}]}
        ),
        "utf-8",
    )

    def read(_r: ModelDependencyPinFactsRequest) -> ModelDependencyPinFactsResult:
        return ModelDependencyPinFactsResult(
            hook_histories=(
                ModelDependencyHookHistory(
                    url=url,
                    rev_times=(
                        ModelPrecommitRevTime(repo=url, rev=rev, committed_at=100),
                    ),
                    release_times=tuple(range(101, 116)),
                ),
            )
        )

    result = ValidatorDependencyPins(
        read, layer_order=layers, policy=policy, today=today
    ).validate(root)
    return result.is_valid, sorted(str(i.code) for i in result.issues)


def test_shipped_policy_exempts_the_ruled_rev_for_the_seven_days(
    tmp_path: Path,
) -> None:
    ruled = RULED_FULL_REV
    assert _shipped_run(tmp_path, ruled, date(2026, 11, 9)) == (
        True,
        ["hook_rev_exempted"],
    )


def test_shipped_policy_fails_the_ruled_rev_after_the_expiry(tmp_path: Path) -> None:
    ruled = RULED_FULL_REV
    valid, codes = _shipped_run(tmp_path, ruled, date(2026, 11, 17))
    assert not valid
    assert "hook_rev_exemption_expired" in codes


def test_shipped_policy_does_not_exempt_any_other_rev(tmp_path: Path) -> None:
    valid, codes = _shipped_run(tmp_path, OTHER_REV, date(2026, 11, 9))
    assert not valid
    assert codes == ["hook_rev_behind"]
