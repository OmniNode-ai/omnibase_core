# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pre-commit pin-parity rule (OMN-21495, plan task T0.2).

A hook of the shared core hook repo may not pin a rev older than the newest rev
that hook repo is pinned at anywhere in the same ``.pre-commit-config.yaml``.
The handler is pure: the commit time of each rev arrives in the request.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_precommit_pin_parity import (
    HandlerPrecommitPinParity,
)
from omnibase_core.models.precommit_pins import (
    ModelPrecommitPinParityInput,
    ModelPrecommitPinRules,
    ModelPrecommitRevTime,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).parents[2] / "fixtures" / "precommit_pin_parity"
_ORG = "OmniNode-ai"
_CORE = f"https://github.com/{_ORG}/omnibase_core"
_OTHER = f"https://github.com/{_ORG}/omniclaude"
_OLD = "1" * 40
_NEW = "2" * 40
_TIMES = (
    ModelPrecommitRevTime(rev=_OLD, committed_at=1_000),
    ModelPrecommitRevTime(rev=_NEW, committed_at=2_000),
)


def _config(*entries: tuple[str, str, str]) -> str:
    """One ``repos`` entry per (repo url, rev, hook id), one line each."""
    return "repos:\n" + "".join(
        f"  - repo: {url}\n    rev: {rev}\n    hooks:\n      - id: {hook}\n"
        for url, rev, hook in entries
    )


def _run(
    source: str,
    times: tuple[ModelPrecommitRevTime, ...] = _TIMES,
    repos: tuple[str, ...] = (_CORE,),
) -> ModelValidationReport:
    return HandlerPrecommitPinParity().handle(
        ModelPrecommitPinParityInput(
            rules=ModelPrecommitPinRules(hook_repos=repos),
            path=".pre-commit-config.yaml",
            source=source,
            rev_times=times,
        )
    )


def test_hook_pinned_older_than_the_newest_pin_fails_at_its_rev_line() -> None:
    report = _run(_config((_CORE, _OLD, "alpha"), (_CORE, _NEW, "beta")))
    assert report.overall_status == "FAIL"
    [finding] = report.findings
    assert finding.severity == "FAIL"
    assert finding.location == ".pre-commit-config.yaml:3"
    assert _OLD in finding.message and _NEW in finding.message
    assert "alpha" in finding.message


def test_order_in_the_file_does_not_matter() -> None:
    report = _run(_config((_CORE, _NEW, "beta"), (_CORE, _OLD, "alpha")))
    assert report.overall_status == "FAIL"
    [finding] = report.findings
    assert finding.location == ".pre-commit-config.yaml:7"


def test_every_hook_at_the_newest_rev_passes() -> None:
    report = _run(_config((_CORE, _NEW, "alpha"), (_CORE, _NEW, "beta")))
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_a_single_pin_passes_without_any_commit_time() -> None:
    assert _run(_config((_CORE, _OLD, "alpha")), times=()).overall_status == "PASS"


def test_a_repo_the_rules_do_not_name_is_ignored() -> None:
    report = _run(_config((_OTHER, _OLD, "alpha"), (_OTHER, _NEW, "beta")))
    assert report.overall_status == "PASS"


def test_the_git_suffix_and_a_trailing_slash_name_the_same_repo() -> None:
    report = _run(_config((f"{_CORE}.git", _OLD, "alpha"), (f"{_CORE}/", _NEW, "beta")))
    assert report.overall_status == "FAIL"


def test_a_rev_with_no_commit_time_fails_closed() -> None:
    report = _run(
        _config((_CORE, _OLD, "alpha"), (_CORE, _NEW, "beta")),
        times=(ModelPrecommitRevTime(rev=_NEW, committed_at=2_000),),
    )
    assert report.overall_status == "FAIL"
    assert any(_OLD in f.message for f in report.findings)


def test_two_hooks_in_one_entry_name_both() -> None:
    source = (
        f"repos:\n  - repo: {_CORE}\n    rev: {_OLD}\n    hooks:\n"
        "      - id: alpha\n      - id: gamma\n"
        f"  - repo: {_CORE}\n    rev: {_NEW}\n    hooks:\n      - id: beta\n"
    )
    [finding] = _run(source).findings
    assert "alpha" in finding.message and "gamma" in finding.message


def test_local_and_meta_repos_are_ignored() -> None:
    source = (
        "repos:\n  - repo: local\n    hooks:\n      - id: x\n"
        f"  - repo: {_CORE}\n    rev: {_NEW}\n    hooks:\n      - id: beta\n"
    )
    assert _run(source).overall_status == "PASS"


@pytest.mark.parametrize("source", ["", "- a\n- b\n", "repos: 3\n", "repos: [\n"])
def test_a_config_that_is_not_a_repos_mapping_is_refused(source: str) -> None:
    with pytest.raises(ModelOnexError):
        _run(source)


def test_canary_lowered_pin_fixture_fails_and_the_converged_fixture_passes() -> None:
    lowered = (_FIXTURES / "canary_lowered_pin.yaml").read_text(encoding="utf-8")
    converged = (_FIXTURES / "converged_pins.yaml").read_text(encoding="utf-8")
    failed = _run(lowered)
    assert failed.overall_status == "FAIL"
    assert [f.location for f in failed.findings] == [".pre-commit-config.yaml:7"]
    assert _run(converged).overall_status == "PASS"


# Real omnibase_core commit times (git show -s --format=%ct) of the two revs the T0.2
# falsifier names: the pin omniclaude-internal carries at .pre-commit-config.yaml:13
# and the omnibase_core dev head it is compared with. The revs are read from the fixture.
_CONSUMER_LAGGING = (_FIXTURES / "consumer_line13_d7ed23f1.yaml").read_text(
    encoding="utf-8"
)
_CONSUMER_REVS = [entry["rev"] for entry in yaml.safe_load(_CONSUMER_LAGGING)["repos"]]
_CONSUMER_TIMES = (
    ModelPrecommitRevTime(rev=_CONSUMER_REVS[0], committed_at=1_792_090_542),
    ModelPrecommitRevTime(rev=_CONSUMER_REVS[1], committed_at=1_793_219_092),
)


def test_consumer_config_pinned_at_d7ed23f1_on_line_13_fails_and_the_current_pin_passes() -> (
    None
):
    current = (_FIXTURES / "consumer_line13_current_pin.yaml").read_text(
        encoding="utf-8"
    )
    assert _CONSUMER_REVS[0].startswith("d7ed23f1")
    assert _CONSUMER_REVS[1].startswith("b8b19b0b")
    failed = _run(_CONSUMER_LAGGING, times=_CONSUMER_TIMES)
    assert failed.overall_status == "FAIL"
    assert [f.location for f in failed.findings] == [".pre-commit-config.yaml:13"]
    assert _CONSUMER_REVS[0] in failed.findings[0].message
    assert _CONSUMER_REVS[1] in failed.findings[0].message
    assert _run(current, times=_CONSUMER_TIMES).overall_status == "PASS"
