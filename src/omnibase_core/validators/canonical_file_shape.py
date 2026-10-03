# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical-file-shape ratchet (OMN-20304).

Operator ruling 2026-10-01 (ledger RULING lane=ratchet-ruling, OMN-20297): no
new scripts, no new plugins, no new exceptions, in any repository. Every
capability is a contract, a node and its handlers
(``docs/architecture/ONEX_CANONICAL_ARCHITECTURE.md`` in omni_home). The gates
before this one only matched words inside ``src/``, so a new file under
``scripts/``, ``plugins/``, ``tools/``, ``bin/`` or a skill directory was never
looked at.

This ratchet looks at every tracked file in the repository and refuses:

``noncanonical-file``
    a code file outside a canonical location that is not in the repo's
    baseline. Canonical locations: ``src/<pkg>/{nodes,handlers,models,
    protocols,contracts,enums}/``, any ``tests/`` or ``test/`` directory,
    ``conftest.py``, and ``docs/``. A code file is one with a code extension,
    or an extensionless file that starts with ``#!``.
``baseline-stale``
    a baseline entry whose file was removed, moved or made canonical. The
    entry must be deleted in the same change, so the baseline only shrinks.
    The old path of a detected rename (below) is not stale.
``baseline-growth``
    a baseline entry that the base revision's baseline did not have, except
    the new path of a detected rename (below).
``skill-imperative``
    a ``SKILL.md`` with more imperative-pattern lines than at the base
    revision. The patterns are the omniclaude thin-shim gate's
    (``.pre-commit-hooks/reject-imperative-skill-patterns.sh``, OMN-12237);
    its ``imperative-ok`` escape is not honoured here.
``new-exception-file``
    a new allowlist, baseline, waiver, exemption or suppression file.
``exception-entry-growth``
    an existing allowlist, baseline, waiver, exemption or suppression file
    with more entries than at the base revision.
``suppression-growth``
    a changed code or config file carrying more suppression comments than at
    the base revision.

One declared file is not an exception: the shrink-only list a gate requires.
The direct-model-call gate (OMN-20295) keeps one per repository, and the
repository declares its path in its own ``.pre-commit-config.yaml`` as the
``--baseline`` argument of the ``check-direct-model-call`` hook taken from
omnibase_core. That file is read from the head revision, and the gate itself
enforces that its list only shrinks. A baseline-named file nothing declares is
still refused.

Renames. A baselined file may be renamed (``git diff -M`` from base to head,
default similarity, so a rename plus an edit counts). The renamed path inherits
its old path's entry from the BASE baseline. Two forms are accepted:

* swap (preferred): the same change removes the old entry and adds the new
  path, so the baseline count does not grow and the baseline stays true;
* untouched: the change leaves the baseline alone. The old entry reads as
  satisfied by the rename and the new path is covered. The old entry is then
  stale in the next change, which must delete it, so the swap is the cleaner
  form.

Nothing is inherited when no rename is detected (a delete plus an add), when
the old path was not in the base baseline, when the new path is not itself a
non-canonical code file, or when the swap keeps the old entry and adds the new
one (growth). Another new script in the same change is still refused. Only
renames count, never copies.

There is no allowlist, no suppression comment and no option that widens the
canonical locations. The only state is the shrink-only baseline file, default
``.onex_ratchets/canonical_file_shape_baseline.txt``.

Revisions. By default the head is the index and the base is ``HEAD``, which
is what a pre-commit hook sees. CI soft-resets to the merge base, so the index
holds the change and the same hook checks it; ``--base``/``--head`` name the
revisions directly. Without a base revision only the first three rules run.

Usage::

    python -m omnibase_core.validators.canonical_file_shape
    python -m omnibase_core.validators.canonical_file_shape --base origin/dev --head HEAD
    python -m omnibase_core.validators.canonical_file_shape --write-baseline
    python -m omnibase_core.validators.canonical_file_shape --prune-baseline
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml

from omnibase_core.models.validation.model_canonical_file_shape_finding import (
    ModelCanonicalFileShapeFinding,
)

DEFAULT_BASELINE = ".onex_ratchets/canonical_file_shape_baseline.txt"
TICKET = "OMN-20304"
PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"
GATE_HOOK_ID = "check-direct-model-call"
GATE_REPO_URL = re.compile(r"omnibase_core(\.git)?/?$")
INDEX = ":"
# Wall-clock ceiling for one cat-file run so a stall fails loud instead of hanging the hook.
CAT_FILE_TIMEOUT_S = 300

