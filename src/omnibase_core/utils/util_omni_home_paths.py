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
1. **Bootstrap seed (OMNI_HOME only):** ``OMNI_HOME`` is irreducible -- it
   locates the operator's multi-repo registry on disk. It must be set
   fail-fast, with no default: ``export OMNI_HOME=/path/to/registry``.

2. **Derived paths → read-time resolution:** This module resolves all
   ``OMNI_HOME``-derived paths at call time, reading ``OMNI_HOME`` fail-fast
   via the typed bootstrap boundary (OMN-17744). Callers that previously
   read ``os.environ["ONEX_WORKTREES_ROOT"]`` etc. should migrate to the
   functions below. The derived env vars (``ONEX_WORKTREES_ROOT``,
   ``ONEX_EVIDENCE_ROOT``, ``OMNIBASE_INFRA_PATH``) can then be removed from
   ``~/.omnibase/.env`` as follow-up operator cleanup.

Boundary ruling (OMN-16849, operator, 2026-08-28)
--------------------------------------------------
This resolver is INTERNAL orchestration and deliberately keeps ``OMNI_HOME``.
It locates the OPERATOR's own multi-repo registry checkout -- a layout no
customer has (a customer runs a packaged CLI/skill against their own project,
never a sibling-repo registry; see beta goal row L1). Product- and
customer-facing parameters (the public installer, shipped skill docs, KB
runbooks, gateway/CLI params a self-hoster sets) use ``OMNIBASE_PATH``
instead, fail-fast, with no dual-read. OMN-16851/omnibase_core#1712 briefly
renamed this module's reads to ``OMNIBASE_PATH`` in violation of this ruling;
this module was reverted back to ``OMNI_HOME`` before that PR's release was
ever cut. The OMN-17744 typed-bootstrap migration (below) is independent of
this naming question and was kept.

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

from pathlib import Path

from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)

_OMNI_HOME_KEY = "OMNI_HOME"

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _omni_home() -> Path:
    """Return the operator's multi-repo registry root from OMNI_HOME (fail-fast).

    Reads through the typed bootstrap boundary (OMN-17744) rather than raw
    ``os.environ``. This is internal orchestration (OMN-16849 boundary
    ruling, 2026-08-28) -- OMNI_HOME, never the customer-facing
    OMNIBASE_PATH.

    Raises:
        ModelOnexError: when OMNI_HOME is not set — never silently produces
            a wrong default path.
    """
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(_OMNI_HOME_KEY,)
    )
    return Path(bootstrap.environment.require(_OMNI_HOME_KEY))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_worktrees_root() -> Path:
    """Return the canonical worktrees root: ``$OMNI_HOME/omni_worktrees``.

    This is the canonical resolver that replaces direct reads of the
    ``ONEX_WORKTREES_ROOT`` env var. Reads ``OMNI_HOME`` fail-fast; callers
    must ensure ``OMNI_HOME`` is set before invoking. Internal orchestration
    (OMN-16849 boundary ruling) -- never customer-facing.

    Returns:
        Absolute path to the worktrees directory (not guaranteed to exist).

    Raises:
        ModelOnexError: when ``OMNI_HOME`` is not set.
    """
    return _omni_home() / "omni_worktrees"


def resolve_evidence_root() -> Path:
    """Return the canonical DoD evidence root: ``$OMNI_HOME/onex_change_control/evidence``.

    This is the canonical resolver that replaces direct reads of the
    ``ONEX_EVIDENCE_ROOT`` env var. Reads ``OMNI_HOME`` fail-fast; callers
    must ensure ``OMNI_HOME`` is set before invoking. Internal orchestration
    (OMN-16849 boundary ruling) -- never customer-facing.

    Returns:
        Absolute path to the evidence directory (not guaranteed to exist).

    Raises:
        ModelOnexError: when ``OMNI_HOME`` is not set.
    """
    return _omni_home() / "onex_change_control" / "evidence"


def resolve_omnibase_infra_path() -> Path:
    """Return the canonical omnibase_infra clone path: ``$OMNI_HOME/omnibase_infra``.

    This is the canonical resolver that replaces direct reads of the
    ``OMNIBASE_INFRA_PATH`` env var. Reads ``OMNI_HOME`` fail-fast; callers
    must ensure ``OMNI_HOME`` is set before invoking. Internal orchestration
    (OMN-16849 boundary ruling) -- never customer-facing.

    Returns:
        Absolute path to the omnibase_infra repository clone (not guaranteed
        to exist).

    Raises:
        ModelOnexError: when ``OMNI_HOME`` is not set.
    """
    return _omni_home() / "omnibase_infra"


__all__ = [
    "resolve_evidence_root",
    "resolve_omnibase_infra_path",
    "resolve_worktrees_root",
]
