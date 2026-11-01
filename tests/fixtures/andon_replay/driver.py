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
import importlib
import shutil
import subprocess
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
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
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


class ModelAdapter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    module: str
    function: str
    fixture_function: str | None = None


class ModelReplay(BaseModel):
    """How the integrated replay finds contracts, fixtures and per-checker adapters."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contracts_glob: str
    repo_root_from_fixture: str
    fixtures_dir: str
    fixture_prefix: str
    expected_assertions: int = Field(gt=0)
    row_name_parameters: list[str]
    validator_aliases: dict[str, str]
    adapters: dict[str, ModelAdapter]


class ModelCorpus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int
    resolution: ModelResolution
    replay: ModelReplay | None = None
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


# ---------------------------------------------------------------------------
# Integrated replay (OMN-21530, plan task T0.8b)
#
# The replay step builds one source per assertion (the audited revision read from
# the canonical clone, or the text snapshot), hands it with the checker's contract to
# the adapter the corpus names for that checker, and collects the rule ids the checker
# reports. Which checker owns a rule id, which adapter calls it and how a rule id is
# spelled are corpus and contract data; the code below holds none of them.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayContract:
    """One ``.validation.yaml`` as the replay reads it."""

    path: Path
    validator_id: str
    subcontract: ModelValidatorSubcontract

    @property
    def rules(self) -> dict[str, ModelValidatorRule]:
        return {r.rule_id: r for r in self.subcontract.rules}


@dataclass(frozen=True)
class ReplaySource:
    """The files one checker run may read: a revision of a clone, or a local tree.

    ``text(path)`` is the content at ``path`` (None when absent), ``names()`` every
    path of the tree, ``fact_text(role)`` and ``fact_names(role)`` the same for the
    fact the assertion's input bundle names under ``role``.
    """

    path: str
    line: int | None
    text: Callable[[str], str | None]
    names: Callable[[], list[str]]
    fact_text: Callable[[str], str | None]
    fact_names: Callable[[str], list[str]]
    fact_revision: Callable[[str], str | None]


@dataclass(frozen=True)
class ReplayRun:
    """What an adapter is handed: the owning contract, the source to judge and the asserted rule id."""

    validator_id: str
    contract: ReplayContract | None
    source: ReplaySource
    rule_id: str = ""


Adapter = Callable[[ReplayRun], Sequence[ModelValidationIssue]]


class ModelReplayResult(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    assertion_id: str
    expected: str
    validator_id: str | None
    reported: list[str] = Field(default_factory=list)
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.expected in self.reported


def repo_root(corpus: ModelCorpus) -> Path:
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    return (FIXTURE_DIR / corpus.replay.repo_root_from_fixture).resolve()


def in_scope(contract: ReplayContract, path: str) -> bool:
    """The contract's own scope test, as the validator base applies it to a path."""
    sub = contract.subcontract
    rooted = f"/{path}"
    if any(fnmatch.fnmatch(rooted, p) for p in sub.exclude_patterns):
        return False
    return any(fnmatch.fnmatch(rooted, p) for p in sub.target_patterns)


def load_contracts(corpus: ModelCorpus, root: Path) -> dict[str, ReplayContract]:
    """Every contract the corpus's glob finds under ``root``, by validator id."""
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    contracts: dict[str, ReplayContract] = {}
    for path in sorted(root.glob(corpus.replay.contracts_glob)):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        body = loaded.get("validation", loaded)
        sub = ModelValidatorSubcontract.model_validate(body)
        contracts[body["validator_id"]] = ReplayContract(
            path, body["validator_id"], sub
        )
    return contracts


def owner_of(
    corpus: ModelCorpus, contracts: Mapping[str, ReplayContract], rule_id: str
) -> str | None:
    """The validator id that owns ``rule_id``: its prefix (after aliasing), else the one
    contract that holds a row of that name, else the alias of the bare id, else None."""
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    aliases = corpus.replay.validator_aliases
    prefix = rule_id.split(":", 1)[0] if ":" in rule_id else None
    candidates = [aliases.get(prefix, prefix)] if prefix else []
    candidates.append(aliases.get(rule_id, ""))
    for candidate in candidates:
        if candidate in contracts or candidate in corpus.replay.adapters:
            return candidate
    holders = [v for v, c in contracts.items() if rule_id in c.rules]
    return holders[0] if len(holders) == 1 else None


def row_of(
    corpus: ModelCorpus, contract: ReplayContract | None, rule_id: str
) -> str | None:
    """The row of ``contract`` a corpus rule id names: the id itself, its part after the
    checker prefix, or the row whose parameter (one the corpus lists) holds that part."""
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    if contract is None:
        return None
    rows = contract.rules
    tail = rule_id.split(":", 1)[-1]
    for name in (rule_id, tail):
        if name in rows:
            return name
    for name, row in rows.items():
        params = row.parameters or {}
        if any(params.get(key) == tail for key in corpus.replay.row_name_parameters):
            return name
    return None


