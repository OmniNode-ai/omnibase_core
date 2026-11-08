# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Re-audit of the canon-audit findings over current heads (OMN-23157, plan D.4 stage 3).

One run judges the current head of each audited repository and the head of every audited pull
request that is still open, with every checker the replay corpus has an adapter for, and writes
one report. It reuses the replay driver (OMN-21530): the corpus, the adapters and the contracts
are the driver's, so a checker is run here exactly as the integrated replay runs it.

Two reads per target:

* the corpus assertions of the target's repository, replayed at the target's revision. An
  assertion whose rule id is reported there is a D.3 finding still present and appears in the
  report by that rule id; one that is not reported there is fixed and does not appear;
* a tree scan: each checker whose configuration says ``tree`` judges every file of a repository
  head that its contract scopes, and of a pull request head the files it changes against the
  repository head, so a finding D.3 never named still shows.

Every repository, ref, pull request number, checker name, scan mode and reading-audit remainder
is ``reaudit.yaml`` data. This module holds none of them.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env
from tests.fixtures.andon_replay import driver

DEFAULT_CONFIG_PATH = driver.FIXTURE_DIR / "reaudit.yaml"


class ModelWave(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    state_env: str
    open_state: str
    prs: dict[str, list[int]]


class ModelCheckerScan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    scan: Literal["tree", "assertion"]
    globs: list[str] = Field(default_factory=list)


class ModelReadingAudit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    finding: str
    part: str
    why: str


class ModelReauditConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int
    corpus: str
    heads: dict[str, str]
    wave: ModelWave
    checkers: dict[str, ModelCheckerScan]
    reading_audit: list[ModelReadingAudit]
    listed_per_rule: int = Field(gt=0)
    report_env: str


class ModelTarget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str
    kind: Literal["head", "pr"]
    label: str
    revision: str


class ModelStillPresent(BaseModel):
    """A D.3 finding the checker that owns its rule id still reports at a target."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    finding: str
    rule_id: str
    assertion_id: str
    target: str
    revision: str
    path: str
    line: int | None
    detail: str


class ModelScanned(BaseModel):
    """One finding of a tree scan."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target: str
    checker: str
    rule: str
    path: str
    line: int | None


class ModelCheckerRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target: str
    checker: str
    mode: Literal["tree", "assertion"]
    files_judged: int
    assertions_judged: int


class ModelReaudit(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    targets: list[ModelTarget] = Field(default_factory=list)
    checkers_without_adapter: list[str] = Field(default_factory=list)
    runs: list[ModelCheckerRun] = Field(default_factory=list)
    still_present: list[ModelStillPresent] = Field(default_factory=list)
    fixed_count: int = 0
    scanned: list[ModelScanned] = Field(default_factory=list)
    reading_audit: list[ModelReadingAudit] = Field(default_factory=list)
    snapshot_only: list[str] = Field(default_factory=list)
    not_read: list[str] = Field(default_factory=list)

    @property
    def checkers_run(self) -> set[str]:
        return {r.checker for r in self.runs}


def replay_section(corpus: driver.ModelCorpus) -> driver.ModelReplay:
    """The corpus's replay section; a corpus without one cannot be replayed."""
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    return corpus.replay


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> ModelReauditConfig:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ModelReauditConfig.model_validate(loaded)


def _run_git(
    clone: Path, timeout: int, *args: str
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(clone), *args],
        capture_output=True,
        check=False,
        timeout=timeout,
        env=scrub_git_location_env(),
    )


def _resolve(clone: Path, timeout: int, ref: str) -> str | None:
    done = _run_git(clone, timeout, "rev-parse", "--verify", f"{ref}^{{commit}}")
    return done.stdout.decode().strip() if done.returncode == 0 else None


def load_pr_state(path_value: str) -> dict[str, Any] | None:
    """The PR watcher state's ``prs`` mapping; None when no readable file is named."""
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    prs = loaded.get("prs") if isinstance(loaded, dict) else None
    return prs if isinstance(prs, dict) else None


def resolve_targets(
    config: ModelReauditConfig,
    corpus: driver.ModelCorpus,
    clone_root: Path,
    pr_state: Mapping[str, Any] | None,
    repositories: Sequence[str] | None = None,
) -> tuple[list[ModelTarget], list[str]]:
    """The current head of each repository and the head of each open wave pull request.

    The second value lists every target that could not be resolved, with the reason.
    """
    timeout = corpus.resolution.git_timeout_seconds
    targets: list[ModelTarget] = []
    not_read: list[str] = []
    for repository, ref in config.heads.items():
        if repositories is not None and repository not in repositories:
            continue
        clone = clone_root / corpus.resolution.clone_dirs.get(repository, repository)
        revision = _resolve(clone, timeout, ref) if clone.is_dir() else None
        if revision is None:
            not_read.append(f"{repository} head {ref}: not readable in {clone.name}")
            continue
        targets.append(
            ModelTarget(
                repository=repository,
                kind="head",
                label=f"{repository}@head",
                revision=revision,
            )
        )
    for repository, numbers in config.wave.prs.items():
        if repositories is not None and repository not in repositories:
            continue
        if pr_state is None:
            not_read.append(
                f"{repository} wave pull requests: no pull request state "
                f"({config.wave.state_env} names no readable file)"
            )
            continue
        clone_name = corpus.resolution.clone_dirs.get(repository, repository)
        clone = clone_root / clone_name
        for number in numbers:
            record = pr_state.get(f"{repository}#{number}") or pr_state.get(
                f"{clone_name}#{number}"
            )
            facts = (record or {}).get("facts") or {}
            if facts.get("state") != config.wave.open_state:
                continue
            revision = None
            if clone.is_dir():
                revision = _resolve(clone, timeout, str(facts.get("head_sha", ""))) or (
                    _resolve(clone, timeout, f"origin/{facts.get('head_ref', '')}")
                )
            if revision is None:
                not_read.append(
                    f"{repository}#{number}: open, head not readable in {clone_name}"
                )
                continue
            targets.append(
                ModelTarget(
                    repository=repository,
                    kind="pr",
                    label=f"{repository}#{number}",
                    revision=revision,
                )
            )
    return targets, not_read


def _heads_by_repository(targets: Sequence[ModelTarget]) -> dict[str, str]:
    return {t.repository: t.revision for t in targets if t.kind == "head"}


def at_target(
    assertion: driver.ModelAssertion, target: ModelTarget, heads: Mapping[str, str]
) -> driver.ModelAssertion:
    """The assertion as it reads at ``target``: its input and the facts of its own repository
    at the target's revision, the facts of another repository at that repository's head."""
    item = assertion.input
    facts = [
        fact.model_copy(
            update={
                "revision": target.revision
                if fact.repository == target.repository
                else heads.get(fact.repository, fact.revision)
            }
        )
        for fact in item.facts
    ]
    moved = item.model_copy(
        update={"revision": target.revision, "revision_short": None, "facts": facts}
    )
    return assertion.model_copy(update={"input": moved})


@dataclass
class RevisionTree:
    """The files of one revision of a clone, read once through ``git cat-file --batch``."""

    clone: Path
    revision: str
    timeout: int
    _names: list[str] | None = None
    _blobs: dict[str, str | None] | None = None

    def names(self) -> list[str]:
        if self._names is None:
            done = _run_git(
                self.clone, self.timeout, "ls-tree", "-r", "--name-only", self.revision
            )
            self._names = done.stdout.decode("utf-8", "replace").splitlines()
        return self._names

    def prefetch(self, paths: Sequence[str]) -> None:
        wanted = [p for p in paths if p not in (self._blobs or {})]
        if self._blobs is None:
            self._blobs = {}
        if not wanted:
            return
        request = "".join(f"{self.revision}:{p}\n" for p in wanted).encode()
        done = subprocess.run(
            ["git", "-C", str(self.clone), "cat-file", "--batch"],
            input=request,
            capture_output=True,
            check=False,
            timeout=max(self.timeout, len(wanted)),
            env=scrub_git_location_env(),
        )
        out = done.stdout
        cursor = 0
        for path in wanted:
            newline = out.index(b"\n", cursor)
            header = out[cursor:newline].decode("utf-8", "replace").split()
            cursor = newline + 1
            if len(header) == 3 and header[1] == "blob":
                size = int(header[2])
                self._blobs[path] = out[cursor : cursor + size].decode(
                    "utf-8", "replace"
                )
                cursor += size + 1
            else:
                self._blobs[path] = None

    def text(self, path: str) -> str | None:
        if self._blobs is None or path not in self._blobs:
            self.prefetch([path])
        return (self._blobs or {}).get(path)


def tree_source(tree: RevisionTree, path: str) -> driver.ReplaySource:
    """A bare tree path as a replay source: no line and no fact bundle."""
    return driver.ReplaySource(
        path=path,
        line=None,
        text=tree.text,
        names=tree.names,
        fact_text=lambda _role: None,
        fact_names=lambda _role: [],
        fact_revision=lambda _role: None,
    )


def _issue_path(issue: ModelValidationIssue, fallback: str) -> str:
    return str(issue.file_path) if issue.file_path else fallback


def _changed_paths(
    clone: Path, timeout: int, base: str | None, revision: str
) -> set[str]:
    """Files a pull request head adds or changes against the repository's current head."""
    if base is None:
        return set()
    done = _run_git(
        clone, timeout, "diff", "--name-only", "--diff-filter=d", f"{base}...{revision}"
    )
    return set(done.stdout.decode("utf-8", "replace").splitlines())


def _scan_paths(
    scan: ModelCheckerScan, contract: driver.ReplayContract | None, names: Sequence[str]
) -> list[str]:
    if contract is not None:
        return [n for n in names if driver.in_scope(contract, n)]
    return [n for n in names if any(fnmatch.fnmatch(n, g) for g in scan.globs)]


def _judge(
    adapter: driver.Adapter, run: driver.ReplayRun
) -> Sequence[ModelValidationIssue]:
    try:
        return adapter(run)
    except ModelOnexError:
        # a checker that refuses its contract reports nothing
        return ()


def reaudit(
    config: ModelReauditConfig,
    corpus: driver.ModelCorpus,
    base_dir: Path,
    contracts: Mapping[str, driver.ReplayContract],
    clone_root: Path,
    pr_state: Mapping[str, Any] | None,
    repositories: Sequence[str] | None = None,
    adapters: Mapping[str, driver.Adapter] | None = None,
    on_target: Callable[[ModelTarget], None] | None = None,
) -> ModelReaudit:
    """Run every checker over the targets and collect the one report.

    ``adapters`` replaces the corpus's adapters by checker id (the tests' injected breaks).
    """
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    report = ModelReaudit(reading_audit=list(config.reading_audit))
    targets, report.not_read = resolve_targets(
        config, corpus, clone_root, pr_state, repositories
    )
    report.targets = targets
    heads = _heads_by_repository(targets)
    timeout = corpus.resolution.git_timeout_seconds
    checkers = sorted(corpus.replay.adapters)
    report.checkers_without_adapter = sorted(
        c for c in contracts if c not in corpus.replay.adapters
    )
    adapter_of: dict[str, driver.Adapter] = {}
    for checker in checkers:
        loaded = (adapters or {}).get(checker) or driver.load_adapter(corpus, checker)
        if loaded is not None:
            adapter_of[checker] = loaded
    report.snapshot_only = [a.id for a in corpus.assertions if a.input.kind == "text"]
    for target in targets:
        if on_target is not None:
            on_target(target)
        clone = clone_root / corpus.resolution.clone_dirs.get(
            target.repository, target.repository
        )
        own = [
            a
            for a in corpus.assertions
            if a.input.kind == "code" and a.input.repository == target.repository
        ]
        judged: Counter[str] = Counter()
        for assertion in own:
            owner = driver.owner_of(corpus, contracts, assertion.rule_id)
            moved = at_target(assertion, target, heads)
            source = driver.clone_source(corpus, base_dir, clone_root, moved)
            if source is None:
                report.not_read.append(
                    f"{assertion.id} at {target.label}: input not readable"
                )
                continue
            if owner is None or owner not in adapter_of:
                report.not_read.append(
                    f"{assertion.id} at {target.label}: no checker adapter for {assertion.rule_id}"
                )
                continue
            judged[owner] += 1
            run = driver.ReplayRun(
                validator_id=owner,
                contract=contracts.get(owner),
                source=source,
                rule_id=assertion.rule_id,
            )
            issues = _judge(adapter_of[owner], run)
            reported = driver.reported_ids(corpus, owner, issues)
            if assertion.rule_id in reported:
                located = next((i for i in issues if i.code or i.rule_name), None)
                report.still_present.append(
                    ModelStillPresent(
                        finding=assertion.finding,
                        rule_id=assertion.rule_id,
                        assertion_id=assertion.id,
                        target=target.label,
                        revision=target.revision,
                        path=_issue_path(located, moved.input.path or "")
                        if located
                        else (moved.input.path or ""),
                        line=located.line_number if located else moved.input.line,
                        detail="; ".join(
                            f"{i.code or i.rule_name}@{i.file_path}:{i.line_number}"
                            for i in issues
                        ),
                    )
                )
            else:
                report.fixed_count += 1
        tree = RevisionTree(clone, target.revision, timeout)
        changed = (
            _changed_paths(
                clone, timeout, heads.get(target.repository), target.revision
            )
            if target.kind == "pr"
            else None
        )
        for checker in checkers:
            if checker not in adapter_of:
                continue
            mode = (
                config.checkers[checker].scan
                if checker in config.checkers
                else "assertion"
            )
            files = 0
            if mode == "tree":
                paths = _scan_paths(
                    config.checkers[checker], contracts.get(checker), tree.names()
                )
                if changed is not None:
                    paths = [p for p in paths if p in changed]
                tree.prefetch(paths)
                for path in paths:
                    if tree.text(path) is None:
                        continue
                    files += 1
                    run = driver.ReplayRun(
                        validator_id=checker,
                        contract=contracts.get(checker),
                        source=tree_source(tree, path),
                    )
                    for issue in _judge(adapter_of[checker], run):
                        report.scanned.append(
                            ModelScanned(
                                target=target.label,
                                checker=checker,
                                rule=issue.code or issue.rule_name or checker,
                                path=_issue_path(issue, path),
                                line=issue.line_number,
                            )
                        )
            report.runs.append(
                ModelCheckerRun(
                    target=target.label,
                    checker=checker,
                    mode=mode,
                    files_judged=files,
                    assertions_judged=judged[checker],
                )
            )
    return report


def environment(
    config: ModelReauditConfig, corpus: driver.ModelCorpus
) -> dict[str, str]:
    """The process variables the run reads, all named by the corpus and the configuration."""
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(
            corpus.resolution.clone_root_env,
            corpus.resolution.require_clones_env,
            config.wave.state_env,
            config.report_env,
        )
    )
    return dict(bootstrap.environment.values)


