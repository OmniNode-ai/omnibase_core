# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Hermetic import guard (OMN-14420).

An ambient ``PYTHONPATH`` exported by the parent shell or session can put a canonical clone's
``src/`` ahead of this checkout on ``sys.path``. ``import omnibase_core`` then resolves to a
different copy of the package than the one under test, so a worktree test run silently executes
canonical-clone source and its result is a false green or a false red.
"""

from __future__ import annotations

from pathlib import Path


def assert_hermetic_import(
    package: str, module_file: str | Path, repo_root: Path
) -> None:
    """Raise ``RuntimeError`` unless ``module_file`` resolves inside ``repo_root``."""
    resolved = Path(module_file).resolve()
    if repo_root.resolve() not in resolved.parents:
        raise RuntimeError(
            f"Hermetic import guard failed: `{package}` resolved OUTSIDE this repo "
            f"checkout ({repo_root.resolve()}); got {resolved} instead. This almost "
            "always means an ambient PYTHONPATH in your shell is shadowing this "
            f"checkout with a different (possibly stale) copy of {package} -- see "
            "OMN-14420. Re-run with 'env -u PYTHONPATH' prefixed on your command."
        )
