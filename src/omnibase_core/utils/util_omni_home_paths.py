# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical resolver for OMNI_HOME-derived path configuration (OMN-13136).

Root defect being fixed
-----------------------
``~/.omnibase/.env`` previously defined N derived path vars (e.g.
``ONEX_WORKTREES_ROOT=${OMNI_HOME}/omni_worktrees``) as separate shell
variables that were expanded at ``source`` time.  When ``OMNI_HOME`` was
unset at that moment, every derived var baked a broken bare-root path
(``/omni_worktrees``, ``/onex_change_control/evidence``, …).

Two-layer canonical fix (per OMN-12803 / OMN-13136)
----------------------------------------------------
1. **Bootstrap seed (OMNI_HOME only):** ``OMNI_HOME`` is irreducible — it
   locates the monorepo registry on disk.  It is the single env var that must
   remain in ``~/.omnibase/.env``, set home-relative:
   ``OMNI_HOME=${OMNI_HOME:-$HOME/Code/omni_home}``.

2. **Derived paths → read-time resolution:** This module resolves all
   ``OMNI_HOME``-derived paths at call time, reading ``OMNI_HOME`` fail-fast
   via ``os.environ["OMNI_HOME"]``.  Callers that previously read
   ``os.environ["ONEX_WORKTREES_ROOT"]`` etc. should migrate to the functions
   below.  The derived env vars (``ONEX_WORKTREES_ROOT``,
   ``ONEX_EVIDENCE_ROOT``, ``OMNIBASE_INFRA_PATH``) can then be removed from
   ``~/.omnibase/.env`` as follow-up operator cleanup.

Migration note
--------------
Existing readers of the legacy env vars are updated in follow-up PRs (one
per repo):
* ``omniclaude/plugins/onex/skills/_lib/dod-evidence-runner/dod_evidence_runner.py``
  → migrate ``os.environ.get("ONEX_EVIDENCE_ROOT")`` to ``resolve_evidence_root()``.
* ``omniclaude/plugins/onex/hooks/scripts/pre_tool_use_bash_guard.sh``
  → already has ``OMNI_HOME``-derived fallback; remove the
  ``ONEX_WORKTREES_ROOT`` override path and rely on ``OMNI_HOME`` only.
* ``~/.omnibase/.env`` — operator cleanup: remove the three derived-path
  lines (``ONEX_WORKTREES_ROOT``, ``ONEX_EVIDENCE_ROOT``,
  ``OMNIBASE_INFRA_PATH``) once all readers are migrated.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _omni_home() -> Path:
    """Return the canonical monorepo root from OMNI_HOME (fail-fast).

    Raises:
        KeyError: when OMNI_HOME is not set — never silently produces a wrong
            default path.
    """
    return Path(os.environ["OMNI_HOME"])  # env-read-ok: bootstrap seed; OMN-13136


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_worktrees_root() -> Path:
    """Return the canonical worktrees root: ``$OMNI_HOME/omni_worktrees``.

    This is the canonical resolver that replaces direct reads of the
    ``ONEX_WORKTREES_ROOT`` env var.  Reads ``OMNI_HOME`` fail-fast; callers
    must ensure ``OMNI_HOME`` is set before invoking.

    Returns:
        Absolute path to the worktrees directory (not guaranteed to exist).

    Raises:
        KeyError: when ``OMNI_HOME`` is not set.
    """
    return _omni_home() / "omni_worktrees"


def resolve_evidence_root() -> Path:
    """Return the canonical DoD evidence root: ``$OMNI_HOME/onex_change_control/evidence``.

    This is the canonical resolver that replaces direct reads of the
    ``ONEX_EVIDENCE_ROOT`` env var.  Reads ``OMNI_HOME`` fail-fast; callers
    must ensure ``OMNI_HOME`` is set before invoking.

    Returns:
        Absolute path to the evidence directory (not guaranteed to exist).

    Raises:
        KeyError: when ``OMNI_HOME`` is not set.
    """
    return _omni_home() / "onex_change_control" / "evidence"


def resolve_omnibase_infra_path() -> Path:
    """Return the canonical omnibase_infra clone path: ``$OMNI_HOME/omnibase_infra``.

    This is the canonical resolver that replaces direct reads of the
    ``OMNIBASE_INFRA_PATH`` env var.  Reads ``OMNI_HOME`` fail-fast; callers
    must ensure ``OMNI_HOME`` is set before invoking.

    Returns:
        Absolute path to the omnibase_infra repository clone (not guaranteed
        to exist).

    Raises:
        KeyError: when ``OMNI_HOME`` is not set.
    """
    return _omni_home() / "omnibase_infra"


__all__ = [
    "resolve_evidence_root",
    "resolve_omnibase_infra_path",
    "resolve_worktrees_root",
]