CODE_EXTENSIONS: frozenset[str] = frozenset(
    (
        ".py",
        ".pyi",
        ".sh",
        ".bash",
        ".zsh",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".jsx",
        ".rb",
        ".pl",
        ".go",
        ".rs",
        ".lua",
        ".ps1",
        ".php",
    )
)
CONFIG_EXTENSIONS: frozenset[str] = frozenset(
    (".yaml", ".yml", ".toml", ".cfg", ".ini")
)
CANONICAL_SRC_DIRS: frozenset[str] = frozenset(
    ("nodes", "handlers", "models", "protocols", "contracts", "enums")
)
TEST_DIRS: frozenset[str] = frozenset(("tests", "test"))

# The omniclaude thin-shim gate's patterns (OMN-12237), verbatim in meaning.
SKILL_IMPERATIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^[^`]*\bAgent\("),
    re.compile(r"\bTeamCreate\b"),
    re.compile(r"(^|[^a-zA-Z])(curl |wget )"),
    re.compile(r"(^|\s)(gh api|gh pr)\s"),
    re.compile(r"(^|\s)(psql|pg_dump|pg_restore)[\s!-/:-@\[-`{-~]"),
    re.compile(r"(^|\s)ssh [^#]"),
    re.compile(r"\basyncio\.run\("),
    re.compile(r"http://(localhost|192\.168)\b"),
)

# Comment markers that switch a check off for a line or a file. Each pattern
# needs comment syntax in front of the marker, so the pattern text below does
# not count as a marker itself.
SUPPRESSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"#\s*noqa\b", re.IGNORECASE),
    re.compile(r"#\s*type:\s*ignore\b"),
    re.compile(r"#\s*pyright:\s*ignore\b"),
    re.compile(r"#\s*mypy:\s*ignore-errors\b"),
    re.compile(r"#\s*pylint:\s*disable\b"),
    re.compile(r"#\s*ruff:\s*noqa\b"),
    re.compile(r"#\s*pragma:\s*(no\s+cover|allowlist)\b"),
    re.compile(r"#\s*nosec\b"),
    re.compile(r"#\s*shellcheck\s+disable\b"),
    re.compile(r"#\s*yamllint\s+disable\b"),
    re.compile(r"#\s*aislop:\s*ignore\b"),
    re.compile(r"#\s*onex-allow"),
    re.compile(r"#\s*[A-Za-z][\w-]*-ok\b"),
    re.compile(r"ONEX_EXCLUD[E]"),
    re.compile(r"NOSONA[R]"),
    re.compile(r"gitleaks:allo[w]"),
    re.compile(r"(//|/\*)\s*eslint-disable"),
    re.compile(r"@ts-(?:ignor[e]|expect-erro[r]|nochec[k])"),
)

EXCEPTION_FILE_NAME = re.compile(
    r"(allow[-_]?list|white[-_]?list|baseline|waiver|exemption|exception"
    r"|grandfather|suppress|skip[-_]?list|ignore[-_]?list)",
    re.IGNORECASE,
)
PROSE_EXTENSIONS: frozenset[str] = frozenset((".md", ".rst", ".html", ".adoc"))


