# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Check generated omniclaude hook bit table for drift."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _candidate_paths(repo_root: Path) -> list[tuple[Path, Path | None]]:
    candidates = [
        (
            repo_root.parent / "omniclaude" / "plugins/onex/hooks/lib/hook_bits.sh",
            None,
        ),
    ]
    if omni_home := os.environ.get("OMNI_HOME"):
        home = Path(omni_home)
        candidates.append(
            (
                home
                / "omni_worktrees/OMN-9617/omniclaude/plugins/onex/hooks/lib/hook_bits.sh",
                home / "omni_worktrees/OMN-9617/omnibase_core/src",
            )
        )
        candidates.append(
            (home / "omniclaude/plugins/onex/hooks/lib/hook_bits.sh", None)
        )
    return candidates


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    resolved = next(
        (
            (path, pythonpath)
            for path, pythonpath in _candidate_paths(repo_root)
            if path.exists()
        ),
        None,
    )
    if resolved is None:
        sys.stderr.write(
            "Skipping hook_bits drift check: omniclaude hook_bits.sh not found\n"
        )
        return 0

    target, pythonpath = resolved
    env = os.environ.copy()
    repo_src = repo_root / "src"
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(repo_src) if not existing else f"{repo_src}{os.pathsep}{existing}"
    )
    if pythonpath is not None and pythonpath.exists():
        env["PYTHONPATH"] = (
            str(pythonpath)
            if not env["PYTHONPATH"]
            else f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
        )

    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts/gen_hook_bits.py"),
            "--check",
            str(target),
        ],
        cwd=repo_root,
        env=env,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
