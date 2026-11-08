# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Re-audit over current heads (OMN-23157, validators plan D.4 stage 3).

The re-audit runs the replay corpus's checkers over tiny scratch clones, one per audited
repository, so each test reads a head it built itself. The scratch heads hold the checker's own
violation or clean fixture at the path a corpus assertion names; nothing here reads a real clone.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env
from tests.fixtures.andon_replay import driver, reaudit

pytestmark = pytest.mark.unit

ASSERTED_RULE = "handler_di:reflective_construction"
VIOLATION_FIXTURE = "violation_reflective_construction_getattr"
CLEAN_FIXTURE = "clean_reflective_construction"
FIXTURE_MODULE = "handlers/handler_x.py"


@pytest.fixture(scope="module")
def config() -> reaudit.ModelReauditConfig:
    return reaudit.load_config()


@pytest.fixture(scope="module")
def corpus() -> driver.ModelCorpus:
    return driver.load_corpus(driver.DEFAULT_CORPUS_PATH)


@pytest.fixture(scope="module")
def contracts(corpus: driver.ModelCorpus) -> dict[str, driver.ReplayContract]:
    return driver.load_contracts(corpus, driver.repo_root(corpus))


def _git(clone: Path, *args: str) -> str:
    done = subprocess.run(
        [
            "git",
            "-C",
            str(clone),
            "-c",
            "user.name=reaudit",
            "-c",
            "user.email=reaudit@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        capture_output=True,
        check=True,
        env=scrub_git_location_env(),
    )
    return done.stdout.decode().strip()


def _commit(clone: Path, files: dict[str, str], branch: str) -> str:
    if not (clone / ".git").exists():
        _git(clone.parent, "init", "-q", str(clone))
    for name, body in files.items():
        target = clone / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "--allow-empty", "-m", "scratch head")
    revision = _git(clone, "rev-parse", "HEAD")
    _git(clone, "update-ref", f"refs/remotes/{branch}", revision)
    return revision


def _fixture_text(corpus: driver.ModelCorpus, name: str) -> str:
    root = (
        driver.repo_root(corpus)
        / reaudit.replay_section(corpus).fixtures_dir
        / "handler_di"
        / name
    )
    return (root / FIXTURE_MODULE).read_text(encoding="utf-8")


def _asserted_path(corpus: driver.ModelCorpus) -> tuple[str, str]:
    assertion = next(a for a in corpus.assertions if a.rule_id == ASSERTED_RULE)
    assert assertion.input.repository and assertion.input.path
    return assertion.input.repository, assertion.input.path


def _heads(
    tmp_path: Path,
    corpus: driver.ModelCorpus,
    config: reaudit.ModelReauditConfig,
    asserted_body: str,
) -> Path:
    """One scratch clone per repository; the asserted file holds ``asserted_body``."""
    asserted_repo, asserted_path = _asserted_path(corpus)
    for repository, ref in config.heads.items():
        clone = tmp_path / corpus.resolution.clone_dirs[repository]
        clone.mkdir(parents=True)
        files = {"README.md": "scratch\n"}
        if repository == asserted_repo:
            files[asserted_path] = asserted_body
        _commit(clone, files, ref)
    return tmp_path


def _pr_state(
    tmp_path: Path, corpus: driver.ModelCorpus, revisions: dict[str, str]
) -> dict[str, Any]:
    """A watcher state naming scratch pull requests: key ``repo#n`` -> head sha and state."""
    prs: dict[str, Any] = {}
    for key, (revision, state) in {
        key: (value, "OPEN" if not key.endswith("!closed") else "CLOSED")
        for key, value in revisions.items()
    }.items():
        prs[key.removesuffix("!closed")] = {
            "facts": {"state": state, "head_sha": revision, "head_ref": "scratch"}
        }
    return prs


def _wave_numbers(config: reaudit.ModelReauditConfig, repository: str) -> list[int]:
    return config.wave.prs[repository]