def reported_ids(
    corpus: ModelCorpus, validator_id: str, issues: Sequence[ModelValidationIssue]
) -> list[str]:
    """The spellings under which a corpus can name what a checker reported: a rule name
    bare or behind the checker's id or one of its aliases, and the checker's own id (and
    its aliases) when it reported anything, for a corpus id that names a checker."""
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    prefixes = [validator_id] + [
        alias
        for alias, target in corpus.replay.validator_aliases.items()
        if target == validator_id
    ]
    spelled: list[str] = []
    for issue in issues:
        for name in (issue.code, issue.rule_name):
            if name:
                spelled.append(name)
                spelled.extend(f"{prefix}:{name}" for prefix in prefixes)
    if issues:
        spelled.extend(prefixes)
    return list(dict.fromkeys(spelled))


def _clone_dir(corpus: ModelCorpus, clone_root: Path, repository: str) -> Path:
    return clone_root / corpus.resolution.clone_dirs.get(repository, repository)


def _fact_by_role(item: ModelInput, role: str) -> ModelFact | None:
    return next((f for f in item.facts if f.role == role), None)


@functools.cache
def _git_text(clone: Path, timeout: int, revision: str, path: str) -> str | None:
    done = _git(clone, timeout, "show", f"{revision}:{path}")
    return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else None


@functools.cache
def _git_names_cached(clone: Path, timeout: int, revision: str) -> tuple[str, ...]:
    done = _git(clone, timeout, "ls-tree", "-r", "--name-only", revision)
    return tuple(done.stdout.decode("utf-8", "replace").splitlines())


def _git_names(clone: Path, timeout: int, revision: str) -> list[str]:
    return list(_git_names_cached(clone, timeout, revision))


def clone_source(
    corpus: ModelCorpus, base_dir: Path, clone_root: Path, assertion: ModelAssertion
) -> ReplaySource | None:
    """The source of one assertion; None when its clone or snapshot is not readable."""
    timeout = corpus.resolution.git_timeout_seconds
    item = assertion.input
    if item.kind == "text":
        snap = _snapshot(corpus, item.snapshot or "")
        if snap is None or not (base_dir / snap.path).is_file():
            return None
        body = (base_dir / snap.path).read_text(encoding="utf-8")
        return ReplaySource(
            path=snap.path,
            line=None,
            text=lambda _path: body,
            names=lambda: [snap.path],
            fact_text=lambda _role: None,
            fact_names=lambda _role: [],
            fact_revision=lambda _role: None,
        )
    clone = _clone_dir(corpus, clone_root, item.repository or "")
    if not clone.is_dir() or not item.revision or not item.path:
        return None
    revision = item.revision
    if not _commit_exists(clone, revision, timeout):
        return None

    def fact_clone(role: str) -> tuple[Path, ModelFact] | None:
        fact = _fact_by_role(item, role)
        if fact is None:
            return None
        where = _clone_dir(corpus, clone_root, fact.repository)
        return (where, fact) if where.is_dir() else None

    def fact_text(role: str) -> str | None:
        found = fact_clone(role)
        if found is None or not found[1].path:
            return None
        return _git_text(found[0], timeout, found[1].revision, found[1].path)

    def fact_names(role: str) -> list[str]:
        found = fact_clone(role)
        return [] if found is None else _git_names(found[0], timeout, found[1].revision)

    def fact_revision(role: str) -> str | None:
        fact = _fact_by_role(item, role)
        return None if fact is None else fact.revision

    return ReplaySource(
        path=item.path,
        line=item.line,
        text=lambda path: _git_text(clone, timeout, revision, path),
        names=lambda: _git_names(clone, timeout, revision),
        fact_text=fact_text,
        fact_names=fact_names,
        fact_revision=fact_revision,
    )


def directory_source(root: Path, relative: str) -> ReplaySource:
    """A checker's own fixture: a local tree, judged at ``relative`` under ``root``."""

    def text(path: str) -> str | None:
        target = root / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    return ReplaySource(
        path=relative,
        line=None,
        text=text,
        names=lambda: sorted(
            p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
        ),
        fact_text=lambda _role: None,
        fact_names=lambda _role: [],
        fact_revision=lambda _role: None,
    )


def load_adapter(corpus: ModelCorpus, validator_id: str) -> Adapter | None:
    if corpus.replay is None or validator_id not in corpus.replay.adapters:
        return None
    named = corpus.replay.adapters[validator_id]
    adapter: Adapter = getattr(importlib.import_module(named.module), named.function)
    return adapter


