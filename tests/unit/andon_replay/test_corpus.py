# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay corpus checks (OMN-21530, plan task T0.8a).

``corpus.yaml`` is data; every revision, path, line and rule id lives there. The
checks below compare it against the finding table it snapshots (D.3) and resolve
every input. The planted tests mutate a copy of the corpus and require the
matching check to fail on the copy.
"""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env
from tests.fixtures.andon_replay import driver

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def corpus() -> driver.ModelCorpus:
    return driver.load_corpus(driver.DEFAULT_CORPUS_PATH)


def _raw() -> dict[str, Any]:
    return driver.load_raw(driver.DEFAULT_CORPUS_PATH)


def test_corpus_covers_findings(corpus: driver.ModelCorpus) -> None:
    assert driver.findings_problems(corpus, driver.DEFAULT_CORPUS_PATH.parent) == []


def test_corpus_covers_findings_counts_forty_seven_mechanical(
    corpus: driver.ModelCorpus,
) -> None:
    expected = driver.mechanical_finding_ids(corpus, driver.DEFAULT_CORPUS_PATH.parent)
    assert len(expected) == 47
    assert {a.finding for a in corpus.assertions} == set(expected)


def test_corpus_covers_findings_fails_on_planted_missing_id(tmp_path: Path) -> None:
    raw = _raw()
    removed = raw["assertions"][0]["finding"]
    raw["assertions"] = [a for a in raw["assertions"] if a["finding"] != removed]
    planted = driver.write_raw(
        tmp_path, raw, copy_snapshots_from=driver.DEFAULT_CORPUS_PATH.parent
    )
    problems = driver.findings_problems(driver.load_corpus(planted), tmp_path)
    assert any(removed in p for p in problems)


def test_corpus_covers_findings_fails_on_excluded_id_given_an_assertion(
    tmp_path: Path,
) -> None:
    raw = _raw()
    donor = copy.deepcopy(raw["assertions"][0])
    donor["id"] = "excluded-planted"
    donor["finding"] = raw["findings"]["not_mechanical"][0]
    raw["assertions"].append(donor)
    planted = driver.write_raw(
        tmp_path, raw, copy_snapshots_from=driver.DEFAULT_CORPUS_PATH.parent
    )
    problems = driver.findings_problems(driver.load_corpus(planted), tmp_path)
    assert any(donor["finding"] in p for p in problems)


def test_corpus_rule_index_names_every_assertion(corpus: driver.ModelCorpus) -> None:
    """The index the disable-a-rule test (T0.8b) reads covers every assertion once."""
    named = [
        i
        for rule in driver.rule_ids(corpus)
        for i in driver.assertions_naming(corpus, rule)
    ]
    assert sorted(named) == sorted(a.id for a in corpus.assertions)
    assert len(set(named)) == len(named)


def test_corpus_names_a_rule_id_in_checker_form(corpus: driver.ModelCorpus) -> None:
    assert all(a.rule_id and " " not in a.rule_id for a in corpus.assertions)


def test_inputs_resolve(corpus: driver.ModelCorpus) -> None:
    report = driver.resolve_inputs(
        corpus, driver.DEFAULT_CORPUS_PATH.parent, driver.environment(corpus)
    )
    assert report.problems == []
    assert report.snapshots_checked == len(corpus.snapshots)
    assert report.code_inputs_structurally_checked > 0
    if report.clones_required:
        assert report.clones_reachable, "clone root required and not reachable"
        assert report.code_inputs_resolved_in_clones == report.code_inputs_total


def test_inputs_resolve_fails_on_planted_altered_snapshot_sha256(
    tmp_path: Path,
) -> None:
    raw = _raw()
    sha = raw["snapshots"][0]["sha256"]
    raw["snapshots"][0]["sha256"] = ("0" if sha[0] != "0" else "1") + sha[1:]
    planted = driver.write_raw(
        tmp_path, raw, copy_snapshots_from=driver.DEFAULT_CORPUS_PATH.parent
    )
    planted_corpus = driver.load_corpus(planted)
    report = driver.resolve_inputs(
        planted_corpus, tmp_path, driver.environment(planted_corpus)
    )
    assert any(
        raw["snapshots"][0]["id"] in p and "sha256" in p for p in report.problems
    )


def test_inputs_resolve_fails_on_planted_edited_snapshot_text(tmp_path: Path) -> None:
    raw = _raw()
    planted = driver.write_raw(
        tmp_path, raw, copy_snapshots_from=driver.DEFAULT_CORPUS_PATH.parent
    )
    target = tmp_path / raw["snapshots"][0]["path"]
    target.write_text(
        target.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8"
    )
    planted_corpus = driver.load_corpus(planted)
    report = driver.resolve_inputs(
        planted_corpus, tmp_path, driver.environment(planted_corpus)
    )
    assert any(raw["snapshots"][0]["id"] in p for p in report.problems)


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(),
    )
    return done.stdout.strip()


def test_inputs_resolve_clone_check_positive_and_negative_control(
    tmp_path: Path,
) -> None:
    """A real revision resolves and made-up ones are refused, in a scratch clone."""
    raw = _raw()
    clone_root_env = raw["resolution"]["clone_root_env"]
    require_env = raw["resolution"]["require_clones_env"]
    repo_key = next(
        a["input"]["repository"]
        for a in raw["assertions"]
        if a["input"]["kind"] == "code"
    )
    clone = tmp_path / raw["resolution"]["clone_dirs"][repo_key]
    clone.mkdir()
    _git(clone, "init", "-q")
    _git(clone, "config", "user.email", "t@example.invalid")
    _git(clone, "config", "user.name", "t")
    (clone / "f.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    _git(clone, "add", "f.txt")
    _git(clone, "commit", "-q", "-m", "x")
    real = _git(clone, "rev-parse", "HEAD")
    env = {clone_root_env: str(tmp_path), require_env: "1"}
    good = driver.build_probe_corpus(raw, repo_key, real, "f.txt", 2, "beta")
    assert driver.resolve_inputs(good, tmp_path, env).problems == []
    bad_rev = driver.build_probe_corpus(raw, repo_key, "1" * 40, "f.txt", 2, "beta")
    assert driver.resolve_inputs(bad_rev, tmp_path, env).problems
    bad_quote = driver.build_probe_corpus(raw, repo_key, real, "f.txt", 1, "beta")
    assert driver.resolve_inputs(bad_quote, tmp_path, env).problems
    no_clones = driver.resolve_inputs(good, tmp_path, {require_env: "1"})
    assert no_clones.problems