def _run(
    config: reaudit.ModelReauditConfig,
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
    clone_root: Path,
    pr_state: dict[str, Any] | None,
    **kwargs: Any,
) -> reaudit.ModelReaudit:
    return reaudit.reaudit(
        config,
        corpus,
        driver.DEFAULT_CORPUS_PATH.parent,
        contracts,
        clone_root,
        pr_state,
        **kwargs,
    )


def test_reaudit_config_describes_every_checker(
    config: reaudit.ModelReauditConfig, corpus: driver.ModelCorpus
) -> None:
    assert reaudit.unconfigured_checkers(config, corpus) == []
    assert set(config.heads) == set(corpus.resolution.clone_dirs)
    assert set(config.wave.prs) <= set(corpus.resolution.clone_dirs)


def test_reaudit_runs_all_checkers(
    tmp_path: Path,
    config: reaudit.ModelReauditConfig,
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
) -> None:
    """One run: every checker, every repository head, every open wave pull request, one report."""
    clone_root = _heads(
        tmp_path / "clones", corpus, config, _fixture_text(corpus, CLEAN_FIXTURE)
    )
    core = clone_root / corpus.resolution.clone_dirs["omnibase_core"]
    market = clone_root / corpus.resolution.clone_dirs["omnimarket"]
    core_pr = _commit(core, {"pr.py": "VALUE = 1\n"}, "origin/scratch-core")
    market_pr = _commit(market, {"pr.py": "VALUE = 2\n"}, "origin/scratch-market")
    open_core = _wave_numbers(config, "omnibase_core")[0]
    open_market = _wave_numbers(config, "omnimarket")[0]
    closed_market = _wave_numbers(config, "omnimarket")[1]
    state = _pr_state(
        tmp_path,
        corpus,
        {
            f"omnibase_core#{open_core}": core_pr,
            f"omnimarket#{open_market}": market_pr,
            f"omnimarket#{closed_market}!closed": market_pr,
        },
    )
    calls: dict[str, list[str]] = {}

    def spy(checker: str) -> driver.Adapter:
        real = driver.load_adapter(corpus, checker)
        assert real is not None

        def adapter(run: driver.ReplayRun) -> Any:
            calls.setdefault(checker, []).append(run.source.path)
            return real(run)

        return adapter

    spies = {name: spy(name) for name in reaudit.replay_section(corpus).adapters}
    report = _run(config, corpus, contracts, clone_root, state, adapters=spies)

    heads = {f"{repo}@head" for repo in config.heads}
    prs = {f"omnibase_core#{open_core}", f"omnimarket#{open_market}"}
    assert {t.label for t in report.targets} == heads | prs
    assert f"omnimarket#{closed_market}" not in {t.label for t in report.targets}
    checkers = set(reaudit.replay_section(corpus).adapters)
    assert report.checkers_run == checkers
    assert {(r.target, r.checker) for r in report.runs} == {
        (t.label, c) for t in report.targets for c in checkers
    }
    # the run reached every checker through its adapter, not a stub of the report
    assert set(calls) == checkers
    # a pull request is judged on the files it changes against the head
    pr_paths = {r.target: r for r in report.runs if r.checker == "handler_di"}
    assert pr_paths[f"omnimarket#{open_market}"].files_judged == 1
    written = reaudit.write_report(report, config, tmp_path / "out" / "reaudit.md")
    text = written.read_text(encoding="utf-8")
    assert all(label in text for label in heads | prs)
    assert all(checker in text for checker in checkers)


def test_reaudit_runs_all_checkers_names_what_it_could_not_read(
    tmp_path: Path,
    config: reaudit.ModelReauditConfig,
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
) -> None:
    """Control: no clone and no pull request state is reported as not read, never as clean."""
    report = _run(config, corpus, contracts, tmp_path / "no-clones", None)
    assert report.targets == []
    assert report.runs == []
    named = " ".join(report.not_read)
    assert all(repo in named for repo in config.heads)
    assert config.wave.state_env in named


