# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The CI-contract test class for ``.github/**`` diffs (OMN-16917).

Applies the OMN-16745 ruling — recorded in omnibase_infra
``docs/reference/selector-workflow-diff-ruling.md``, landed as omnibase_infra#2988
(``95fb95837``) — to omnibase_core's OWN selector, which is a different design
(the OMN-14921 import-graph closure, not infra's static reverse-dependency map)
and was never fixed by that PR.

Ruling, restated for this repo: for a ``.github/**`` diff the necessary and
sufficient proof is the **CI-contract class** — the tests that read ``.github/**``
off disk and assert its contents — plus any test module the diff itself touches.
The class may never select NOTHING (OMN-15541: a workflow edit can turn
full-suite escalation itself fail-OPEN), and everything outside ``.github/**``
keeps its existing fail-closed behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ci.detect_test_paths import (
    CI_CONTRACT_TEST_ROOT,
    _count_test_files,
    ci_contract_test_paths,
    compute_selection,
    is_test_file_name,
    unnarrowable_test_paths,
)
from scripts.ci.test_selection_closure import compute_closure_selection
from scripts.ci.test_selection_models import EnumFullSuiteReason

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
ADJ = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"
ALWAYS_RUN = unnarrowable_test_paths(REPO_ROOT)

# The real, merged OMN-16625 diff in this repo (commit a88cff22). This exact
# five-file list measured `split_count=39` with `selected_paths` containing the
# whole `tests/unit/` tree (1,478 collectable files) before OMN-16917 — a
# whole-suite-equivalent selection with `is_full_suite=False`, which is the
# shape the pre-push hook's OMN-15408 `selection_is_whole_suite` predicate
# routes into the OMN-15059 / OMN-16295 host-load guard.
OMN_16625_DIFF = [
    ".github/required-checks.yaml",
    ".github/workflows/ci.yml",
    "tests/unit/validation/test_ci_workflow_shape.py",
    "tests/unit/validation/test_draft_state_admission_gate_omn16215.py",
    "tests/unit/validation/test_quality_gate_docs_only_short_circuit_omn16625.py",
]

# Named members of the class, asserted BY NAME (OMN-16745 AC2: assert the class,
# not merely a smaller test count). Each of these reads `.github/**` off disk.
NAMED_CI_CONTRACT_MODULES = (
    "tests/unit/validation/test_ci_workflow_shape.py",
    "tests/unit/validation/test_receipt_gate_workflow_shape.py",
    "tests/unit/validation/test_occ_preflight_workflow_shape.py",
    "tests/unit/validation/test_release_workflow_shape.py",
    "tests/unit/validation/test_auto_merge_workflow_shape.py",
    "tests/unit/validation/test_required_check_skip_guard.py",
)


# ---------------------------------------------------------------------------
# The class itself: derived, non-empty, workflow-aware
# ---------------------------------------------------------------------------


def test_ci_contract_class_is_non_empty_and_workflow_aware() -> None:
    """OMN-15541: the class may never be empty, and must actually read .github."""
    paths = ci_contract_test_paths(REPO_ROOT)

    assert paths, "the CI-contract class may never select nothing"
    assert CI_CONTRACT_TEST_ROOT in paths
    for module in NAMED_CI_CONTRACT_MODULES:
        assert module in paths, (
            f"{module} reads .github/** off disk but is not in the class"
        )


def test_ci_contract_class_is_derived_not_hand_listed() -> None:
    """Every non-root member is a real, collectable test file in this tree."""
    paths = ci_contract_test_paths(REPO_ROOT)
    for path in paths:
        if path == CI_CONTRACT_TEST_ROOT:
            assert (REPO_ROOT / path).is_dir()
            continue
        resolved = REPO_ROOT / path
        assert resolved.is_file(), f"{path} is not a file in this tree"
        assert ".github" in resolved.read_text(encoding="utf-8")


def test_ci_contract_class_is_a_strict_subset_of_the_unit_tree() -> None:
    """The class is proof, not an escalation in disguise."""
    paths = ci_contract_test_paths(REPO_ROOT)
    unit_files = list((REPO_ROOT / "tests/unit").rglob("test_*.py"))
    assert "tests/unit/" not in paths
    assert len(paths) < len(unit_files) / 10


# ---------------------------------------------------------------------------
# The stranded shape: the real OMN-16625 diff
# ---------------------------------------------------------------------------


def test_omn16625_diff_selects_the_ci_contract_class_not_the_unit_tree() -> None:
    selection = compute_selection(
        changed_files=OMN_16625_DIFF,
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.is_full_suite is False
    assert selection.full_suite_reason is None
    # RED before OMN-16917: this was `["tests/unit/", ...]` at split_count=39.
    assert "tests/unit/" not in selection.selected_paths
    assert CI_CONTRACT_TEST_ROOT in selection.selected_paths
    for module in NAMED_CI_CONTRACT_MODULES:
        assert module in selection.selected_paths
    assert selection.split_count < 39
    assert selection.matrix == list(range(1, selection.split_count + 1))


def test_omn16625_diff_selects_its_own_touched_test_modules_at_file_grain() -> None:
    """The OMN-16745 grain lesson: a touched test module narrows to ITSELF.

    The real OMN-16625 test module reads `.github/workflows/ci.yml` and
    `.github/required-checks.yaml` off disk (it asserts the quality-gate's
    docs-only short circuit against those manifests), so once it lands it is
    ALSO a member of the derived CI-contract class -- membership in the two
    sets is not exclusive. What OMN-16745 actually guarantees, and what this
    test proves, is narrower: a touched test module is always selected by
    name, whether or not it independently qualifies for the derived class,
    and it is never widened to its containing directory.
    """
    selection = compute_selection(
        changed_files=OMN_16625_DIFF,
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    touched = (
        "tests/unit/validation/test_quality_gate_docs_only_short_circuit_omn16625.py"
    )
    assert touched in ci_contract_test_paths(REPO_ROOT)
    assert touched in selection.selected_paths
    # ...and it is NOT widened to its containing directory.
    assert "tests/unit/validation/" not in selection.selected_paths


def test_workflow_only_diff_selects_the_ci_contract_class() -> None:
    selection = compute_selection(
        changed_files=[".github/workflows/receipt-gate.yml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.is_full_suite is False
    assert "tests/unit/" not in selection.selected_paths
    assert CI_CONTRACT_TEST_ROOT in selection.selected_paths
    assert selection.selected_paths == [
        *ci_contract_test_paths(REPO_ROOT),
        *[p for p in ALWAYS_RUN if p not in ci_contract_test_paths(REPO_ROOT)],
    ]


# ---------------------------------------------------------------------------
# Fail-closed properties preserved
# ---------------------------------------------------------------------------


def test_unresolvable_file_alongside_a_workflow_still_fails_closed() -> None:
    """A genuinely unresolvable path still collapses the run to the unit tree."""
    selection = compute_selection(
        changed_files=[".github/workflows/ci.yml", "Makefile"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.is_full_suite is False
    assert "tests/unit/" in selection.selected_paths


def test_workflow_plus_shared_module_still_escalates() -> None:
    selection = compute_selection(
        changed_files=[".github/workflows/ci.yml", "src/omnibase_core/models/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SHARED_MODULE


def test_workflow_plus_test_infrastructure_still_escalates() -> None:
    selection = compute_selection(
        changed_files=[".github/workflows/ci.yml", "tests/conftest.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE


def test_workflow_plus_selector_change_still_escalates() -> None:
    """A selector that narrowed on a change to ITSELF is fail-open."""
    selection = compute_selection(
        changed_files=[".github/workflows/ci.yml", "scripts/ci/detect_test_paths.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE


def test_empty_ci_contract_class_escalates_rather_than_selecting_nothing(
    tmp_path: Path,
) -> None:
    """OMN-15541 counterexample, mechanised: no class -> no narrowing."""
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_inert.py").write_text(
        "def test_x() -> None:\n    assert True\n", encoding="utf-8"
    )

    assert ci_contract_test_paths(tmp_path) == []

    selection = compute_selection(
        changed_files=[".github/workflows/ci.yml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=tmp_path,
    )

    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE
    assert selection.split_count == 40


def test_unreadable_unit_test_is_kept_in_the_class_not_dropped(
    tmp_path: Path,
) -> None:
    """The class never shrinks on an unproven negative."""
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_binary.py").write_bytes(b"\xff\xfe not utf-8 \x00")

    assert "tests/unit/test_binary.py" in ci_contract_test_paths(tmp_path)


# ---------------------------------------------------------------------------
# Everything outside .github/** is untouched
# ---------------------------------------------------------------------------


def test_docs_only_github_markdown_stays_docs_exempt() -> None:
    selection = compute_selection(
        changed_files=[".github/PULL_REQUEST_TEMPLATE.md"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.is_full_suite is False
    assert selection.selected_paths == []


def test_required_checks_manifest_only_is_byte_for_byte_unchanged() -> None:
    """Step 5b's exact-match special case is strictly narrower and stays put."""
    selection = compute_selection(
        changed_files=[".github/required-checks.yaml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.selected_paths == [
        "tests/unit/validation/test_required_check_skip_guard.py",
        *[
            p
            for p in ALWAYS_RUN
            if p != "tests/unit/validation/test_required_check_skip_guard.py"
        ],
    ]


def test_source_only_diff_is_byte_for_byte_the_pre_existing_closure_path() -> None:
    """No `.github` path in the diff -> the new classification is inert.

    The expected value is built from the SAME primitives step 6 has always used
    (``compute_closure_selection`` unioned with the OMN-15661 always-run set),
    so this fails if the new branch leaks into a non-``.github`` diff.
    """
    changed = ["src/omnibase_core/cli/cli_main.py"]
    closure = compute_closure_selection(changed, repo_root=REPO_ROOT)
    expected = [
        *closure.selected_files,
        *[p for p in ALWAYS_RUN if p not in closure.selected_files],
    ]

    selection = compute_selection(
        changed_files=changed,
        adjacency_path=ADJ,
        ref_name="pr-branch",
        repo_root=REPO_ROOT,
    )

    assert selection.is_full_suite is False
    assert selection.selected_paths == expected


def test_split_count_counts_every_configured_test_filename_pattern(
    tmp_path: Path,
) -> None:
    """Volume counting honours ALL of ``TEST_FILE_PATTERNS``, not just half.

    ``_contains_collectable_test`` admits a directory on either pattern, so a
    directory can be SELECTED on the strength of ``*_test.py`` files. If the
    volume counter only globbed ``test_*.py`` it would not count the files that
    justified the selection, undercount the volume, and emit too few matrix
    splits — a selection whose own proof is invisible to its sizing.

    Asserted against the counter directly so the invariant holds regardless of
    which patterns happen to be populated in the live tree today.
    """
    suite = tmp_path / "tests" / "suite"
    suite.mkdir(parents=True)
    (suite / "test_prefix_style.py").write_text("def test_a() -> None: ...\n")
    (suite / "suffix_style_test.py").write_text("def test_b() -> None: ...\n")
    (suite / "helper.py").write_text("VALUE = 1\n")

    assert _count_test_files(["tests/suite/"], tmp_path) == 2
    assert is_test_file_name("suffix_style_test.py") is True
    assert is_test_file_name("helper.py") is False
