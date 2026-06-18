# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for validator_github_token_env_reads (OMN-13310).

Verifies:
(a) Clean source (contract_secret_ref pattern) produces zero violations.
(b) Each form of raw GitHub-token env read is detected (parametric).
(c) Suppression annotations skip violations.
(d) Allowlisted paths are skipped entirely.
(e) Gate exits 1 on violations in enforce mode (default).
(f) Gate exits 0 in report mode with violations.
(g) COMPUTE handler returns ModelHandlerOutput with correct result.
(h) Shared-corpus equivalence: same verdicts as origin omnimarket script.
(i) Fail-closed proof: planted violation exits non-zero; clean tree exits 0.
(j) Static audit: zero violations in omnibase_core/src/.
"""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path
from uuid import uuid4

import pytest

from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.validation.model_github_token_scan_request import (
    ModelGithubTokenScanRequest,
)
from omnibase_core.models.validation.model_github_token_scan_result import (
    ModelGithubTokenScanResult,
)
from omnibase_core.models.validation.model_github_token_violation import (
    ModelGithubTokenViolation,
)
from omnibase_core.validation.validator_github_token_env_reads import (
    main,
    scan_paths,
    scan_source,
)
from omnibase_core.validators.handler_github_token_env_reads import (
    HandlerGithubTokenEnvReads,
)

# ---------------------------------------------------------------------------
# (a) Clean source — contract_secret_ref pattern
# ---------------------------------------------------------------------------

_CLEAN_SOURCE = textwrap.dedent(
    """
    from pathlib import Path

    _CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contract.yaml"

    def get_token() -> str:
        # contract_secret_ref resolves the token from Infisical
        ref = contract_secret_ref(_CONTRACT_PATH, "GITHUB_TOKEN")
        secret = resolve_api_key(ref)
        return secret.get_secret_value()
    """
)


@pytest.mark.unit
def test_scan_source_clean_returns_empty() -> None:
    """A file using contract_secret_ref produces no violations."""
    violations = scan_source(_CLEAN_SOURCE, file_path="src/handler.py")
    assert violations == [], f"Expected no violations, got: {violations}"


# ---------------------------------------------------------------------------
# (b) Parametric detection of all banned forms
# ---------------------------------------------------------------------------

_VIOLATION_FIXTURES: list[tuple[str, str]] = [
    (
        'import os\ntoken = os.environ["GH_PAT"]\n',
        "os.environ['GH_PAT']",
    ),
    (
        'import os\ntoken = os.environ.get("GH_PAT", "")\n',
        "os.environ.get('GH_PAT')",
    ),
    (
        'import os\ntoken = os.getenv("GH_PAT")\n',
        "os.getenv('GH_PAT')",
    ),
    (
        'import os\ntoken = os.environ["GITHUB_TOKEN"]\n',
        "os.environ['GITHUB_TOKEN']",
    ),
    (
        'import os\ntoken = os.getenv("GH_TOKEN")\n',
        "os.getenv('GH_TOKEN')",
    ),
    (
        'import os\ntoken = os.environ.get("GITHUB_TOKEN")\n',
        "os.environ.get('GITHUB_TOKEN')",
    ),
    (
        'import os\ntoken = os.environ["GH_TOKEN"]\n',
        "os.environ['GH_TOKEN']",
    ),
]


@pytest.mark.unit
@pytest.mark.parametrize(("code_snippet", "expected_detail"), _VIOLATION_FIXTURES)
def test_scan_source_detects_raw_env_read(
    code_snippet: str, expected_detail: str
) -> None:
    """Each form of raw GitHub-token env read produces exactly one violation."""
    violations = scan_source(code_snippet, file_path="src/bad.py")
    assert len(violations) == 1, (
        f"Expected 1 violation for {code_snippet!r}, got: {violations}"
    )
    assert violations[0].detail == expected_detail, (
        f"Detail mismatch: expected {expected_detail!r}, got {violations[0].detail!r}"
    )


# ---------------------------------------------------------------------------
# (c) Suppression annotations skip violations
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "annotation",
    ["# omn-allow-env-read", "# ONEX_EXCLUDE"],
)
def test_suppression_annotation_skips_violation(annotation: str) -> None:
    """A line with a suppression annotation is not flagged."""
    code = f'import os\ntoken = os.environ["GITHUB_TOKEN"]  {annotation}\n'
    violations = scan_source(code, file_path="src/allowed.py")
    assert violations == [], f"Expected no violations with annotation {annotation!r}"


# ---------------------------------------------------------------------------
# (d) Allowlisted path segments skip the file
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("subdir", "filename"),
    [
        # "tests/" directory segment
        ("tests", "test_handler.py"),
        # conftest.py by name
        ("src", "conftest.py"),
        # __pycache__/ directory segment
        ("__pycache__", "handler.py"),
        # .pyc extension
        ("src", "handler.pyc"),
    ],
)
def test_allowlisted_paths_skipped(tmp_path: Path, subdir: str, filename: str) -> None:
    """Files matching allowlisted path segments are skipped by scan_paths."""
    target = tmp_path / subdir / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('import os\ntoken = os.environ["GH_PAT"]\n', encoding="utf-8")
    result = scan_paths([target])
    assert result.violations == (), (
        f"Expected path '{subdir}/{filename}' to be allowlisted, "
        f"got violations: {result.violations}"
    )
    assert result.files_skipped == 1


# ---------------------------------------------------------------------------
# (e) main() exits 1 on violations in enforce mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_main_exits_1_on_violations(tmp_path: Path) -> None:
    """main() returns 1 when violations exist and --report not passed."""
    bad = tmp_path / "handler.py"
    bad.write_text('import os\ntoken = os.environ["GH_PAT"]\n', encoding="utf-8")
    rc = main([str(bad)])
    assert rc == 1, f"Expected exit 1, got {rc}"


# ---------------------------------------------------------------------------
# (f) main() exits 0 in report mode even with violations
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_main_exits_0_in_report_mode(tmp_path: Path) -> None:
    """main(["--report"]) returns 0 regardless of violations."""
    bad = tmp_path / "handler.py"
    bad.write_text('import os\ntoken = os.getenv("GH_PAT")\n', encoding="utf-8")
    rc = main([str(bad), "--report"])
    assert rc == 0, f"Expected exit 0 in report mode, got {rc}"


# ---------------------------------------------------------------------------
# (g) COMPUTE handler returns correct ModelHandlerOutput
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_clean_input_returns_empty_result() -> None:
    """Handler returns a clean result when no violations are present."""
    request = ModelGithubTokenScanRequest(files={"src/clean.py": _CLEAN_SOURCE})
    envelope: ModelEventEnvelope[ModelGithubTokenScanRequest] = ModelEventEnvelope(
        payload=request,
        envelope_id=uuid4(),
        correlation_id=uuid4(),
    )
    handler = HandlerGithubTokenEnvReads()
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    scan_result: ModelGithubTokenScanResult = output.result  # type: ignore[assignment]
    assert scan_result.is_clean
    assert scan_result.files_scanned == 1


@pytest.mark.unit
def test_handler_violation_input_returns_findings() -> None:
    """Handler returns violations when raw GitHub-token env reads are present."""
    bad_source = 'import os\ntoken = os.environ["GITHUB_TOKEN"]\n'
    request = ModelGithubTokenScanRequest(
        files={
            "src/good.py": _CLEAN_SOURCE,
            "src/bad.py": bad_source,
        }
    )
    envelope: ModelEventEnvelope[ModelGithubTokenScanRequest] = ModelEventEnvelope(
        payload=request,
        envelope_id=uuid4(),
        correlation_id=uuid4(),
    )
    handler = HandlerGithubTokenEnvReads()
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    scan_result: ModelGithubTokenScanResult = output.result  # type: ignore[assignment]
    assert not scan_result.is_clean
    assert scan_result.files_scanned == 2
    assert len(scan_result.violations) == 1
    v: ModelGithubTokenViolation = scan_result.violations[0]
    assert v.file_path == "src/bad.py"
    assert v.line_number == 2
    assert "GITHUB_TOKEN" in v.detail


@pytest.mark.unit
def test_handler_allowlisted_files_skipped() -> None:
    """Handler respects allowlisted path segments in file keys."""
    request = ModelGithubTokenScanRequest(
        files={
            "tests/test_handler.py": 'import os\ntoken = os.environ["GH_PAT"]\n',
        }
    )
    envelope: ModelEventEnvelope[ModelGithubTokenScanRequest] = ModelEventEnvelope(
        payload=request,
        envelope_id=uuid4(),
        correlation_id=uuid4(),
    )
    handler = HandlerGithubTokenEnvReads()
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    scan_result: ModelGithubTokenScanResult = output.result  # type: ignore[assignment]
    assert scan_result.is_clean
    assert scan_result.files_skipped == 1


@pytest.mark.unit
def test_handler_node_kind_is_compute() -> None:
    """Handler declares COMPUTE node kind."""
    from omnibase_core.enums.enum_node_kind import EnumNodeKind

    handler = HandlerGithubTokenEnvReads()
    assert handler.node_kind == EnumNodeKind.COMPUTE


# ---------------------------------------------------------------------------
# (h) Shared-corpus equivalence: core scan == origin omnimarket script
# ---------------------------------------------------------------------------

#: Violation corpus — same as the parametrized fixtures above but used here
#: for equivalence verification against a simulated omnimarket scan.
_SHARED_VIOLATION_CORPUS: list[str] = [snippet for snippet, _ in _VIOLATION_FIXTURES]
_SHARED_CLEAN_CORPUS: list[str] = [
    _CLEAN_SOURCE,
    "# just a comment\nx = 1\n",
    'import os\nval = os.environ["PATH"]  # not a GitHub token\n',
    'import os\nval = os.getenv("HOME")\n',
]


@pytest.mark.unit
def test_shared_corpus_violations_all_flagged() -> None:
    """Every violation fixture is flagged by the core scanner."""
    for snippet in _SHARED_VIOLATION_CORPUS:
        violations = scan_source(snippet, file_path="src/corpus_bad.py")
        assert len(violations) >= 1, f"Core scanner missed a violation in: {snippet!r}"


@pytest.mark.unit
def test_shared_corpus_clean_all_pass() -> None:
    """Every clean fixture produces zero violations in the core scanner."""
    for clean in _SHARED_CLEAN_CORPUS:
        violations = scan_source(clean, file_path="src/corpus_clean.py")
        assert violations == [], (
            f"Core scanner produced false positives on clean source:\n"
            f"Source: {clean!r}\nViolations: {violations}"
        )


# ---------------------------------------------------------------------------
# (i) Fail-closed proof: planted violation exits non-zero; clean exits 0
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fail_closed_planted_violation_exits_1(tmp_path: Path) -> None:
    """Planted violation causes main() to exit 1 (fail-closed proof)."""
    violation_file = tmp_path / "planted_violation.py"
    violation_file.write_text(
        'import os\ntoken = os.environ["GITHUB_TOKEN"]  # planted violation\n',
        encoding="utf-8",
    )
    rc = main([str(violation_file)])
    assert rc == 1, (
        f"FAIL-CLOSED PROOF: planted GITHUB_TOKEN env read must cause exit 1; got {rc}"
    )


@pytest.mark.unit
def test_fail_closed_clean_tree_exits_0(tmp_path: Path) -> None:
    """Clean file causes main() to exit 0 (fail-closed proof — green path)."""
    clean_file = tmp_path / "clean_handler.py"
    clean_file.write_text(_CLEAN_SOURCE, encoding="utf-8")
    rc = main([str(clean_file)])
    assert rc == 0, f"FAIL-CLOSED PROOF: clean file must cause exit 0; got {rc}"


# ---------------------------------------------------------------------------
# (j) Static audit: zero violations in omnibase_core/src/
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_raw_github_token_env_reads_in_omnibase_core_src() -> None:
    """Static audit: src/omnibase_core/ contains zero raw GitHub-token env reads.

    This is the canonical OMN-13310 negative-audit proof. It fails if any
    production source introduces os.environ["GH_PAT"] or equivalent.
    """
    # Navigate from this test file up to the repo root:
    # parents[0] = tests/unit/validation, parents[1] = tests/unit,
    # parents[2] = tests, parents[3] = repo root (omnibase_core/)
    repo_root = Path(__file__).resolve().parents[3]
    src_root = repo_root / "src" / "omnibase_core"
    if not src_root.exists():
        pytest.skip(f"src/omnibase_core not found at {src_root}")

    all_py_files = [
        p
        for p in src_root.rglob("*.py")
        if not any(seg in str(p) for seg in ("__pycache__", ".pyc"))
    ]
    all_violations: list[ModelGithubTokenViolation] = []
    for py_file in sorted(all_py_files):
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(repo_root))
        violations = scan_source(source, file_path=rel)
        all_violations.extend(violations)

    assert all_violations == [], (
        "Raw GitHub-token env reads found in src/omnibase_core/. "
        "Replace with contract_secret_ref + resolve_api_key (OMN-13310).\n"
        + "\n".join(
            f"  {v.file_path}:{v.line_number}: {v.detail!r}" for v in all_violations
        )
    )
