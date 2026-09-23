# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18790 — one test per acceptance-criterion falsifier for the skip-count ratchet.

Ported from omnibase_infra's OMN-18776 landing (that repo's
``tests/ci/test_skip_count_ratchet_omn18776.py``, squash ``77ea8d01``). The
mechanism, its display name and its exit codes are deliberately identical
across the fleet; only the suite keys, the measured baselines and the
enforcement surface are per-repo.

Epic OMN-18775 measured this repo on 2026-09-18. Its ``Integration Tests
(Split n/4)`` matrix skipped 17 tests and its ``Tests (Split n/m)`` matrix
skipped 60 — the same ids, byte-identical, across five consecutive runs. A set
that never moves is a set of tests that never runs, and nothing on the fleet
notices when it grows.

Each test below is named for the falsifier it refuses. Deleting one deletes the
proof of that acceptance criterion.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "skip_count_ratchet.py"
BASELINE = REPO_ROOT / "config" / "skip_count_baseline.yaml"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CI_SUMMARY_GATE = REPO_ROOT / "scripts" / "ci" / "ci_summary_gate.py"

# The integration matrix is the frozen-17 surface epic OMN-18775 named. It runs
# `pytest tests/integration/ --splits 4`, a fixed selection, so its collected
# set is identical every run and `count` is the correct comparison.
SUITE_INTEGRATION = "omnibase_core/tests-integration"
# The unit matrix sits behind scripts/ci/detect_test_paths.py with
# ENABLE_SMART_TESTS live, so its collected set is selector-determined and
# `nodeids` is the correct comparison.
SUITE_UNIT = "omnibase_core/test-parallel"

JOB_KEY = "skip-count-ratchet"
JOB_DISPLAY_NAME = "Skip Count Ratchet (OMN-18776)"

pytestmark = pytest.mark.unit


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


def _junit(cases: list[tuple[str, bool]], collected: int) -> str:
    """Render a JUnit report. `cases` is (node_id, skipped) pairs."""
    body = []
    for node_id, skipped in cases:
        classname, _, name = node_id.rpartition("::")
        inner = "<skipped message='synthetic'/>" if skipped else ""
        body.append(
            f'<testcase classname="{classname}" name="{name}">{inner}</testcase>'
        )
    joined = "".join(body)
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuites><testsuite name="pytest" errors="0" failures="0" '
        f'skipped="{sum(1 for _, s in cases if s)}" tests="{collected}" time="1.0">'
        f"{joined}</testsuite></testsuites>"
    )


def _baseline_entry(suite: str) -> dict[str, object]:
    loaded = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    entry = loaded["suites"][suite]
    assert isinstance(entry, dict)
    return entry


def _baseline_ids(suite: str) -> list[str]:
    ids = _baseline_entry(suite)["node_ids"]
    assert isinstance(ids, list)
    return [str(i) for i in ids]


def _baseline_collected(suite: str) -> int:
    value = _baseline_entry(suite)["baseline_collected"]
    assert isinstance(value, int)
    return value


def _baseline_job(suite: str) -> str:
    value = _baseline_entry(suite)["job"]
    assert isinstance(value, str)
    return value


def _job_block() -> str:
    """The raw ci.yml text of the ratchet job, from its key to the next job key."""
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index(f"\n  {JOB_KEY}:\n")
    rest = text[start + 1 :]
    match = re.search(r"\n  [a-z][a-z0-9_-]*:\n", rest[len(f"  {JOB_KEY}:\n") :])
    end = len(rest) if match is None else len(f"  {JOB_KEY}:\n") + match.start()
    return rest[:end]


# ---------------------------------------------------------------- AC1


def test_ac1_shipped_baseline_records_provenance_for_every_entry() -> None:
    """Falsifier: a baseline entry with no recorded provenance."""
    loaded = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    suites = loaded["suites"]
    assert suites, "positive control: the shipped baseline declares at least one suite"
    for key, entry in suites.items():
        provenance = entry.get("provenance")
        assert provenance, f"{key}: no provenance block"
        for field in ("measured_at", "measurement_command", "source_runs"):
            assert provenance.get(field), (
                f"{key}: provenance.{field} is missing or empty"
            )


def test_ac1_both_measured_suites_are_registered() -> None:
    """Falsifier: a covered matrix quietly drops out of the baseline file."""
    loaded = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    assert SUITE_INTEGRATION in loaded["suites"]
    assert SUITE_UNIT in loaded["suites"]
    assert loaded["suites"][SUITE_INTEGRATION]["mode"] == "count"
    assert loaded["suites"][SUITE_UNIT]["mode"] == "nodeids"


