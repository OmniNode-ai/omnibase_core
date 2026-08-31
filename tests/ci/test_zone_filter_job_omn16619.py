# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ci.yml's inline zone-filter job must stage the classifier (OMN-16619).

omnibase_core runs its own copy of the docs-only detector inline in ci.yml
rather than calling the reusable .github/workflows/zone-filter.yml. The
reusable workflow stages the two pure-stdlib classifier modules under empty
__init__.py files before running them; the inline job did not, so it imported
the real src/omnibase_core/__init__.py, which calls
importlib.metadata.version("omnibase-core") and raises on a runner that never
installed the distribution. The resulting exit code 1 was read as the verdict
"production/mixed diff", so the docs-only short-circuit never fired in the repo
that owns it, silently, on every PR.

These tests pin the staged shape so the inline job cannot regress to importing
the installed-package path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _zone_filter_steps() -> list[dict[str, Any]]:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text())
    job = workflow["jobs"]["zone-filter"]
    return list(job["steps"])


def _run_step() -> dict[str, Any]:
    for step in _zone_filter_steps():
        if step.get("id") == "zone":
            return step
    raise AssertionError("ci.yml zone-filter job has no step with id 'zone'")


def test_zone_filter_stages_classifier_before_running_it() -> None:
    names = [str(step.get("name", "")) for step in _zone_filter_steps()]
    staging = [n for n in names if "Stage classifier" in n]
    assert staging, (
        "ci.yml zone-filter job must stage the classifier as a standalone "
        f"module before running it; steps were {names}"
    )
    assert names.index(staging[0]) < names.index("Run zone-diff filter")


def test_zone_filter_does_not_import_the_installed_package_path() -> None:
    """PYTHONPATH must point at the staged tree, never at src/.

    PYTHONPATH: src imports src/omnibase_core/__init__.py, whose
    importlib.metadata.version call raises when the distribution is not
    installed — which it is not, because this job deliberately skips uv sync.
    """
    pythonpath = str(_run_step().get("env", {}).get("PYTHONPATH", ""))
    assert pythonpath == ".zone-pkg", (
        f"zone-filter PYTHONPATH is {pythonpath!r}; expected '.zone-pkg' so the "
        "staged stdlib-only classifier is used instead of the real package init"
    )


def test_zone_filter_runs_the_staged_copy_of_the_script() -> None:
    run_block = str(_run_step().get("run", ""))
    assert ".zone-pkg/zone_diff_filter.py" in run_block
    assert "python scripts/zone_diff_filter.py" not in run_block


def test_zone_filter_treats_a_non_verdict_exit_code_as_full_matrix() -> None:
    """Only 0 and 1 are verdicts; anything else must fall back to full CI."""
    run_block = str(_run_step().get("run", ""))
    assert "RC -eq 0" in run_block and "RC -eq 1" in run_block
    tail = run_block.split("RC -eq 1", 1)[1]
    assert "else" in tail and "docs_only=false" in tail, (
        "the zone-filter verdict branch must end in an else that forces "
        "docs_only=false for any exit code that is not a verdict"
    )
