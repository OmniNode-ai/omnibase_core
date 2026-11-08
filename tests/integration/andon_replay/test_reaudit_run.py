# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The re-audit over the real clones (OMN-23157, plan D.4 stage 3).

With the corpus's clone root set, every configured repository head and every open wave pull request
named by the PR watcher state file is read; the report goes to the file the configuration's report
variable names, else to a scratch file. With the require-clones variable set a head that cannot be
read fails the run; without a clone root the report names every head as not read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.andon_replay import driver, reaudit

pytestmark = [pytest.mark.integration, pytest.mark.timeout(3600)]


def test_reaudit_run_writes_one_report(tmp_path: Path) -> None:
    config = reaudit.load_config()
    corpus = driver.load_corpus(driver.DEFAULT_CORPUS_PATH)
    env = reaudit.environment(config, corpus)
    contracts = driver.load_contracts(corpus, driver.repo_root(corpus))
    clone_root = env.get(corpus.resolution.clone_root_env, "")
    report = reaudit.reaudit(
        config,
        corpus,
        driver.DEFAULT_CORPUS_PATH.parent,
        contracts,
        Path(clone_root) if clone_root else tmp_path / "no-clones",
        reaudit.load_pr_state(env.get(config.wave.state_env, "")),
    )
    out = Path(env.get(config.report_env, "") or tmp_path / "reaudit.md")
    written = reaudit.write_report(report, config, out)
    text = written.read_text(encoding="utf-8")
    heads = {t.repository for t in report.targets if t.kind == "head"}
    unread = " ".join(report.not_read)
    # every configured head is either judged or named as not read
    assert all(repo in heads or repo in unread for repo in config.heads)
    if env.get(corpus.resolution.require_clones_env, ""):
        assert heads == set(config.heads), unread
        assert report.checkers_run == set(reaudit.replay_section(corpus).adapters)
    assert "## Stays with a reading audit" in text
