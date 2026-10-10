# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Replay of the decisions of the OCC ``check-bare-feature-flags`` hook (OMN-20074).

The fixtures are verbatim files of omnibase_infra and omniclaude. ``manifest.yaml`` records,
per case, the stdout and exit code the onex_change_control rev 8d7e85bc00e7 script produced on
the materialised files, and the handler must reproduce them byte for byte, so consumers that
change only ``repo:`` and ``rev:`` see no difference in what is flagged.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.handlers.handler_no_bare_feature_flags import (
    APPROVED_BASENAMES,
    APPROVED_PATH_SEGMENTS,
    HandlerNoBareFeatureFlags,
    main,
)
from omnibase_core.models.nodes.bare_feature_flag_check.model_bare_feature_flag_check_input import (
    ModelBareFeatureFlagCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "occ_bare_feature_flags"
SUMMARY_TAIL = "Declare flags in contract.yaml feature_flags: block and resolve via the flag system."


class _File(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    as_path: str
    base: str | None = None
    append: list[str] = Field(default_factory=list)


class _Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    klass: str = Field(alias="class")
    files: list[_File]
    args: list[str]
    expected_rc: int
    expected_stdout_lines: list[str]

    @property
    def expected_stdout(self) -> str:
        return "".join(f"{line}\n" for line in self.expected_stdout_lines)


def _manifest() -> dict[str, object]:
    raw = yaml.safe_load((FIXTURES / "manifest.yaml").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def _cases() -> list[_Case]:
    cases = _manifest()["cases"]
    assert isinstance(cases, list)
    return [_Case(**item) for item in cases]


def _case(case_id: str) -> _Case:
    return next(case for case in _cases() if case.id == case_id)


def _text(spec: _File) -> str:
    text = ""
    if spec.base is not None:
        text = (FIXTURES / spec.base).read_text(encoding="utf-8")
    if spec.append:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n".join(spec.append) + "\n"
    return text


def _materialise(root: Path, case: _Case) -> None:
    for spec in case.files:
        target = root / spec.as_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_text(spec), encoding="utf-8")


def _scan(path: str, source: str) -> list[str]:
    report = HandlerNoBareFeatureFlags().handle(
        ModelBareFeatureFlagCheckInput(
            files=[ModelSourceFile(path=path, source=source)]
        )
    )
    return [f.message for f in report.findings if f.severity == "FAIL"]


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case.id)
def test_fleet_case_output_matches_the_occ_hook_byte_for_byte(
    case: _Case,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _materialise(tmp_path, case)
    monkeypatch.chdir(tmp_path)
    assert main(case.args) == case.expected_rc
    assert capsys.readouterr().out == case.expected_stdout


@pytest.mark.parametrize(
    "case", [c for c in _cases() if c.files], ids=lambda case: case.id
)
def test_handler_violation_lines_are_the_occ_violation_lines(case: _Case) -> None:
    expected = (
        case.expected_stdout.split("\n\n")[0].splitlines()
        if case.expected_stdout
        else []
    )
    flagged: list[str] = []
    for spec in case.files:
        flagged.extend(_scan(spec.as_path, _text(spec)))
    assert flagged == expected


def test_positive_control_flags_all_four_read_forms_of_a_real_fleet_file() -> None:
    case = _case("positive-control-py")
    assert case.klass == "positive-control"
    assert case.expected_rc == 1
    spec = case.files[0]
    assert spec.base is not None
    messages = _scan(spec.as_path, _text(spec))
    assert [m.split('"')[1] for m in messages] == [
        "ENABLE_REAL_TIME_EVENTS",
        "ENABLE_PATTERN_ENFORCEMENT",
        "ENABLE_FOO",
        "KAFKA_ENABLED",
    ]


def test_the_real_fleet_exemption_is_a_skip_of_a_line_that_would_be_flagged() -> None:
    spec = _case("skip-exemption-with-reason-real").files[0]
    text = _text(spec)
    assert (
        'os.getenv("MY_DOMAIN_ENABLED"))  # ONEX_FLAG_EXEMPT: docstring example' in text
    )
    assert _scan(spec.as_path, text) == []
    assert _scan(
        spec.as_path, text.replace("  # ONEX_FLAG_EXEMPT: docstring example", "")
    )


def test_the_exemption_is_listed_in_the_summary_with_its_reason_and_line() -> None:
    case = _case("summary-with-exemption")
    assert "1 exemption(s) (" in case.expected_stdout
    assert "protocol_domain_plugin.py:214 [docstring example])" in case.expected_stdout
    assert case.expected_stdout.rstrip("\n").endswith(SUMMARY_TAIL)


@pytest.mark.parametrize(
    "case_id",
    [
        "skip-approved-basename-contract-yaml",
        "skip-approved-basename-feature-flag-resolver",
        "skip-approved-basename-model-contract-feature-flag",
        "skip-approved-basename-self",
        "skip-approved-segment-capabilities",
        "skip-approved-segment-config-discovery",
        "skip-approved-segment-contracts",
        "skip-approved-segment-tests",
    ],
)
def test_each_skip_class_clears_a_file_that_would_otherwise_be_flagged(
    case_id: str,
) -> None:
    case = _case(case_id)
    assert case.expected_rc == 0
    spec = case.files[0]
    text = _text(spec)
    assert _scan(spec.as_path, text) == []
    assert _scan("src/pkg/service.py", text), "the skipped content must be flaggable"


def test_a_comment_line_and_a_reasoned_exemption_are_line_skips() -> None:
    comments = _case("skip-comment-line")
    exempt = _case("skip-exemption-with-reason-ts")
    assert comments.expected_rc == exempt.expected_rc == 0
    commented = _text(comments.files[0])
    assert _scan(comments.files[0].as_path, commented) == []
    assert (
        len(
            _scan(
                comments.files[0].as_path, commented.replace("# ", "").replace("//", "")
            )
        )
        == 3
    )
    reasoned = _text(exempt.files[0])
    assert _scan(exempt.files[0].as_path, reasoned) == []
    assert _scan(
        exempt.files[0].as_path, reasoned.replace(" // ONEX_FLAG_EXEMPT: legacy", "")
    )


def test_the_approved_basenames_are_the_four_of_the_occ_hook() -> None:
    assert (
        frozenset(
            {
                "feature_flag_resolver.py",
                "contract.yaml",
                "check_bare_feature_flags.py",
                "model_contract_feature_flag.py",
            }
        )
        == APPROVED_BASENAMES
    )


def test_the_approved_path_segments_are_the_four_of_the_occ_hook() -> None:
    assert APPROVED_PATH_SEGMENTS == (
        "/tests/",
        "/capabilities/",
        "/config_discovery/",
        "/contracts/",
    )


@pytest.mark.parametrize(
    ("path", "flagged"),
    [
        ("src/pkg/tests/helpers.py", False),
        # pre-commit passes repo-relative paths, and the OCC rule needs a leading
        # slash before the segment: a top-level tests/ or contracts/ path is flagged.
        ("tests/helpers.py", True),
        ("contracts/service.py", True),
        ("src/pkg/contracts/service.py", False),
        ("src/pkg/contract/service.py", True),
        ("capabilities/service.py", True),
    ],
)
def test_path_segment_rule_needs_a_leading_slash(path: str, flagged: bool) -> None:
    assert bool(_scan(path, 'x = os.getenv("ENABLE_FOO")\n')) is flagged


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ('x = os.getenv("ENABLE_FOO")\n', 1),
        ("x = os.getenv('ENABLE_FOO')\n", 1),
        ('x = os.getenv( "ENABLE_FOO", "0")\n', 1),
        ('x = os.environ.get("FOO_ENABLED", "0")\n', 1),
        ('x = os.environ["ENABLE_FOO"]\n', 1),
        ("const x = process.env.ENABLE_FOO;\n", 1),
        ("const x = process.env.FOO_ENABLED;\n", 1),
        ('x = os.getenv("ENABLE_FOO") or os.getenv("BAR_ENABLED")\n', 1),
        ('x = os.getenv("ENABLE_FOO")\ny = os.getenv("BAR_ENABLED")\n', 2),
        ('x = os.getenv("ENABLE")\n', 0),
        ('x = os.getenv("enable_foo")\n', 0),
        ('x = os.getenv("FOO_ENABLED_X")\n', 0),
        ("x = os.getenv(ENABLE_FOO)\n", 0),
        ('x = environ.get("ENABLE_FOO")\n', 0),
        ('# x = os.getenv("ENABLE_FOO")\n', 0),
        ('    // x = os.getenv("ENABLE_FOO")\n', 0),
        ('x = 1  # os.getenv("ENABLE_FOO")\n', 1),
        ('x = os.getenv("ENABLE_FOO")  # ONEX_FLAG_EXEMPT: legacy\n', 0),
        ('x = os.getenv("ENABLE_FOO")  # ONEX_FLAG_EXEMPT:\n', 1),
        ('x = os.getenv("ENABLE_FOO")  # ONEX_FLAG_EXEMPT:    \n', 1),
        ('x = os.getenv("ENABLE_FOO")  //ONEX_FLAG_EXEMPT: why\n', 0),
    ],
)
def test_line_rules(source: str, count: int) -> None:
    assert len(_scan("src/service.py", source)) == count


def test_a_bare_exemption_is_reported_with_its_own_message() -> None:
    assert _scan(
        "src/service.py", 'x = os.getenv("ENABLE_FOO")  # ONEX_FLAG_EXEMPT:\n'
    ) == [
        "src/service.py:1: ONEX_FLAG_EXEMPT without reason token -- add a reason after the colon"
    ]


def test_non_utf8_bytes_are_replaced_not_fatal(tmp_path: Path) -> None:
    target = tmp_path / "service.py"
    target.write_bytes(b'x = os.getenv("ENABLE_FOO")  # \xff\xfe\n')
    assert main([str(target)]) == 1


def test_an_unreadable_path_is_skipped_silently_as_the_occ_hook_does(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "missing.py"), str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""
