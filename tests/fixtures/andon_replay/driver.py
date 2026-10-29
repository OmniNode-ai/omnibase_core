# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Generic replay driver for the andon replay corpus (OMN-21530, plan task T0.8a).

The corpus (``corpus.yaml``) is data: every repository, revision, path, line, rule
id, clone directory, environment variable name and timeout is a corpus field. This
module holds none of them. It loads the corpus, compares its finding ids with the
finding table the corpus snapshots, and resolves every input: a snapshot against
its sha256, a code input against a revision in a canonical clone.

The clone check runs when the clone root named by the corpus is set in the
environment. When the corpus's require-clones variable is also set, an
unreachable clone root is itself a problem, so a lab run cannot pass without
reading the clones. Without it the check is structural (full 40-hex revision,
short revision prefix, positive line) and the report says the clones were not read.
"""

from __future__ import annotations

import fnmatch
import functools
import hashlib
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

FIXTURE_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS_PATH = FIXTURE_DIR / "corpus.yaml"
CORPUS_FILE_NAME = DEFAULT_CORPUS_PATH.name
FULL_SHA_LENGTH = 40


class ModelResolution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    clone_root_env: str
    require_clones_env: str
    git_timeout_seconds: int = Field(gt=0)
    clone_dirs: dict[str, str]


class ModelFindings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    table_snapshot: str
    id_prefix: str
    class_column: int = Field(ge=0)
    not_mechanical_class: str
    not_mechanical: list[str]


class ModelSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: str
    path: str
    sha256: str
    provenance: dict[str, Any]


class ModelFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    role: str
    kind: Literal["git_file", "tree_glob", "revision"]
    repository: str
    revision: str
    path: str | None = None
    glob: str | None = None


class ModelInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["code", "text"]
    repository: str | None = None
    revision: str | None = None
    revision_short: str | None = None
    path: str | None = None
    line: int | None = Field(default=None, ge=1)
    quote: str | None = None
    snapshot: str | None = None
    facts: list[ModelFact] = Field(default_factory=list)


class ModelAssertion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: str
    finding: str
    rule_id: str
    input: ModelInput
    note: str | None = None


class ModelCorpus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int
    resolution: ModelResolution
    findings: ModelFindings
    snapshots: list[ModelSnapshot]
    assertions: list[ModelAssertion]


class ModelResolutionReport(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    problems: list[str] = Field(default_factory=list)
    snapshots_checked: int = 0
    code_inputs_total: int = 0
    code_inputs_structurally_checked: int = 0
    code_inputs_resolved_in_clones: int = 0
    clones_required: bool = False
    clones_reachable: bool = False


def load_raw(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: corpus root must be a mapping")
    return loaded


def load_corpus(path: Path) -> ModelCorpus:
    return ModelCorpus.model_validate(load_raw(path))


def write_raw(
    target_dir: Path,
    raw: Mapping[str, Any],
    copy_snapshots_from: Path | None = None,
) -> Path:
    """Write ``raw`` as a corpus file in ``target_dir``; optionally copy snapshots."""
    target_dir.mkdir(parents=True, exist_ok=True)
    if copy_snapshots_from is not None:
        for snap in raw.get("snapshots", []):
            source = copy_snapshots_from / snap["path"]
            destination = target_dir / snap["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    out = target_dir / CORPUS_FILE_NAME
    out.write_text(yaml.safe_dump(dict(raw), sort_keys=False), encoding="utf-8")
    return out


def environment(corpus: ModelCorpus) -> dict[str, str]:
    """The two process variables the corpus names, read through the typed bootstrap."""
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(
            corpus.resolution.clone_root_env,
            corpus.resolution.require_clones_env,
        )
    )
    return dict(bootstrap.environment.values)


def build_probe_corpus(
    raw: Mapping[str, Any],
    repository: str,
    revision: str,
    path: str,
    line: int,
    quote: str,
) -> ModelCorpus:
    """A one-assertion corpus over a scratch clone, for positive/negative controls."""
    probe = {
        "schema_version": raw["schema_version"],
        "resolution": raw["resolution"],
        "findings": raw["findings"],
        "snapshots": [],
        "assertions": [
            {
                "id": "probe",
                "finding": raw["findings"]["id_prefix"] + "00",
                "rule_id": "probe",
                "input": {
                    "kind": "code",
                    "repository": repository,
                    "revision": revision,
                    "path": path,
                    "line": line,
                    "quote": quote,
                },
            }
        ],
    }
    return ModelCorpus.model_validate(probe)


def _snapshot(corpus: ModelCorpus, snapshot_id: str) -> ModelSnapshot | None:
    for snap in corpus.snapshots:
        if snap.id == snapshot_id:
            return snap
    return None


def mechanical_finding_ids(corpus: ModelCorpus, base_dir: Path) -> list[str]:
    """Finding ids of the finding table whose class column is not the none marker."""
    snap = _snapshot(corpus, corpus.findings.table_snapshot)
    if snap is None:
        raise ValueError(f"finding table snapshot {corpus.findings.table_snapshot!r}")
    return [
        finding_id
        for finding_id, class_cell in _table_rows(corpus, base_dir / snap.path)
        if class_cell != corpus.findings.not_mechanical_class
    ]


def _table_rows(corpus: ModelCorpus, table: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for text in table.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in text.strip().strip("|").split("|")]
        prefix = corpus.findings.id_prefix
        if (
            len(cells) > corpus.findings.class_column
            and cells[0].startswith(prefix)
            and cells[0][len(prefix) :].isdigit()
        ):
            rows.append((cells[0], cells[corpus.findings.class_column]))
    return rows


def findings_problems(corpus: ModelCorpus, base_dir: Path) -> list[str]:
    """Compare the corpus's finding ids with the finding table."""
    problems: list[str] = []
    snap = _snapshot(corpus, corpus.findings.table_snapshot)
    if snap is None:
        return [f"finding table snapshot {corpus.findings.table_snapshot!r} missing"]
    rows = _table_rows(corpus, base_dir / snap.path)
    table_ids = [r[0] for r in rows]
    mechanical = {r[0] for r in rows if r[1] != corpus.findings.not_mechanical_class}
    excluded = {r[0] for r in rows if r[1] == corpus.findings.not_mechanical_class}
    covered = {a.finding for a in corpus.assertions}
    for finding_id in sorted(mechanical - covered):
        problems.append(f"{finding_id}: no assertion in the corpus")
    for finding_id in sorted(covered - set(table_ids)):
        problems.append(f"{finding_id}: assertion names a finding the table lacks")
    for finding_id in sorted(covered & excluded):
        problems.append(f"{finding_id}: not mechanical in the table, has an assertion")
    if set(corpus.findings.not_mechanical) != excluded:
        problems.append(
            f"not_mechanical {sorted(corpus.findings.not_mechanical)} differs from "
            f"the table's {sorted(excluded)}"
        )
    seen: set[str] = set()
    for assertion in corpus.assertions:
        if assertion.id in seen:
            problems.append(f"{assertion.id}: duplicate assertion id")
        seen.add(assertion.id)
        if not assertion.rule_id.strip():
            problems.append(f"{assertion.id}: empty rule_id")
    return problems