def rule_fixtures(
    corpus: ModelCorpus, root: Path, validator_id: str, rule_id: str
) -> list[Path]:
    """The checker's own violation fixtures of one rule row (files or directories)."""
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    home = root / corpus.replay.fixtures_dir / validator_id
    stem = corpus.replay.fixture_prefix + rule_id
    return (
        sorted(p for p in home.glob("*") if p.name.startswith(stem))
        if home.is_dir()
        else []
    )


FixtureAdapter = Callable[[ReplayContract, Path], Sequence[ModelValidationIssue]]


def load_fixture_adapter(
    corpus: ModelCorpus, validator_id: str
) -> FixtureAdapter | None:
    if corpus.replay is None or validator_id not in corpus.replay.adapters:
        return None
    named = corpus.replay.adapters[validator_id]
    if named.fixture_function is None:
        return None
    adapter: FixtureAdapter = getattr(
        importlib.import_module(named.module), named.fixture_function
    )
    return adapter


def replay_assertion(
    corpus: ModelCorpus,
    contracts: Mapping[str, ReplayContract],
    assertion: ModelAssertion,
    source: ReplaySource,
) -> ModelReplayResult:
    """Call the checker that owns the assertion's rule id; the rule ids it reports."""
    owner = owner_of(corpus, contracts, assertion.rule_id)
    result = ModelReplayResult(
        assertion_id=assertion.id, expected=assertion.rule_id, validator_id=owner
    )
    if owner is None:
        result.detail = "no checker owns this rule id"
        return result
    adapter = load_adapter(corpus, owner)
    if adapter is None:
        result.detail = f"no adapter for checker {owner}"
        return result
    try:
        issues = adapter(
            ReplayRun(
                validator_id=owner,
                contract=contracts.get(owner),
                source=source,
                rule_id=assertion.rule_id,
            )
        )
    except ModelOnexError as refusal:
        # a checker that refuses its contract reports nothing: the assertion is not met
        result.detail = f"checker refused: {refusal.message}"
        return result
    result.reported = reported_ids(corpus, owner, issues)
    result.detail = "; ".join(
        f"{i.code or i.rule_name}@{i.file_path}:{i.line_number}" for i in issues
    )
    return result


def replay(
    corpus: ModelCorpus,
    base_dir: Path,
    env: Mapping[str, str],
    contracts: Mapping[str, ReplayContract],
    only: Callable[[ModelAssertion], bool] = lambda _a: True,
) -> tuple[list[ModelReplayResult], list[str]]:
    """Replay the selected assertions; the second value lists those not replayable
    here (clone or snapshot unreadable) with the reason."""
    clone_root_value = env.get(corpus.resolution.clone_root_env, "")
    clone_root = Path(clone_root_value) if clone_root_value else None
    results: list[ModelReplayResult] = []
    unreadable: list[str] = []
    for assertion in corpus.assertions:
        if not only(assertion):
            continue
        needs_clone = assertion.input.kind == "code"
        if needs_clone and (clone_root is None or not clone_root.is_dir()):
            unreadable.append(f"{assertion.id}: no clone root")
            continue
        source = clone_source(corpus, base_dir, clone_root or Path(), assertion)
        if source is None:
            unreadable.append(f"{assertion.id}: input not readable")
            continue
        results.append(replay_assertion(corpus, contracts, assertion, source))
    return results, unreadable


def coverage_problems(
    corpus: ModelCorpus,
    results: Sequence[ModelReplayResult],
    unreadable: Sequence[str],
) -> list[str]:
    """The replay report must account for exactly the assertions the corpus promises."""
    if corpus.replay is None:
        raise ValueError("corpus has no replay section")
    promised = corpus.replay.expected_assertions
    accounted = len(results) + len(unreadable)
    problems: list[str] = []
    if accounted != promised:
        problems.append(
            f"replay accounts for {accounted} assertions, corpus promises {promised}"
        )
    seen = [r.assertion_id for r in results]
    if len(set(seen)) != len(seen):
        problems.append("an assertion is reported twice")
    return problems


def disabled_contract(
    contract: ReplayContract, rule_id: str, target_dir: Path
) -> ReplayContract:
    """A copy of ``contract`` in ``target_dir`` with the row ``rule_id`` disabled."""
    raw = yaml.safe_load(contract.path.read_text(encoding="utf-8"))
    body = raw.get("validation", raw)
    for row in body["rules"]:
        if row["rule_id"] == rule_id:
            row["enabled"] = False
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / contract.path.name
    out.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return ReplayContract(
        out, contract.validator_id, ModelValidatorSubcontract.model_validate(body)
    )


def failed_ids(results: Sequence[ModelReplayResult]) -> set[str]:
    return {r.assertion_id for r in results if not r.ok}


def fixture_codes(
    judge: FixtureAdapter, contract: ReplayContract, fixture: Path
) -> list[str]:
    """Rule ids a checker reports on its own fixture; a refused contract reports none."""
    try:
        return [i.code for i in judge(contract, fixture) if i.code]
    except ModelOnexError:
        return []