@dataclass(frozen=True, slots=True)
class GitRepo:
    """A git working tree and the environment its git commands run with."""

    root: Path
    env: Mapping[str, str] | None = None

    def run(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            env=None if self.env is None else dict(self.env),
            capture_output=True,
            check=True,
        ).stdout

    def has_revision(self, rev: str) -> bool:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
            cwd=self.root,
            env=None if self.env is None else dict(self.env),
            capture_output=True,
            check=False,
        )
        return proc.returncode == 0

    def list_files(self, rev: str) -> list[str]:
        """Tracked file paths at ``rev`` (``INDEX`` for the index), gitlinks skipped."""
        if rev == INDEX:
            raw = self.run("ls-files", "-s", "-z")
            entries = [e.split("\t", 1) for e in raw.decode().split("\0") if e]
            return [path for meta, path in entries if not meta.startswith("160000")]
        raw = self.run("ls-tree", "-r", "-z", rev)
        entries = [e.split("\t", 1) for e in raw.decode().split("\0") if e]
        return [path for meta, path in entries if not meta.startswith("160000")]

    def read_blobs(self, rev: str, paths: Iterable[str]) -> dict[str, bytes | None]:
        """Contents of ``paths`` at ``rev`` (``INDEX`` for the index); None if absent.

        Requests and responses go through temporary files, not pipes: on the
        launching Mac, a request over about 1 KB on the child's stdin pipe never
        became writable again, and the hook slept at 0% CPU forever (OMN-17427).
        The run has a wall-clock ceiling so a stall fails loud.
        """
        wanted = list(dict.fromkeys(paths))
        if not wanted:
            return {}
        prefix = ":" if rev == INDEX else f"{rev}:"
        spec = "".join(f"{prefix}{path}\n" for path in wanted).encode()
        with (
            tempfile.TemporaryFile() as requests,
            tempfile.TemporaryFile() as responses,
        ):
            requests.write(spec)
            requests.seek(0)
            subprocess.run(
                ["git", "cat-file", "--batch"],
                cwd=self.root,
                env=None if self.env is None else dict(self.env),
                stdin=requests,
                stdout=responses,
                check=True,
                timeout=CAT_FILE_TIMEOUT_S,
            )
            responses.seek(0)
            out = responses.read()
        result: dict[str, bytes | None] = {}
        pos = 0
        for path in wanted:
            end = out.index(b"\n", pos)
            header = out[pos:end].decode(errors="replace")
            pos = end + 1
            if header.endswith((" missing", " ambiguous")):
                result[path] = None
                continue
            size = int(header.rsplit(" ", 1)[1])
            result[path] = out[pos : pos + size]
            pos += size + 1
        return result

    def changed_paths(self, base: str, head: str) -> list[tuple[str, str, str | None]]:
        """``(status, path, renamed_from)`` for every path changed from base to head."""
        if head == INDEX:
            raw = self.run("diff", "--cached", "--name-status", "-M", "-z", base)
        else:
            raw = self.run("diff", "--name-status", "-M", "-z", base, head)
        parts = [p for p in raw.decode().split("\0") if p]
        changes: list[tuple[str, str, str | None]] = []
        i = 0
        while i < len(parts):
            status = parts[i]
            if status.startswith(("R", "C")):
                changes.append((status[0], parts[i + 2], parts[i + 1]))
                i += 3
            else:
                changes.append((status[0], parts[i + 1], None))
                i += 2
        return changes