def assertions_naming(corpus: ModelCorpus, rule_id: str) -> list[str]:
    """Ids of the assertions that name ``rule_id`` (the set a disabled rule must fail)."""
    return [a.id for a in corpus.assertions if a.rule_id == rule_id]


def rule_ids(corpus: ModelCorpus) -> list[str]:
    """Every distinct rule id the corpus names, in first-use order."""
    return list(dict.fromkeys(a.rule_id for a in corpus.assertions))


def _is_full_sha(value: str | None) -> bool:
    if value is None or len(value) != FULL_SHA_LENGTH or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _structural_problems(corpus: ModelCorpus) -> tuple[list[str], int, int]:
    problems: list[str] = []
    total = 0
    checked = 0
    snapshot_ids = {s.id for s in corpus.snapshots}
    for assertion in corpus.assertions:
        item = assertion.input
        if item.kind == "text":
            if item.snapshot not in snapshot_ids:
                problems.append(f"{assertion.id}: snapshot {item.snapshot!r} unknown")
            continue
        total += 1
        before = len(problems)
        if item.repository not in corpus.resolution.clone_dirs:
            problems.append(f"{assertion.id}: repository {item.repository!r} unknown")
        if item.revision is None or not _is_full_sha(item.revision):
            problems.append(f"{assertion.id}: revision is not a full 40-hex sha")
        elif item.revision_short and not item.revision.startswith(item.revision_short):
            problems.append(f"{assertion.id}: revision does not extend revision_short")
        if not item.path or item.line is None or not item.quote:
            problems.append(f"{assertion.id}: code input needs path, line and quote")
        for fact in item.facts:
            if not _is_full_sha(fact.revision):
                problems.append(f"{assertion.id}: fact {fact.role} revision not full")
        if len(problems) == before:
            checked += 1
    return problems, total, checked


def _git(clone: Path, timeout: int, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(clone), *args],
        capture_output=True,
        check=False,
        timeout=timeout,
        env=scrub_git_location_env(),
    )