def test_reaudit_reports_by_rule_id(
    tmp_path: Path,
    config: reaudit.ModelReauditConfig,
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
) -> None:
    """A finding still present appears by its rule id; the same head fixed does not."""
    repository, path = _asserted_path(corpus)
    named = {
        a.finding
        for a in corpus.assertions
        if a.rule_id == ASSERTED_RULE
        and a.input.repository == repository
        and a.input.path == path
    }
    still = _heads(
        tmp_path / "still", corpus, config, _fixture_text(corpus, VIOLATION_FIXTURE)
    )
    present = _run(config, corpus, contracts, still, None, repositories=[repository])
    assert ASSERTED_RULE in {f.rule_id for f in present.still_present}
    assert {
        f.finding for f in present.still_present if f.rule_id == ASSERTED_RULE
    } == named
    assert f"### {ASSERTED_RULE}" in reaudit.render(present, config)

    fixed = _heads(
        tmp_path / "fixed", corpus, config, _fixture_text(corpus, CLEAN_FIXTURE)
    )
    clean = _run(config, corpus, contracts, fixed, None, repositories=[repository])
    assert ASSERTED_RULE not in {f.rule_id for f in clean.still_present}
    assert ASSERTED_RULE not in reaudit.render(clean, config)
    assert clean.fixed_count > 0
    assert clean.fixed_count + len(clean.still_present) >= len(present.still_present)


def test_reaudit_reports_by_rule_id_fails_when_the_checker_goes_quiet(
    tmp_path: Path,
    config: reaudit.ModelReauditConfig,
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
) -> None:
    """Injected break: a handler_di adapter that reports nothing hides the finding."""
    repository, _ = _asserted_path(corpus)
    still = _heads(
        tmp_path / "quiet", corpus, config, _fixture_text(corpus, VIOLATION_FIXTURE)
    )
    report = _run(
        config,
        corpus,
        contracts,
        still,
        None,
        repositories=[repository],
        adapters={"handler_di": lambda _run: ()},
    )
    assert ASSERTED_RULE not in {f.rule_id for f in report.still_present}


def test_reaudit_reading_audit_remainder(
    tmp_path: Path,
    config: reaudit.ModelReauditConfig,
    corpus: driver.ModelCorpus,
    contracts: dict[str, driver.ReplayContract],
) -> None:
    """The reading audit holds F02, F13, F42's exception call and F43's ticket fit, no others."""
    assert reaudit.reading_audit_problems(config, corpus) == []
    still = _heads(
        tmp_path / "heads", corpus, config, _fixture_text(corpus, VIOLATION_FIXTURE)
    )
    report = _run(
        config, corpus, contracts, still, None, repositories=["omnibase_core"]
    )
    assert report.still_present, (
        "the section must not borrow from findings still present"
    )
    assert [(r.finding, r.part) for r in report.reading_audit] == [
        ("F02", "whole"),
        ("F13", "whole"),
        ("F42", "exception call"),
        ("F43", "ticket fit"),
    ]
    section = reaudit.render(report, config).split("## Stays with a reading audit")[1]
    section = section.split("\n## ")[0]
    assert re.findall(r"F\d+", section) == ["F02", "F13", "F42", "F43"]
    assert report.snapshot_only, "text snapshots are named apart from the reading audit"
    assert not set(report.snapshot_only) & set(section.split())


def test_reaudit_reading_audit_remainder_refuses_a_fifth_finding(
    config: reaudit.ModelReauditConfig, corpus: driver.ModelCorpus
) -> None:
    """Control: a remainder with an extra whole finding, or a missing one, is refused."""
    extra = config.model_copy(
        update={
            "reading_audit": [
                *config.reading_audit,
                reaudit.ModelReadingAudit(finding="F20", part="whole", why="planted"),
            ]
        }
    )
    assert reaudit.reading_audit_problems(extra, corpus) != []
    missing = config.model_copy(update={"reading_audit": config.reading_audit[1:]})
    assert reaudit.reading_audit_problems(missing, corpus) != []


def test_reaudit_pr_state_reader_reads_the_watcher_prs(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps({"prs": {"a#1": {"facts": {"state": "OPEN"}}}}), encoding="utf-8"
    )
    assert reaudit.load_pr_state(str(state)) == {"a#1": {"facts": {"state": "OPEN"}}}
    assert reaudit.load_pr_state("") is None
    assert reaudit.load_pr_state(str(tmp_path / "absent.json")) is None