def _suffix(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def is_code_file(path: str, head_bytes: bytes | None) -> bool:
    """A code extension, or an extensionless file that starts with a shebang."""
    suffix = _suffix(path)
    if suffix in CODE_EXTENSIONS:
        return True
    if suffix == "" and head_bytes is not None:
        return head_bytes.startswith(b"#!")
    return False


def is_canonical_location(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if not parts:
        return False
    if parts[0] == "docs" or parts[-1] == "conftest.py":
        return True
    if any(part in TEST_DIRS for part in parts[:-1]):
        return True
    return len(parts) >= 4 and parts[0] == "src" and parts[2] in CANONICAL_SRC_DIRS


def declared_gate_baselines(text: str | None) -> frozenset[str]:
    """Paths a ``check-direct-model-call`` hook names with ``--baseline``.

    Read from a ``.pre-commit-config.yaml``. Only the hook that the
    omnibase_core repository provides counts; a local hook of the same id does
    not.
    """
    if text is None:
        return frozenset()
    try:
        config = yaml.safe_load(text)
    except yaml.YAMLError:
        return frozenset()
    if not isinstance(config, dict):
        return frozenset()
    declared: set[str] = set()
    for entry in config.get("repos") or []:
        if not isinstance(entry, dict) or not GATE_REPO_URL.search(
            str(entry.get("repo", ""))
        ):
            continue
        for hook in entry.get("hooks") or []:
            if not isinstance(hook, dict) or hook.get("id") != GATE_HOOK_ID:
                continue
            args = [str(a) for a in hook.get("args") or []]
            for i, arg in enumerate(args):
                if arg == "--baseline" and i + 1 < len(args):
                    declared.add(args[i + 1])
                elif arg.startswith("--baseline="):
                    declared.add(arg.split("=", 1)[1])
    return frozenset(PurePosixPath(p).as_posix() for p in declared)


def is_exception_file(
    path: str, baseline_path: str, declared: frozenset[str] = frozenset()
) -> bool:
    if path == baseline_path or path in declared:
        return False
    suffix = _suffix(path)
    if suffix in CODE_EXTENSIONS or suffix in PROSE_EXTENSIONS:
        return False
    return EXCEPTION_FILE_NAME.search(PurePosixPath(path).name) is not None


def count_entries(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "//")):
            count += 1
    return count


def count_skill_imperative_lines(text: str) -> int:
    return sum(
        1
        for line in text.splitlines()
        if any(pattern.search(line) for pattern in SKILL_IMPERATIVE_PATTERNS)
    )


def count_suppressions(text: str) -> int:
    return sum(len(pattern.findall(text)) for pattern in SUPPRESSION_PATTERNS)


def parse_baseline(text: str | None) -> list[str]:
    if text is None:
        return []
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def render_baseline(paths: Iterable[str]) -> str:
    header = (
        "# canonical-file-shape baseline. Shrink-only.\n"
        "# Every line is a code file outside a canonical location that existed\n"
        "# when the ratchet was installed. Delete a line when its file is removed,\n"
        "# moved into a canonical location or rewritten as contract + node +\n"
        "# handler. A new line is refused.\n"
    )
    return header + "".join(f"{path}\n" for path in sorted(set(paths)))


def _decode(blob: bytes | None) -> str | None:
    return None if blob is None else blob.decode("utf-8", errors="replace")


def noncanonical_code_files(repo: GitRepo, head: str) -> list[str]:
    files = repo.list_files(head)
    extensionless = [f for f in files if _suffix(f) == ""]
    first_bytes = repo.read_blobs(head, extensionless)
    return sorted(
        f
        for f in files
        if is_code_file(f, first_bytes.get(f)) and not is_canonical_location(f)
    )


def check(
    repo: GitRepo,
    head: str,
    base: str | None,
    baseline_path: str = DEFAULT_BASELINE,
) -> list[ModelCanonicalFileShapeFinding]:
    """Every finding for ``head`` against the baseline and the ``base`` revision."""
    findings: list[ModelCanonicalFileShapeFinding] = []
    declared = declared_gate_baselines(
        _decode(repo.read_blobs(head, [PRE_COMMIT_CONFIG])[PRE_COMMIT_CONFIG])
    )
    head_baseline = parse_baseline(
        _decode(repo.read_blobs(head, [baseline_path])[baseline_path])
    )
    baselined = set(head_baseline)
    noncanonical = noncanonical_code_files(repo, head)
    noncanonical_set = set(noncanonical)

    base_baseline_text = (
        None
        if base is None
        else _decode(repo.read_blobs(base, [baseline_path])[baseline_path])
    )
    base_entries = set(parse_baseline(base_baseline_text))
    all_changes = [] if base is None else repo.changed_paths(base, head)
    # new path -> old path, for a detected rename of a baselined file to a path
    # that is itself a non-canonical code file.
    renames = {
        path: old
        for status, path, old in all_changes
        if status == "R"
        and old is not None
        and old in base_entries
        and path in noncanonical_set
    }
    renamed_from = set(renames.values())

    for path in noncanonical:
        if path not in baselined and path not in renames:
            findings.append(
                ModelCanonicalFileShapeFinding(
                    path=path,
                    rule="noncanonical-file",
                    reason=(
                        "new code file outside a canonical location "
                        "(src/<pkg>/{nodes,handlers,models,protocols,contracts,enums}/, "
                        "tests/, docs/). Build it as a contract + node + handler."
                    ),
                )
            )
    for path in sorted(baselined - noncanonical_set - renamed_from):
        findings.append(
            ModelCanonicalFileShapeFinding(
                path=baseline_path,
                rule="baseline-stale",
                reason=f"entry '{path}' is no longer a non-canonical code file; delete the line",
            )
        )

    if base is None:
        return findings

    if base_baseline_text is not None:
        for path in sorted(baselined - base_entries):
            if path in renames and renames[path] not in baselined:
                continue
            findings.append(
                ModelCanonicalFileShapeFinding(
                    path=baseline_path,
                    rule="baseline-growth",
                    reason=f"entry '{path}' is new; the baseline only shrinks",
                )
            )

    changes = [c for c in all_changes if c[0] != "D"]
    head_text = repo.read_blobs(head, [path for _, path, _ in changes])
    base_text = repo.read_blobs(base, [old or path for _, path, old in changes])

    for _status, path, old in changes:
        new_text = _decode(head_text.get(path))
        if new_text is None:
            continue
        old_text = _decode(base_text.get(old or path))
        findings.extend(
            _diff_findings(path, new_text, old_text, baseline_path, declared)
        )
    return findings


def _diff_findings(
    path: str,
    new_text: str,
    old_text: str | None,
    baseline_path: str,
    declared: frozenset[str],
) -> list[ModelCanonicalFileShapeFinding]:
    findings: list[ModelCanonicalFileShapeFinding] = []
    if PurePosixPath(path).name == "SKILL.md":
        new_n = count_skill_imperative_lines(new_text)
        old_n = 0 if old_text is None else count_skill_imperative_lines(old_text)
        if new_n > old_n:
            findings.append(
                ModelCanonicalFileShapeFinding(
                    path=path,
                    rule="skill-imperative",
                    reason=(
                        f"imperative lines {old_n} -> {new_n}; a skill is a thin "
                        "dispatch shim, the logic belongs in a node"
                    ),
                )
            )
    if is_exception_file(path, baseline_path, declared):
        if old_text is None:
            findings.append(
                ModelCanonicalFileShapeFinding(
                    path=path,
                    rule="new-exception-file",
                    reason="new allowlist/baseline/waiver/exemption/suppression file",
                )
            )
        else:
            new_n, old_n = count_entries(new_text), count_entries(old_text)
            if new_n > old_n:
                findings.append(
                    ModelCanonicalFileShapeFinding(
                        path=path,
                        rule="exception-entry-growth",
                        reason=f"entries {old_n} -> {new_n}; exception lists only shrink",
                    )
                )
    suffix = _suffix(path)
    if (
        suffix in CODE_EXTENSIONS
        or suffix in CONFIG_EXTENSIONS
        or (suffix == "" and new_text.startswith("#!"))
    ):
        new_n = count_suppressions(new_text)
        old_n = 0 if old_text is None else count_suppressions(old_text)
        if new_n > old_n:
            findings.append(
                ModelCanonicalFileShapeFinding(
                    path=path,
                    rule="suppression-growth",
                    reason=f"suppression comments {old_n} -> {new_n}; fix the code instead",
                )
            )
    return findings


def resolve_revisions(
    repo: GitRepo, base: str | None, head: str | None
) -> tuple[str, str | None]:
    """``(head, base)``: the flags as given, else the index against ``HEAD``."""
    resolved_head = head or INDEX
    if base is not None:
        return resolved_head, base
    if resolved_head == INDEX and repo.has_revision("HEAD"):
        return resolved_head, "HEAD"
    return resolved_head, None


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refuse new code files outside canonical locations, new imperative "
            f"code in skills and any new exception entry ({TICKET})."
        )
    )
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--base", default=None, help="base revision")
    parser.add_argument("--head", default=None, help="head revision (default: index)")
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="create the baseline from the head; refused when one exists",
    )
    parser.add_argument(
        "--prune-baseline",
        action="store_true",
        help="delete baseline entries that are no longer non-canonical code files",
    )
    parser.add_argument(
        "filenames", nargs="*", help="ignored; the whole tree is checked"
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    repo_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo = GitRepo(root=repo_root or Path.cwd(), env=env)
    baseline_file = repo.root / args.baseline

    if args.write_baseline:
        if baseline_file.exists():
            sys.stderr.write(
                f"{args.baseline} exists; a baseline is written once, then only shrinks\n"
            )
            return 1
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        paths = noncanonical_code_files(repo, args.head or INDEX)
        baseline_file.write_text(render_baseline(paths), encoding="utf-8")
        sys.stdout.write(f"wrote {len(paths)} entries to {args.baseline}\n")
        return 0

    if args.prune_baseline:
        current = parse_baseline(
            baseline_file.read_text(encoding="utf-8")
            if baseline_file.exists()
            else None
        )
        keep = set(noncanonical_code_files(repo, args.head or INDEX))
        kept = [p for p in current if p in keep]
        baseline_file.write_text(render_baseline(kept), encoding="utf-8")
        sys.stdout.write(
            f"pruned {len(current) - len(kept)} entries from {args.baseline}\n"
        )
        return 0

    head, base = resolve_revisions(repo, args.base, args.head)
    findings = check(repo, head, base, args.baseline)
    if not findings:
        return 0
    sys.stderr.write(f"Canonical-file-shape ratchet ({TICKET}) refused this change:\n")
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nOperator ruling 2026-10-01: no new scripts, plugins or exceptions. "
        "Build new capability as contract + node + handler. The baseline only "
        "shrinks; there is no suppression.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
