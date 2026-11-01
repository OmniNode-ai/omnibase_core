# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Integrated replay of every checker over the andon corpus (OMN-21530, plan task T0.8b).

``corpus.yaml`` is data and so are the ``.validation.yaml`` contracts; no revision, path or
rule id is spelled here. Each assertion is replayed at its audited revision (a clone) or
snapshot through the adapter the corpus names for the checker that owns its rule id.

The clone root and the require-clones variable are the corpus's own. With the root set the
whole corpus is replayed; without it only text snapshots are, and the report says which
assertions were not read; with the require-clones variable set a missing clone fails.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.andon_replay import driver

pytestmark = [pytest.mark.integration, pytest.mark.timeout(900)]

BASE_DIR = driver.DEFAULT_CORPUS_PATH.parent


@pytest.fixture(scope="module")
def corpus() -> driver.ModelCorpus:
    return driver.load_corpus(driver.DEFAULT_CORPUS_PATH)


@pytest.fixture(scope="module")
def contracts(corpus: driver.ModelCorpus) -> dict[str, driver.ReplayContract]:
    return driver.load_contracts(corpus, driver.repo_root(corpus))


@pytest.fixture(scope="module")
def environment(corpus: driver.ModelCorpus) -> dict[str, str]:
    return driver.environment(corpus)


@pytest.fixture(scope="module")
def report(
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
    environment: dict[str, str],
) -> tuple[list[driver.ModelReplayResult], list[str]]:
    return driver.replay(corpus, BASE_DIR, environment, contracts)


def _raw() -> dict[str, Any]:
    return driver.load_raw(driver.DEFAULT_CORPUS_PATH)


def _require_clones(corpus: driver.ModelCorpus, environment: dict[str, str]) -> bool:
    return bool(environment.get(corpus.resolution.require_clones_env, ""))


def test_integrated_replay_reports_every_assertion(
    corpus: driver.ModelCorpus,
    environment: dict[str, str],
    report: tuple[list[driver.ModelReplayResult], list[str]],
) -> None:
    results, unreadable = report
    assert driver.coverage_problems(corpus, results, unreadable) == []
    if _require_clones(corpus, environment):
        assert unreadable == [], "clones required and not all readable"
    wrong = [
        f"{r.assertion_id}: expected {r.expected}; {r.detail or 'nothing reported'}"
        for r in results
        if not r.ok
    ]
    assert wrong == []
    assert results, "nothing was replayed"


def test_integrated_replay_names_the_checker_of_every_assertion(
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
) -> None:
    unowned = [
        a.id
        for a in corpus.assertions
        if driver.owner_of(corpus, contracts, a.rule_id) is None
    ]
    assert unowned == []


def test_integrated_replay_fails_on_planted_unreported_rule_id(
    tmp_path: Path,
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
    environment: dict[str, str],
    report: tuple[list[driver.ModelReplayResult], list[str]],
) -> None:
    """A copy whose assertion expects a rule id its checker does not report fails."""
    results, _ = report
    chosen = next(
        (
            r
            for r in results
            if r.ok
            and r.validator_id in contracts
            and any(
                row not in {i.split(":", 1)[-1] for i in r.reported}
                for row in contracts[r.validator_id].rules
            )
        ),
        None,
    )
    assert chosen is not None and chosen.validator_id is not None
    absent = next(
        row
        for row in contracts[chosen.validator_id].rules
        if row not in {i.split(":", 1)[-1] for i in chosen.reported}
    )
    raw = _raw()
    for assertion in raw["assertions"]:
        if assertion["id"] == chosen.assertion_id:
            assertion["rule_id"] = f"{chosen.validator_id}:{absent}"
    planted = driver.write_raw(tmp_path, raw, copy_snapshots_from=BASE_DIR)
    planted_corpus = driver.load_corpus(planted)
    planted_results, _ = driver.replay(
        planted_corpus,
        tmp_path,
        environment,
        contracts,
        lambda a: a.id == chosen.assertion_id,
    )
    assert driver.failed_ids(planted_results) == {chosen.assertion_id}


def test_integrated_replay_fails_coverage_count_on_dropped_assertion(
    tmp_path: Path,
    contracts: dict[str, driver.ReplayContract],
    environment: dict[str, str],
) -> None:
    raw = _raw()
    raw["assertions"] = copy.deepcopy(raw["assertions"])[:-1]
    planted = driver.write_raw(tmp_path, raw, copy_snapshots_from=BASE_DIR)
    planted_corpus = driver.load_corpus(planted)
    results, unreadable = driver.replay(
        planted_corpus, tmp_path, environment, contracts
    )
    assert driver.coverage_problems(planted_corpus, results, unreadable)


def _rows_to_disable() -> list[str]:
    """Rule ids of the corpus that name a row of a contract, from the corpus and contracts."""
    corpus = driver.load_corpus(driver.DEFAULT_CORPUS_PATH)
    contracts = driver.load_contracts(corpus, driver.repo_root(corpus))
    return [
        rule_id
        for rule_id in driver.rule_ids(corpus)
        if driver.row_of(
            corpus,
            contracts.get(driver.owner_of(corpus, contracts, rule_id) or ""),
            rule_id,
        )
    ]


@pytest.mark.parametrize("rule_id", _rows_to_disable())
def test_disable_rule_fails_its_assertions(
    rule_id: str,
    tmp_path: Path,
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
    environment: dict[str, str],
    report: tuple[list[driver.ModelReplayResult], list[str]],
) -> None:
    """Disable one rule row in a copy of its contract: its own fixture stops reporting it
    and exactly the corpus assertions that name it newly fail."""
    owner = driver.owner_of(corpus, contracts, rule_id)
    assert owner is not None
    contract = contracts[owner]
    row = driver.row_of(corpus, contract, rule_id)
    assert row is not None
    disabled = driver.disabled_contract(contract, row, tmp_path)
    named = set(driver.assertions_naming(corpus, rule_id))
    results, _ = report
    before_failed = driver.failed_ids(results)

    def of_owner(a: driver.ModelAssertion) -> bool:
        return driver.owner_of(corpus, contracts, a.rule_id) == owner

    after, _ = driver.replay(
        corpus, BASE_DIR, environment, {**contracts, owner: disabled}, of_owner
    )
    replayed = {r.assertion_id for r in after}
    assert (
        driver.failed_ids(after) - before_failed == (named & replayed) - before_failed
    )
    fixtures = driver.rule_fixtures(corpus, driver.repo_root(corpus), owner, row)
    judge = driver.load_fixture_adapter(corpus, owner)
    assert judge is not None
    assert fixtures, f"{row}: no violation fixture of its own"
    assert any(row in driver.fixture_codes(judge, contract, f) for f in fixtures), (
        f"{row}: none of its violation fixtures reports it under the shipped contract"
    )
    for fixture in fixtures:
        assert row not in driver.fixture_codes(judge, disabled, fixture)