def reading_audit_problems(
    config: ModelReauditConfig, corpus: driver.ModelCorpus
) -> list[str]:
    """The reading-audit remainder must be the table's not-mechanical findings plus the
    listed halves of findings the corpus covers in part, and nothing else."""
    problems: list[str] = []
    listed = [r.finding for r in config.reading_audit]
    if len(set(listed)) != len(listed):
        problems.append("a finding is listed twice")
    covered = {a.finding for a in corpus.assertions}
    whole = {r.finding for r in config.reading_audit if r.part == "whole"}
    partial = {r.finding for r in config.reading_audit if r.part != "whole"}
    if whole != set(corpus.findings.not_mechanical):
        problems.append(
            f"whole findings {sorted(whole)} differ from the table's "
            f"not-mechanical {sorted(corpus.findings.not_mechanical)}"
        )
    for finding in sorted(partial - covered):
        problems.append(f"{finding}: a partial remainder of a finding the corpus lacks")
    return problems


def unconfigured_checkers(
    config: ModelReauditConfig, corpus: driver.ModelCorpus
) -> list[str]:
    """Checkers the corpus has an adapter for and the configuration does not describe."""
    adapters = corpus.replay.adapters if corpus.replay else {}
    return sorted(set(adapters) - set(config.checkers))


