# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fail-closed resolution gate for cross-repo ``uses: OmniNode-ai/...@ref`` pins.

Ported from omnibase_infra (OMN-14941/E1 root-cause, OMN-14990 fan-out): a
caller workflow pinned a reusable ``@main`` while that file existed only on
omniclaude ``dev``. GitHub fails such a workflow at parse time ("workflow was
not found") — no job runs, nothing publishes, and because the caller was not
a required check the breakage was a silent green-by-absence for weeks. No
gate anywhere resolved the pinned refs against the live remotes.

This module is that gate:

* ``_extract_cross_repo_uses`` statically extracts every cross-repo
  ``uses: OmniNode-ai/<repo>/<path>@<ref>`` from ``.github/workflows/*.yml``
  (job-level reusable-workflow pins AND step-level action pins), via YAML
  parsing so commented-out lines are never counted (unit-tested below).
* The integration test (``tests/integration/ci/
  test_workflow_uses_refs_resolve_live.py`` — under ``tests/integration``
  because the pre-push selector always ignores that tree by design and the
  gate's enforcement surface is the CI full-suite job) resolves each
  extracted pin live via the GitHub contents API
  (``/repos/OmniNode-ai/<repo>/contents/<path>?ref=<ref>``) and FAILS on any
  HTTP 404 — the exact E1 shape.

Design point (recorded, deliberate, carried over from the infra original):
the CI pytest steps carry no GH token and ``gh`` hard-refuses unauthenticated
use — a gh-only gate would be permanently red in CI for transport reasons
rather than for broken pins. All OmniNode-ai repos referenced here are
PUBLIC, so this gate calls the REST API directly via urllib, attaching
``GH_TOKEN``/``GITHUB_TOKEN`` as a bearer token when present (for rate-limit
headroom). Fail-closed posture per the optional-input-silent-skip trap: when
resolution CANNOT be performed (no network / rate-limited), the test FAILS in
CI and skips only on a local machine; a definitive 404 fails everywhere.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import NamedTuple

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

_ORG_PREFIX = "OmniNode-ai/"
_REQUEST_TIMEOUT_SECONDS = 5.0
# After this many consecutive transport (non-HTTP-status) failures, stop
# probing and report the remainder as undetermined — keeps the worst case
# bounded well under the CI per-test timeout.
_TRANSPORT_FAILURE_CIRCUIT_BREAKER = 2


class UsesRef(NamedTuple):
    """One cross-repo ``uses:`` pin extracted from a workflow file."""

    workflow: str  # workflow filename the pin appears in
    repo: str  # repo name under OmniNode-ai/
    path: str  # in-repo path ("" for a repo-root action pin)
    ref: str  # pinned git ref (branch, tag, or SHA)


def _extract_cross_repo_uses(workflows_dir: Path) -> list[UsesRef]:
    """Extract every cross-repo OmniNode-ai ``uses:`` pin, via YAML parsing.

    Covers both job-level reusable-workflow pins (``jobs.<id>.uses``) and
    step-level action pins (``jobs.<id>.steps[].uses``). YAML parsing (not a
    line regex) means commented-out ``uses:`` lines are structurally ignored.
    Local (``./``), docker (``docker://``) and third-party (``actions/...``)
    pins are out of scope — this gate owns only the OmniNode-ai cross-repo
    surface, where a moving-branch/deleted-file pin is a silent outage.
    """
    refs: list[UsesRef] = []
    for workflow_path in sorted(workflows_dir.glob("*.yml")) + sorted(
        workflows_dir.glob("*.yaml")
    ):
        loaded = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            continue
        jobs = loaded.get("jobs")
        if not isinstance(jobs, dict):
            continue
        uses_values: list[str] = []
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            job_uses = job.get("uses")
            if isinstance(job_uses, str):
                uses_values.append(job_uses)
            steps = job.get("steps")
            if isinstance(steps, list):
                for step in steps:
                    if isinstance(step, dict) and isinstance(step.get("uses"), str):
                        uses_values.append(step["uses"])
        for value in uses_values:
            if not value.startswith(_ORG_PREFIX) or "@" not in value:
                continue
            spec, _, ref = value.rpartition("@")
            remainder = spec[len(_ORG_PREFIX) :]
            repo, _, path = remainder.partition("/")
            refs.append(
                UsesRef(workflow=workflow_path.name, repo=repo, path=path, ref=ref)
            )
    return refs


def _resolve_ref_live(repo: str, path: str, ref: str) -> tuple[bool | None, str]:
    """Resolve one pin against the live GitHub contents API.

    Returns ``(True, detail)`` when the path exists at the ref,
    ``(False, detail)`` on a definitive HTTP 404 (the E1 failure shape), and
    ``(None, detail)`` when resolution could not be performed (no network,
    rate-limited, unexpected status) — the caller decides fail-vs-skip.
    """
    quoted_path = urllib.parse.quote(path)
    quoted_ref = urllib.parse.quote(ref, safe="")
    url = (
        f"https://api.github.com/repos/OmniNode-ai/{repo}/contents/"
        f"{quoted_path}?ref={quoted_ref}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "omnibase-core-uses-ref-resolution-gate (OMN-14990)",
    }
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - fixed https host
    try:
        with urllib.request.urlopen(  # noqa: S310 - fixed https host
            request, timeout=_REQUEST_TIMEOUT_SECONDS
        ) as response:
            return (response.status == 200), f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False, "HTTP 404 (path/ref does not resolve)"
        detail = f"HTTP {exc.code}"
        try:
            body = json.loads(exc.read().decode("utf-8", errors="replace"))
            message = body.get("message", "")
            if message:
                detail = f"HTTP {exc.code}: {message}"
        except (ValueError, OSError):
            pass
        # 403/429 (rate limit) and anything else non-404: cannot determine.
        return None, detail
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return None, f"transport error: {exc}"


# ---------------------------------------------------------------------------
# Extraction — unit, no network
# ---------------------------------------------------------------------------

_FIXTURE_WORKFLOW = """\
name: fixture
on:
  pull_request:
# uses: OmniNode-ai/omniclaude/.github/workflows/commented-out.yml@main
jobs:
  reusable-caller:
    uses: OmniNode-ai/omniclaude/.github/workflows/real-reusable.yml@dev
    with:
      lane: dev
  step-user:
    runs-on: ubuntu-latest
    steps:
      - name: third-party action (out of scope)
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
      - name: local composite (out of scope)
        uses: ./.github/actions/setup-python-uv
      - name: cross-repo step action
        uses: OmniNode-ai/omnimarket/some/action@abc1234
      - name: repo-root action pin
        uses: OmniNode-ai/omnibase_infra@main
"""


@pytest.mark.unit
def test_extraction_covers_job_and_step_level_pins(tmp_path: Path) -> None:
    (tmp_path / "fixture.yml").write_text(_FIXTURE_WORKFLOW, encoding="utf-8")
    refs = _extract_cross_repo_uses(tmp_path)
    assert refs == [
        UsesRef(
            workflow="fixture.yml",
            repo="omniclaude",
            path=".github/workflows/real-reusable.yml",
            ref="dev",
        ),
        UsesRef(
            workflow="fixture.yml",
            repo="omnimarket",
            path="some/action",
            ref="abc1234",
        ),
        UsesRef(workflow="fixture.yml", repo="omnibase_infra", path="", ref="main"),
    ]


@pytest.mark.unit
def test_extraction_ignores_commented_out_uses_lines(tmp_path: Path) -> None:
    """A workflow can carry a commented-out @main usage example in its header
    docs — a line regex would extract it and fail the gate on documentation."""
    (tmp_path / "fixture.yml").write_text(_FIXTURE_WORKFLOW, encoding="utf-8")
    refs = _extract_cross_repo_uses(tmp_path)
    assert not any(r.path.endswith("commented-out.yml") for r in refs)


@pytest.mark.unit
def test_real_tree_extraction_is_nonempty() -> None:
    """Guard against the optional-input-silent-skip trap: if the extractor
    silently returned nothing (glob typo, schema drift), the live gate below
    would pass vacuously. This repo is known to carry cross-repo pins."""
    refs = _extract_cross_repo_uses(WORKFLOWS_DIR)
    assert len(refs) >= 1, (
        f"expected at least 1 cross-repo uses: pin in {WORKFLOWS_DIR}, "
        f"got {len(refs)} — extractor is likely broken, not the tree"
    )


@pytest.mark.unit
def test_occ_companion_effect_pin_is_dev_not_main() -> None:
    """OMN-14941 F1 regression pin, carried into omnibase_core (OMN-14990):
    the occ-companion-effect reusable exists only on omniclaude dev; an
    @main pin is a parse-time 404 on every PR (the E1 failure class)."""
    refs = _extract_cross_repo_uses(WORKFLOWS_DIR)
    occ_pins = {
        r.path: r.ref for r in refs if r.repo == "omniclaude" and "call-occ-" in r.path
    }
    assert occ_pins == {
        ".github/workflows/call-occ-companion-effect-reusable.yml": "dev",
    }


# ---------------------------------------------------------------------------
# Live resolution — relocated (OMN-14941 pattern, OMN-14990 fan-out)
# ---------------------------------------------------------------------------
# test_every_cross_repo_uses_ref_resolves_live lives in
# tests/integration/ci/test_workflow_uses_refs_resolve_live.py: it needs the
# live GitHub API, the pre-push selector always ignores tests/integration by
# design, and its enforcement surface is the CI full-suite job (fail-closed
# there, including on unverifiable pins). It imports the helpers above.