@functools.cache
def _commit_exists(clone: Path, revision: str, timeout: int) -> bool:
    done = _git(clone, timeout, "cat-file", "-e", f"{revision}^{{commit}}")
    return done.returncode == 0


def _clone_problems(corpus: ModelCorpus, clone_root: Path) -> tuple[list[str], int]:
    problems: list[str] = []
    resolved = 0
    timeout = corpus.resolution.git_timeout_seconds
    blobs: dict[tuple[str, str, str], list[str] | None] = {}

    def read(repository: str, revision: str, path: str) -> list[str] | None:
        key = (repository, revision, path)
        if key not in blobs:
            clone = clone_root / corpus.resolution.clone_dirs[repository]
            done = _git(clone, timeout, "show", f"{revision}:{path}")
            blobs[key] = (
                done.stdout.decode("utf-8", "replace").splitlines()
                if done.returncode == 0
                else None
            )
        return blobs[key]

    for assertion in corpus.assertions:
        item = assertion.input
        if item.kind != "code":
            continue
        if item.repository not in corpus.resolution.clone_dirs:
            continue
        clone = clone_root / corpus.resolution.clone_dirs[item.repository]
        if not clone.is_dir():
            problems.append(f"{assertion.id}: no clone at {clone.name}")
            continue
        before = len(problems)
        if not item.revision or not item.path or item.line is None or not item.quote:
            continue
        if not _commit_exists(clone, item.revision, timeout):
            problems.append(f"{assertion.id}: revision {item.revision} not in clone")
            continue
        lines = read(item.repository, item.revision, item.path)
        if lines is None:
            problems.append(f"{assertion.id}: {item.path} absent at {item.revision}")
        elif item.line > len(lines) or item.quote not in lines[item.line - 1]:
            problems.append(
                f"{assertion.id}: quote not at {item.path}:{item.line} "
                f"at {item.revision}"
            )
        for fact in item.facts:
            problems.extend(
                _fact_problems(corpus, clone_root, assertion.id, fact, read)
            )
        if len(problems) == before:
            resolved += 1
    return problems, resolved


def _fact_problems(
    corpus: ModelCorpus,
    clone_root: Path,
    assertion_id: str,
    fact: ModelFact,
    read: Any,
) -> list[str]:
    timeout = corpus.resolution.git_timeout_seconds
    clone = clone_root / corpus.resolution.clone_dirs.get(
        fact.repository, fact.repository
    )
    if not clone.is_dir():
        return [f"{assertion_id}: fact {fact.role} has no clone at {clone.name}"]
    if not _commit_exists(clone, fact.revision, timeout):
        return [
            f"{assertion_id}: fact {fact.role} revision {fact.revision} not in clone"
        ]
    if fact.kind == "git_file" and fact.path:
        if read(fact.repository, fact.revision, fact.path) is None:
            return [f"{assertion_id}: fact {fact.role} {fact.path} absent"]
    if fact.kind == "tree_glob" and fact.glob:
        listing = _git(clone, timeout, "ls-tree", "-r", "--name-only", fact.revision)
        names = listing.stdout.decode("utf-8", "replace").splitlines()
        if not any(fnmatch.fnmatch(n, fact.glob) for n in names):
            return [f"{assertion_id}: fact {fact.role} glob matches nothing"]
    return []


def resolve_inputs(
    corpus: ModelCorpus, base_dir: Path, env: Mapping[str, str]
) -> ModelResolutionReport:
    """Check snapshots against sha256 and code inputs against the clones."""
    report = ModelResolutionReport()
    for snap in corpus.snapshots:
        report.snapshots_checked += 1
        target = base_dir / snap.path
        if not target.is_file():
            report.problems.append(f"snapshot {snap.id}: {snap.path} missing")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != snap.sha256:
            report.problems.append(
                f"snapshot {snap.id}: sha256 {actual} differs from recorded {snap.sha256}"
            )
    structural, total, checked = _structural_problems(corpus)
    report.problems.extend(structural)
    report.code_inputs_total = total
    report.code_inputs_structurally_checked = checked
    root_value = env.get(corpus.resolution.clone_root_env, "")
    report.clones_required = bool(env.get(corpus.resolution.require_clones_env, ""))
    report.clones_reachable = bool(root_value) and Path(root_value).is_dir()
    if report.clones_reachable and report.clones_required:
        problems, resolved = _clone_problems(corpus, Path(root_value))
        report.problems.extend(problems)
        report.code_inputs_resolved_in_clones = resolved
    elif report.clones_required:
        report.problems.append(
            f"{corpus.resolution.require_clones_env} is set and "
            f"{corpus.resolution.clone_root_env} does not name a directory"
        )
    return report
