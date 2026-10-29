"""The checked-in checker_rule_data baseline matches the tree (OMN-21503 AC7).

The baseline only shrinks: a file that holds fewer rule tables than its entry
must have the entry lowered in the same change. This runs the same command as
the Import Layering Oracle "Run checker rule-data check" step.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / ".onex_ratchets" / "checker_rule_data_baseline.txt"
GLOBS = (
    "src/omnibase_core/handlers/handler_*_cli.py",
    "src/omnibase_core/validation/checker_*.py",
    "src/omnibase_core/validation/validator_*.py",
    "src/omnibase_core/validators/*.py",
)


@pytest.mark.unit
def test_rule_data_baseline_matches_tree() -> None:
    targets = sorted(
        str(path.relative_to(REPO_ROOT))
        for pattern in GLOBS
        for path in REPO_ROOT.glob(pattern)
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_checker_rule_data",
            "--baseline",
            str(BASELINE),
            "--base-ref",
            "HEAD",
            *targets,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