def test_ac1_entry_missing_provenance_is_refused(tmp_path: Path) -> None:
    """Falsifier control: the validator must actually reject a bare entry."""
    bare = tmp_path / "baseline.yaml"
    bare.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "suites": {
                    SUITE_INTEGRATION: {
                        "repo": "omnibase_core",
                        "job": "Integration Tests (Split n/4)",
                        "mode": "count",
                        "max_skips": 1,
                        "baseline_collected": 1,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    junit = tmp_path / "j.xml"
    junit.write_text(_junit([("a.b::test_c", True)], 1), encoding="utf-8")
    result = _run(
        "--baseline", str(bare), "--suite", SUITE_INTEGRATION, "--junit", str(junit)
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "provenance" in (result.stdout + result.stderr)


# ---------------------------------------------------------------- AC2


@pytest.mark.parametrize("suite", [SUITE_INTEGRATION, SUITE_UNIT])
def test_ac2_added_environmental_skip_fails_naming_repo_job_and_delta(
    suite: str, tmp_path: Path
) -> None:
    """Falsifier: a deliberately added environmentally-skipped test produces a green run."""
    cases: list[tuple[str, bool]] = [(i, True) for i in _baseline_ids(suite)]
    cases.append(("tests.ci.test_synthetic_omn18790::test_needs_absent_service", True))
    junit = tmp_path / "j.xml"
    junit.write_text(_junit(cases, _baseline_collected(suite)), encoding="utf-8")

    result = _run("--baseline", str(BASELINE), "--suite", suite, "--junit", str(junit))
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "omnibase_core" in out
    assert _baseline_job(suite) in out
    assert "test_needs_absent_service" in out
    assert "+1" in out, "the failure must name the delta"


@pytest.mark.parametrize("suite", [SUITE_INTEGRATION, SUITE_UNIT])
def test_ac2_positive_control_baseline_set_alone_passes(
    suite: str, tmp_path: Path
) -> None:
    """Positive control for the test above: without the added skip the run is green."""
    cases = [(i, True) for i in _baseline_ids(suite)]
    junit = tmp_path / "j.xml"
    junit.write_text(_junit(cases, _baseline_collected(suite)), encoding="utf-8")
    result = _run("--baseline", str(BASELINE), "--suite", suite, "--junit", str(junit))
    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------- AC3


@pytest.mark.parametrize("suite", [SUITE_INTEGRATION, SUITE_UNIT])
def test_ac3_removed_skip_passes_and_prints_a_ratchet_candidate(
    suite: str, tmp_path: Path
) -> None:
    """Falsifier: removing a skipped test turns the run red."""
    ids = _baseline_ids(suite)
    cases = [(i, True) for i in ids[:-1]]
    junit = tmp_path / "j.xml"
    junit.write_text(_junit(cases, _baseline_collected(suite)), encoding="utf-8")

    result = _run("--baseline", str(BASELINE), "--suite", suite, "--junit", str(junit))
    out = result.stdout + result.stderr
    assert result.returncode == 0, out
    assert "RATCHET CANDIDATE" in out
    assert str(len(ids) - 1) in out, "the new lower number must be printed"


# ---------------------------------------------------------------- AC4


def test_ac4_ratchet_job_carries_no_continue_on_error() -> None:
    """Falsifier: `continue-on-error` appears anywhere in the new job."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert JOB_DISPLAY_NAME in text, "positive control: the job is declared in ci.yml"
    workflow = yaml.safe_load(text)
    job = workflow["jobs"][JOB_KEY]
    assert "continue-on-error" not in job
    for step in job["steps"]:
        assert "continue-on-error" not in step, step.get("name")

    # The falsifier is a grep, so the raw block must not even mention the
    # setting in prose -- a comment naming it reads as a hit to the same probe
    # that is supposed to prove its absence.
    block = _job_block()
    assert "skip_count_ratchet.py" in block, "positive control: the block was located"
    assert "continue-on-error" not in block


def test_ac4_ratchet_job_is_registered_under_the_ci_summary_umbrella() -> None:
    """Falsifier: the context appears in neither enforcement surface.

    `CI Summary` is this repo's required context and the ratchet is deliberately
    NOT added to branch protection as a raw context: an unregistered job that is
    `skipped` or ABSENT yields SUCCESS, and the GATE_JOBS entry is what closes
    that. STRICT_SUCCESS_JOBS is the half that refuses a `skipped` conclusion.
    """
    gate = CI_SUMMARY_GATE.read_text(encoding="utf-8")
    assert f'"{JOB_DISPLAY_NAME}"' in gate

    gate_block = gate.split("GATE_JOBS: tuple[str, ...] = (", 1)[1].split("\n)", 1)[0]
    assert f'"{JOB_DISPLAY_NAME}"' in gate_block

    strict_block = gate.split("STRICT_SUCCESS_JOBS: frozenset[str] = frozenset(", 1)[
        1
    ].split("\n)", 1)[0]
    assert f'"{JOB_DISPLAY_NAME}"' in strict_block


def test_ac4_ratchet_job_is_unconditional() -> None:
    """A registered job that can legitimately skip wedges the umbrella; ours uses always()."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"][JOB_KEY]
    assert str(job.get("if", "")).strip() == "always()"


def test_ac4_ratchet_job_needs_both_test_matrices() -> None:
    """Falsifier: the job runs without the matrix whose reports it is supposed to read."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"][JOB_KEY]
    needs = set(job["needs"])
    assert {"test-parallel", "tests-integration", "tests-gate"} <= needs


# ---------------------------------------------------------------- AC5


def test_ac5_selector_narrowed_run_does_not_false_fail(tmp_path: Path) -> None:
    """Falsifier: a run fails on a count the impacted-test selector explains.

    The unit matrix sits behind scripts/ci/detect_test_paths.py, so a narrower
    diff collects less and skips fewer. That lower number is the selector, not
    progress, and must neither fail the run nor be reported as a ratchet
    opportunity -- acting on the advice would red every subsequent full run.
    """
    ids = _baseline_ids(SUITE_UNIT)
    cases = [(i, True) for i in ids[: max(1, len(ids) // 4)]]
    junit = tmp_path / "j.xml"
    junit.write_text(
        _junit(cases, _baseline_collected(SUITE_UNIT) // 10), encoding="utf-8"
    )
    result = _run(
        "--baseline", str(BASELINE), "--suite", SUITE_UNIT, "--junit", str(junit)
    )
    out = result.stdout + result.stderr
    assert result.returncode == 0, out
    assert "narrowed selection" in out.lower()
    assert "RATCHET CANDIDATE" not in out


def test_ac5_positive_control_one_new_id_in_a_narrowed_run_still_fails(
    tmp_path: Path,
) -> None:
    """The zero above is not a broken probe: one unknown id in the same shape is red."""
    ids = _baseline_ids(SUITE_UNIT)
    cases = [(i, True) for i in ids[: max(1, len(ids) // 4)]]
    cases.append(("tests.ci.test_control_omn18790::test_positive_control", True))
    junit = tmp_path / "j.xml"
    junit.write_text(
        _junit(cases, _baseline_collected(SUITE_UNIT) // 10), encoding="utf-8"
    )
    result = _run(
        "--baseline", str(BASELINE), "--suite", SUITE_UNIT, "--junit", str(junit)
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "test_positive_control" in result.stdout + result.stderr


# ---------------------------------------------------------------- AC6


def test_ac6_parser_declares_no_override_option() -> None:
    """Falsifier: the argument parser declares any skip, force or baseline-override option.

    Lowering a baseline is an edit to the baseline file, reviewed like any other
    diff. A command-line lever would make it a decision one lane takes alone.
    """
    result = _run("--help")
    assert result.returncode == 0, result.stdout + result.stderr
    help_text = result.stdout.lower()
    forbidden = (
        "--force",
        "--skip",
        "--allow",
        "--ignore",
        "--override",
        "--no-fail",
        "--update-baseline",
        "--set-baseline",
        "--write-baseline",
        "--max-skips",
        "--tolerance",
        "--threshold",
        "--warn-only",
        "--advisory",
    )
    for option in forbidden:
        assert option not in help_text, f"{option} would make the ratchet optional"
    assert "--junit" in help_text, "positive control: the parser's help was read"


def test_ac6_no_environment_variable_lowers_the_verdict() -> None:
    """An env var escape hatch is the same hole wearing a different hat."""
    env_names = (
        "SKIP_COUNT_RATCHET",
        "SKIP_COUNT_RATCHET_FORCE",
        "SKIP_COUNT_RATCHET_ADVISORY",
        "ENABLE_SKIP_COUNT_RATCHET",
        "SKIP_RATCHET_OVERRIDE",
    )
    source = SCRIPT.read_text(encoding="utf-8")
    assert "os.environ" not in source and "getenv" not in source, (
        "the gate must read no environment variable at all"
    )
    for name in env_names:
        assert name not in source


# ---------------------------------------------------------------- fail-closed


def test_missing_junit_input_fails_closed(tmp_path: Path) -> None:
    result = _run(
        "--baseline",
        str(BASELINE),
        "--suite",
        SUITE_INTEGRATION,
        "--junit",
        str(tmp_path / "nope.xml"),
    )
    assert result.returncode == 2, result.stdout + result.stderr


def test_unparsable_junit_fails_closed(tmp_path: Path) -> None:
    junit = tmp_path / "j.xml"
    junit.write_text("this is not xml", encoding="utf-8")
    result = _run(
        "--baseline", str(BASELINE), "--suite", SUITE_INTEGRATION, "--junit", str(junit)
    )
    assert result.returncode == 2, result.stdout + result.stderr


def test_unknown_suite_fails_closed(tmp_path: Path) -> None:
    junit = tmp_path / "j.xml"
    junit.write_text(_junit([("a.b::test_c", True)], 1), encoding="utf-8")
    result = _run(
        "--baseline", str(BASELINE), "--suite", "nope/nope", "--junit", str(junit)
    )
    assert result.returncode == 2, result.stdout + result.stderr


def test_selftest_mode_passes_and_is_what_the_pre_commit_hook_runs() -> None:
    result = _run("--selftest")
    assert result.returncode == 0, result.stdout + result.stderr
    hook_config = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "skip_count_ratchet.py --selftest" in hook_config


def _toggle_prefix(node_id: str) -> str:
    """Render a baseline id under the OTHER rootdir than the one it was
    recorded in: add the leading ``tests.`` segment when it is absent, drop it
    when it is present. Deriving the synthetic report this way keeps the test
    honest whichever form the shipped baseline happens to carry -- the unit
    entry was re-recorded prefixed on 2026-09-19, the integration entry was
    not, and hard-coding either would silently stop exercising one of them.
    """
    return (
        node_id[len("tests.") :] if node_id.startswith("tests.") else "tests." + node_id
    )


# ------------------------------------------------- rootdir-invariance (OMN-14160)


@pytest.mark.unit
@pytest.mark.parametrize("suite", [SUITE_INTEGRATION, SUITE_UNIT])
def test_rootdir_prefix_difference_alone_is_not_a_grown_skip_set(
    suite: str, tmp_path: Path
) -> None:
    """A `tests.` prefix difference names the same tests and must not read as growth.

    JUnit dotted paths are relative to pytest's rootdir, and this repository
    resolves two of them: `tests/` for the full-suite invocation
    (`pytest tests/ --splits 40`), and the repository root for some runner
    invocations, which prefixes every id with an extra `tests.` segment.

    Before this was normalised the two forms had zero overlap, so a baseline
    recorded under one and a report emitted under the other produced the
    self-contradicting verdict this test refuses: "the skipped set GREW by 60
    test(s) (delta +60; 60 observed against a baseline of 60)" -- every id new
    while the count had not moved. Measured live on omnibase_core#1713
    (OMN-14160) against the baseline landed the same morning by OMN-16851
    (#1712), which recorded the prefixed form; `pytest tests/ ... --junitxml`
    emits the un-prefixed one, so the first full-suite run to read that
    baseline failed closed on a formatting difference.

    The negative case is the test above: a genuinely added skip still fails.
    """
    prefixed = [(_toggle_prefix(i), True) for i in _baseline_ids(suite)]
    junit = tmp_path / "j.xml"
    junit.write_text(_junit(prefixed, _baseline_collected(suite)), encoding="utf-8")
    result = _run("--baseline", str(BASELINE), "--suite", suite, "--junit", str(junit))
    assert result.returncode == 0, (
        "a rootdir prefix difference must not read as a grown skip set:\n"
        + result.stdout
        + result.stderr
    )


@pytest.mark.unit
@pytest.mark.parametrize("suite", [SUITE_INTEGRATION, SUITE_UNIT])
def test_added_skip_still_fails_when_the_report_carries_the_rootdir_prefix(
    suite: str, tmp_path: Path
) -> None:
    """The normalisation must not become a hole: growth is still refused under it.

    Same prefixed report as the test above plus one id that is in no baseline.
    If stripping the prefix had been implemented as "ignore ids that do not
    match", this would pass and the gate would be decorative.
    """
    cases = [(_toggle_prefix(i), True) for i in _baseline_ids(suite)]
    cases.append(("tests.unit.synthetic.test_never_runs::test_added", True))
    junit = tmp_path / "j.xml"
    junit.write_text(_junit(cases, _baseline_collected(suite)), encoding="utf-8")
    result = _run("--baseline", str(BASELINE), "--suite", suite, "--junit", str(junit))
    assert result.returncode != 0, (
        "an added skip must still fail even when the report is prefixed:\n"
        + result.stdout
    )
    assert "unit.synthetic.test_never_runs::test_added" in result.stdout
