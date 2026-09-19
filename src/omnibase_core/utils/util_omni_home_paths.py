# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical resolver for OMNIBASE_PATH-derived path configuration (OMN-13136, OMN-16851).

Root defect being fixed
-----------------------
``~/.omnibase/.env`` previously defined N derived path vars (e.g.
``ONEX_WORKTREES_ROOT=${OMNIBASE_PATH}/omni_worktrees``) as separate shell
variables that were expanded at ``source`` time.  When ``OMNIBASE_PATH`` was
unset at that moment, every derived var baked a broken bare-root path
(``/omni_worktrees``, ``/onex_change_control/evidence``, …).

Two-layer canonical fix (per OMN-12803 / OMN-13136)
----------------------------------------------------
1. **Bootstrap seed (OMNIBASE_PATH only):** ``OMNIBASE_PATH`` is irreducible
   -- it locates the multi-repo registry on disk. It must be set fail-fast,
   with no default: ``export OMNIBASE_PATH=/path/to/registry``.

2. **Derived paths → read-time resolution:** This module resolves all
   ``OMNIBASE_PATH``-derived paths at call time, reading ``OMNIBASE_PATH``
   fail-fast via ``os.environ["OMNIBASE_PATH"]``. Callers that previously
   read ``os.environ["ONEX_WORKTREES_ROOT"]`` etc. should migrate to the
   functions below. The derived env vars (``ONEX_WORKTREES_ROOT``,
   ``ONEX_EVIDENCE_ROOT``, ``OMNIBASE_INFRA_PATH``) can then be removed from
   ``~/.omnibase/.env`` as follow-up operator cleanup.

Rename note (OMN-16851)
------------------------
This variable was previously named ``OMNI_HOME``. It has been renamed to
``OMNIBASE_PATH`` as a clean break (OMN-16849): there is no dual-read
fallback and no deprecation window. Any caller that still sets only
``OMNI_HOME`` gets the same fail-fast ``KeyError`` as a caller that set
nothing.

Migration note
--------------
Existing readers of the legacy env vars are updated in follow-up PRs (one
per repo):
* ``omniclaude/plugins/onex/skills/_lib/dod-evidence-runner/dod_evidence_runner.py``
  → migrate ``os.environ.get("ONEX_EVIDENCE_ROOT")`` to ``resolve_evidence_root()``.
* ``omniclaude/plugins/onex/hooks/scripts/pre_tool_use_bash_guard.sh``
  → already has ``OMNIBASE_PATH``-derived fallback; remove the
  ``ONEX_WORKTREES_ROOT`` override path and rely on ``OMNIBASE_PATH`` only.
* ``~/.omnibase/.env`` — operator cleanup: remove the three derived-path
  lines (``ONEX_WORKTREES_ROOT``, ``ONEX_EVIDENCE_ROOT``,
  ``OMNIBASE_INFRA_PATH``) once all readers are migrated.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)

_OMNIBASE_PATH_KEY = "OMNIBASE_PATH"

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _omnibase_path() -> Path:
    """Return the canonical multi-repo registry root from OMNIBASE_PATH (fail-fast).

    Reads through the typed bootstrap boundary (OMN-17744) rather than raw
    ``os.environ``.

    Raises:
        ModelOnexError: when OMNIBASE_PATH is not set — never silently
            produces a wrong default path.
    """
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(_OMNIBASE_PATH_KEY,)
    )
    return Path(bootstrap.environment.require(_OMNIBASE_PATH_KEY))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_worktrees_root() -> Path:
    """Return the canonical worktrees root: ``$OMNIBASE_PATH/omni_worktrees``.

    This is the canonical resolver that replaces direct reads of the
    ``ONEX_WORKTREES_ROOT`` env var. Reads ``OMNIBASE_PATH`` fail-fast;
    callers must ensure ``OMNIBASE_PATH`` is set before invoking.

    Returns:
        Absolute path to the worktrees directory (not guaranteed to exist).

    Raises:
        KeyError: when ``OMNIBASE_PATH`` is not set.
    """
    return _omnibase_path() / "omni_worktrees"


def resolve_evidence_root() -> Path:
    """Return the canonical DoD evidence root: ``$OMNIBASE_PATH/onex_change_control/evidence``.

    This is the canonical resolver that replaces direct reads of the
    ``ONEX_EVIDENCE_ROOT`` env var. Reads ``OMNIBASE_PATH`` fail-fast;
    callers must ensure ``OMNIBASE_PATH`` is set before invoking.

    Returns:
        Absolute path to the evidence directory (not guaranteed to exist).

    Raises:
        KeyError: when ``OMNIBASE_PATH`` is not set.
    """
    return _omnibase_path() / "onex_change_control" / "evidence"


def resolve_omnibase_infra_path() -> Path:
    """Return the canonical omnibase_infra clone path: ``$OMNIBASE_PATH/omnibase_infra``.

    This is the canonical resolver that replaces direct reads of the
    ``OMNIBASE_INFRA_PATH`` env var. Reads ``OMNIBASE_PATH`` fail-fast;
    callers must ensure ``OMNIBASE_PATH`` is set before invoking.

    Returns:
        Absolute path to the omnibase_infra repository clone (not guaranteed
        to exist).

    Raises:
        KeyError: when ``OMNIBASE_PATH`` is not set.
    """
    return _omnibase_path() / "omnibase_infra"


__all__ = [
    "resolve_evidence_root",
    "resolve_omnibase_infra_path",
    "resolve_worktrees_root",
]