def render(report: ModelReaudit, config: ModelReauditConfig) -> str:
    """The one report, as markdown."""
    lines: list[str] = ["# Re-audit report", ""]
    lines += ["## Targets", ""]
    lines += [f"- {t.label} {t.revision}" for t in report.targets] or ["- none"]
    lines += ["", "## Checkers run", ""]
    by_checker: dict[str, list[ModelCheckerRun]] = defaultdict(list)
    for run in report.runs:
        by_checker[run.checker].append(run)
    for checker in sorted(by_checker):
        runs = by_checker[checker]
        lines.append(
            f"- {checker} ({runs[0].mode}): {len(runs)} targets, "
            f"{sum(r.files_judged for r in runs)} files, "
            f"{sum(r.assertions_judged for r in runs)} assertions"
        )
    if report.checkers_without_adapter:
        lines += ["", "Contracts with no replay adapter (not run here):", ""]
        lines += [f"- {c}" for c in report.checkers_without_adapter]
    lines += ["", "## Findings of the audit still present", ""]
    if report.still_present:
        by_rule: dict[str, list[ModelStillPresent]] = defaultdict(list)
        for found in report.still_present:
            by_rule[found.rule_id].append(found)
        for rule_id in sorted(by_rule):
            lines.append(f"### {rule_id}")
            lines += [
                f"- {f.finding} at {f.target} {f.path}:{f.line}"
                for f in by_rule[rule_id]
            ]
    else:
        lines.append("none")
    lines += ["", f"Findings no longer reported: {report.fixed_count}", ""]
    lines += ["## Tree scan findings", ""]
    counts: Counter[tuple[str, str]] = Counter(
        (s.checker, s.rule) for s in report.scanned
    )
    if counts:
        for (checker, rule), count in sorted(counts.items()):
            lines.append(f"### {checker}: {rule} ({count})")
            shown = [
                s for s in report.scanned if (s.checker, s.rule) == (checker, rule)
            ]
            lines += [
                f"- {s.target} {s.path}:{s.line}"
                for s in shown[: config.listed_per_rule]
            ]
    else:
        lines.append("none")
    lines += ["", "## Stays with a reading audit", ""]
    lines += [f"- {r.finding} ({r.part}): {r.why}" for r in report.reading_audit]
    lines += ["", "## Not re-audited at a head", ""]
    lines.append(
        f"{len(report.snapshot_only)} assertions are frozen text snapshots of tickets, "
        "briefs and plans; a head does not carry them."
    )
    lines += ["", "## Not read", ""]
    lines += [f"- {n}" for n in report.not_read] or ["none"]
    return "\n".join(lines) + "\n"


def write_report(
    report: ModelReaudit, config: ModelReauditConfig, target: Path
) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(report, config), encoding="utf-8")
    return target
