# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Record-mode authority guard for the canonical golden-chain harness (OMN-13499).

Record-mode authority (highest-risk surface — operator-gated):

  * ``OMN_RECORD_GOLDEN=1`` + a real endpoint is the ONLY way to mint/refresh a
    fixture.
  * Fixture creation is allowed ONLY manually or in approved nightly jobs.
  * PR CI MUST FAIL if it attempts recording — no accidental fixture
    regeneration during local debugging or in a PR run. Replay is the default.

The guard distinguishes "is record mode requested" (``OMN_RECORD_GOLDEN=1``) from
"is record mode allowed here". A PR CI run is detected via the canonical CI env
markers (``CI`` / ``GITHUB_ACTIONS``) and is NOT an approved nightly job unless it
also carries the explicit nightly-record marker ``OMN_GOLDEN_NIGHTLY_RECORD=1``
(set only by the gated nightly record workflow). Anything else that requests
recording inside CI fails closed.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

_RECORD_ENV = "OMN_RECORD_GOLDEN"
_NIGHTLY_RECORD_ENV = "OMN_GOLDEN_NIGHTLY_RECORD"
_CI_ENV_MARKERS = ("CI", "GITHUB_ACTIONS")


def record_mode_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return True only when ``OMN_RECORD_GOLDEN=1`` is set."""
    source = os.environ if env is None else env
    return source.get(_RECORD_ENV, "").strip() == "1"


def _in_ci(source: Mapping[str, str]) -> bool:
    return any(
        source.get(marker, "").strip() not in ("", "0", "false", "False")
        for marker in _CI_ENV_MARKERS
    )


def _approved_nightly(source: Mapping[str, str]) -> bool:
    return source.get(_NIGHTLY_RECORD_ENV, "").strip() == "1"


def require_record_mode_disabled(env: Mapping[str, str] | None = None) -> None:
    """Fail closed if a fixture record/refresh is attempted in a non-approved context.

    Called by the recorder BEFORE any live model call. Raises ``RuntimeError``
    when record mode is requested inside a CI run that is not an approved nightly
    record job — so a PR CI run that tries to regenerate a fixture fails the build
    instead of silently re-recording. Local manual runs (no CI markers) and the
    gated nightly job (``OMN_GOLDEN_NIGHTLY_RECORD=1``) are permitted.
    """
    source = os.environ if env is None else env
    if not record_mode_enabled(source):
        return
    if _in_ci(source) and not _approved_nightly(source):
        raise RuntimeError(
            "Golden-chain RECORD mode (OMN_RECORD_GOLDEN=1) was requested inside a "
            "CI run that is not an approved nightly record job. PR CI must REPLAY "
            "fixtures only and must never mint/refresh a fixture (no accidental "
            "regeneration). Record fixtures manually with a real endpoint, or via "
            "the gated nightly record workflow (OMN_GOLDEN_NIGHTLY_RECORD=1)."
        )


__all__ = ["record_mode_enabled", "require_record_mode_disabled"]
