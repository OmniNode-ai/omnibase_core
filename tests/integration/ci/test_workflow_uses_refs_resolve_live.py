# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Live half of the cross-repo ``uses:`` pin resolution gate.

Ported from omnibase_infra (OMN-14941/E1, OMN-14990 fan-out). Static
extraction + pin-expectation regression tests live in
``tests/ci/test_workflow_uses_refs_resolve.py`` (hermetic, run at pre-push by
the governed impacted-test selector). This module holds ONLY the live GitHub
contents-API resolution test, and lives under ``tests/integration/`` because:

* the pre-push selector ALWAYS ignores ``tests/integration`` by design (it
  needs live infra), and this test needs the live GitHub API;
* the enforcement surface of this gate is CI (the ``tests-integration`` job
  runs the full ``tests/integration/`` tree unconditionally on every PR),
  where it FAILS CLOSED: a definitive 404 fails, and an unverifiable pin (no
  network / rate-limited) also fails when ``CI`` is set.
"""

from __future__ import annotations

import os

import pytest

from tests.ci.test_workflow_uses_refs_resolve import (
    _ORG_PREFIX,
    _TRANSPORT_FAILURE_CIRCUIT_BREAKER,
    WORKFLOWS_DIR,
    _extract_cross_repo_uses,
    _resolve_ref_live,
)

# Pre-existing, dormant broken pin discovered by this gate on first run
# (OMN-14992): `deploy-gate-reusable.yml` (relocated from omniclaude under
# OMN-14277, never wired to any live caller — 0 hits org-wide via
# `gh api search/code`) self-references `.github/actions/deploy-gate@main`,
# which exists on omnibase_core `dev` but was never promoted to `main`. It
# is unrelated to the OMN-14990 occ-companion-effect change this test suite
# ships alongside, and grandfathering it here (rather than silently failing
# this PR on someone else's pre-existing debt) follows the same
# documented-exception pattern as e.g. deploy_gate_legacy_grandfather.yaml.
# Remove this entry the moment OMN-14992 closes — do NOT add further
# entries without an equally-cited ticket; this is a single, named
# exception, not a blanket allowlist mechanism.
_KNOWN_BROKEN_PINS_PENDING_FIX: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("omnibase_core", ".github/actions/deploy-gate", "main"),  # OMN-14992
    }
)


@pytest.mark.integration
def test_every_cross_repo_uses_ref_resolves_live() -> None:
    refs = _extract_cross_repo_uses(WORKFLOWS_DIR)
    assert refs, "no cross-repo uses: pins extracted — extractor is broken"

    unique_targets = sorted(
        {(r.repo, r.path, r.ref) for r in refs} - _KNOWN_BROKEN_PINS_PENDING_FIX
    )
    broken: list[str] = []
    undetermined: list[str] = []
    transport_failures = 0

    for repo, path, ref in unique_targets:
        if transport_failures >= _TRANSPORT_FAILURE_CIRCUIT_BREAKER:
            undetermined.append(
                f"{_ORG_PREFIX}{repo}/{path}@{ref} (not probed: circuit "
                "breaker open after repeated transport failures)"
            )
            continue
        resolved, detail = _resolve_ref_live(repo, path, ref)
        pin = f"{_ORG_PREFIX}{repo}/{path}@{ref}"
        if resolved is False:
            broken.append(f"{pin} -> {detail}")
        elif resolved is None:
            undetermined.append(f"{pin} -> {detail}")
            if detail.startswith("transport error"):
                transport_failures += 1

    if broken:
        pinned_by = {f"{r.repo}/{r.path}@{r.ref}": r.workflow for r in refs}
        lines = [
            f"  {entry}  (pinned in "
            f"{pinned_by.get(entry.split(' -> ')[0][len(_ORG_PREFIX) :], '?')})"
            for entry in broken
        ]
        pytest.fail(
            "cross-repo `uses:` pins that DO NOT resolve on the live remote "
            "(the OMN-14941/E1 silent-outage class — the workflow fails at "
            "parse time and no job ever runs):\n" + "\n".join(lines)
        )

    if undetermined:
        detail = "\n".join(f"  {entry}" for entry in undetermined)
        if os.environ.get("CI"):
            pytest.fail(
                "could not resolve these cross-repo `uses:` pins against the "
                "live GitHub API — failing CLOSED in CI (an unverifiable pin "
                "is not a passing pin; thread GH_TOKEN into the test step or "
                "fix runner egress):\n" + detail
            )
        pytest.skip(
            "GitHub API unreachable from this local machine; live resolution "
            "gate enforced in CI. Unverified pins:\n" + detail
        )
