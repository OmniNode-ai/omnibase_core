# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Git reader of the canonical-file-shape validator (OMN-21515).

Reads tracked paths, blobs, changes and commit messages of a revision (``INDEX``
for the index) through git. The COMPUTE node package performs no I/O; its runtime
gathers facts through this reader and hands them to the pure checker.
"""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path

INDEX = ":"
# Failure type of a git run, for callers that must not import subprocess themselves.
GitCommandError = subprocess.SubprocessError


class GitRepo:
    """A git working tree and the environment its git commands run with."""

    def __init__(
        self,
        root: Path,
        env: Mapping[str, str] | None = None,
        *,
        cat_file_timeout_s: float,
    ) -> None:
        self.root = root
        self.env = env
        # Wall-clock ceiling for one cat-file run so a stall fails loud instead
        # of hanging the hook; the validator contract supplies it.
        self.cat_file_timeout_s = cat_file_timeout_s

    def _env(self) -> dict[str, str] | None:
        return None if self.env is None else dict(self.env)

    def run(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            env=self._env(),
            capture_output=True,
            check=True,
        ).stdout

    def has_revision(self, rev: str) -> bool:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
            cwd=self.root,
            env=self._env(),
            capture_output=True,
            check=False,
        )
        return proc.returncode == 0

    def merge_base(self, left: str, right: str) -> str | None:
        """The best common ancestor of two revisions, or None when they share none."""
        proc = subprocess.run(
            ["git", "merge-base", left, right],
            cwd=self.root,
            env=self._env(),
            capture_output=True,
            check=False,
        )
        sha = proc.stdout.decode().strip()
        return sha if proc.returncode == 0 and sha else None

    def list_files(self, rev: str) -> list[str]:
        """Tracked file paths at ``rev`` (``INDEX`` for the index), gitlinks skipped."""
        if rev == INDEX:
            raw = self.run("ls-files", "-s", "-z")
        else:
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
                env=self._env(),
                stdin=requests,
                stdout=responses,
                check=True,
                timeout=self.cat_file_timeout_s,
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

    def commit_messages(self, base: str, head: str) -> tuple[str, ...]:
        """Full messages of the commits in ``base..head``."""
        raw = self.run("log", "--format=%B%x00", f"{base}..{head}")
        return tuple(m for m in raw.decode(errors="replace").split("\0") if m.strip())
