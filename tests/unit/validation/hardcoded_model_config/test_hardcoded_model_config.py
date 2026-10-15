# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# test-literal-ok: OMN-19252 — the corpus fixtures ARE hardcoded lab model
# configuration the scanner-under-test must flag; the literals are the subject.
"""Corpus and ratchet tests for check-hardcoded-model-config-compute (OMN-19252).

Task A1 of knowledge-base-internal
``beta/plans/2026-09-23-remove-hardcoded-model-config.md``. The acceptance
authority is the corpus under ``corpus/``: every violation fixture yields exactly
one finding of its family, and every clean fixture yields none. The ratchet
tests pin the baseline contract: new findings fail, stale entries fail, retired
values can never be baselined, and a baseline may only lose entries against its
base.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.hardcoded_model_config import (
    runtime_hardcoded_model_config as runtime,
)
from omnibase_core.validation.hardcoded_model_config.handler import (
    HandlerHardcodedModelConfigCompute,
    classify_path,
    content_sha1,
    scan,
)
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigPolicy,
    ModelHardcodedModelConfigScanInput,
)

CORPUS_DIR = Path(__file__).parent / "corpus"
MANIFEST = yaml.safe_load((CORPUS_DIR / "manifest.yaml").read_text(encoding="utf-8"))
FIXTURES: dict[str, dict[str, str | None]] = MANIFEST["fixtures"]

# A lab address assembled at runtime, so this test module carries no literal.
LAB_HOST = ".".join(["192", "168", "86", "201"])


@pytest.fixture(scope="module")
def policy() -> ModelHardcodedModelConfigPolicy:
    return runtime.load_policy()


def _sha1(line: str) -> str:
    return content_sha1(line)


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", sorted(FIXTURES))
def test_corpus_fixture_yields_its_family(
    fixture_name: str, policy: ModelHardcodedModelConfigPolicy
) -> None:
    spec = FIXTURES[fixture_name]
    path = spec["path"]
    assert isinstance(path, str)
    text = (CORPUS_DIR / fixture_name).read_text(encoding="utf-8")
    findings = scan(path, text, policy)
    families = [f.family for f in findings]
    expected = spec["family"]
    if expected is None:
        assert families == [], f"{fixture_name} must be clean, got {findings}"
    else:
        assert families == [expected], (
            f"{fixture_name} must yield exactly one {expected} finding, got {findings}"
        )


@pytest.mark.unit
def test_corpus_covers_every_family_and_clean_cases() -> None:
    families = {spec["family"] for spec in FIXTURES.values()}
    assert families == {"M", "E", "E-LAN", "R", "L", None}


@pytest.mark.unit
def test_marker_ignored(policy: ModelHardcodedModelConfigPolicy) -> None:
    text = (CORPUS_DIR / "marker_ignored.fixture").read_text(encoding="utf-8")
    assert "onex-allow-internal-ip" in text
    findings = scan("src/pkg/endpoints.py", text, policy)
    assert [f.family for f in findings] == ["E-LAN"]


@pytest.mark.unit
def test_handler_is_a_typed_pure_compute(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    handler = HandlerHardcodedModelConfigCompute(policy)
    result = handler.handle(
        ModelHardcodedModelConfigScanInput(
            path="src/pkg/a.py", content=f'URL = "http://{LAB_HOST}:8000"\n'
        )
    )
    assert result.path_class == "SOURCE"
    assert [f.family for f in result.findings] == ["E-LAN"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("evidence/OMN-1/x.yaml", "HISTORICAL"),
        ("contracts/OMN-19252.yaml", "HISTORICAL"),
        ("src/omnibase_core/validation/hardcoded_model_config/policy.yaml", "GUARD"),
        ("config/lane.example.yaml", "EXAMPLE"),
        (".env.example", "EXAMPLE"),
        # OMN-21147: the former vendor-default files are ordinary source.
        ("src/omnimarket/configs/bifrost_delegation.yaml", "SOURCE"),
        ("src/omnimarket/inference/openrouter_models.py", "SOURCE"),
        ("plugins/onex/skills/_bin/lab-onboarding.sh", "SOURCE"),
        ("deploy/systemd/vllm-gpu0.service", "LAUNCH"),
        ("README.md", "DOC"),
        ("app/(marketing)/page.tsx", "DOC"),
        ("tests/unit/test_x.py", "TEST"),
        ("src/pkg/tests/data.yaml", "TEST"),
        ("src/pkg/router.py", "SOURCE"),
    ],
)
def test_classify_path(
    path: str, expected: str, policy: ModelHardcodedModelConfigPolicy
) -> None:
    assert classify_path(path, policy).name == expected


@pytest.mark.unit
def test_no_path_class_admits_a_named_file(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    """OMN-21147: no file is named into a class; VENDOR_DEFAULT is gone."""
    assert "VENDOR_DEFAULT" not in {c.name for c in policy.path_classes}
    assert all(c.files == () for c in policy.path_classes)


@pytest.mark.unit
def test_every_scanned_class_refuses_model_ids_and_lab_facts(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    """OMN-21147: a model id belongs in a contract overlay, never in the tree.

    HISTORICAL (records) and GUARD (this guard's own policy and corpus) scan
    nothing. DOC refuses retired values. TEST refuses private and lab-subnet
    hosts (E-LAN), lab deployment facts (D) and retired values; its model ids
    wait on a follow-up. Every other class refuses model ids (M) as well.
    """
    for path_class in policy.path_classes:
        if path_class.name in ("HISTORICAL", "GUARD"):
            assert path_class.families == ()
        elif path_class.name == "DOC":
            assert set(path_class.families) == {"R"}
        elif path_class.name == "TEST":
            assert set(path_class.families) == {"E-LAN", "D", "R"}
        else:
            assert {"M", "E-LAN", "D", "R"} <= set(path_class.families), path_class.name


@pytest.mark.unit
def test_last_path_class_is_source(policy: ModelHardcodedModelConfigPolicy) -> None:
    assert policy.path_classes[-1].name == "SOURCE"
    assert policy.path_classes[-1].globs == ("**",)


@pytest.mark.unit
def test_bare_health_ports_are_not_retired(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    assert ":8099" not in policy.retired_values
    assert ":8101" not in policy.retired_values


# --------------------------------------------------------------------------
# Ratchet: the effect-side runner over a real directory.
# --------------------------------------------------------------------------


def _write(root: Path, rel: str, text: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _baseline(root: Path, entries: list[dict[str, str]]) -> str:
    rel = "config/hardcoded_model_config_baseline.yaml"
    _write(root, rel, yaml.safe_dump({"schema_version": 1, "entries": entries}))
    return rel


@pytest.mark.unit
def test_new_finding_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    line = f'HOST = "http://{LAB_HOST}:8000"'
    _write(tmp_path, "src/pkg/a.py", line + "\n")
    rel = _baseline(tmp_path, [])
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 1
    assert "src/pkg/a.py:1" in capsys.readouterr().out


@pytest.mark.unit
def test_baselined_finding_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    line = f'HOST = "http://{LAB_HOST}:8000"'
    _write(tmp_path, "src/pkg/a.py", line + "\n")
    rel = _baseline(
        tmp_path,
        [{"path": "src/pkg/a.py", "family": "E-LAN", "content_sha1": _sha1(line)}],
    )
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 0


@pytest.mark.unit
def test_overlay_only_scan_preserves_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The stricter policy refuses new example/launch models without baseline growth."""
    monkeypatch.chdir(tmp_path)
    source = "src/pkg/a.py"
    line = f'HOST = "http://{LAB_HOST}:8000"'
    _write(tmp_path, source, line + "\n")
    rel = _baseline(
        tmp_path,
        [{"path": source, "family": "E-LAN", "content_sha1": _sha1(line)}],
    )
    baseline_before = (tmp_path / rel).read_bytes()
    assert runtime.main(["--baseline", rel, source]) == 0
    capsys.readouterr()

    example = "config/lane.example.yaml"
    launch = "deploy/systemd/serve.service"
    _write(tmp_path, example, 'model: "qwen3-coder"\n')
    _write(tmp_path, launch, 'ExecStart=/bin/serve --model "qwen3-coder"\n')
    assert runtime.main(["--baseline", rel, source, example, launch]) == 1
    out = capsys.readouterr().out
    assert f"{example}:1: [M in EXAMPLE]" in out
    assert f"{launch}:1: [M in LAUNCH]" in out
    assert "2 new finding(s), 0 stale baseline entr(y/ies)" in out
    assert (tmp_path / rel).read_bytes() == baseline_before


@pytest.mark.unit
def test_duplicate_line_needs_its_own_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    line = f'HOST = "http://{LAB_HOST}:8000"'
    _write(tmp_path, "src/pkg/a.py", line + "\n" + line + "\n")
    entry = {"path": "src/pkg/a.py", "family": "E-LAN", "content_sha1": _sha1(line)}
    rel = _baseline(tmp_path, [entry])
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 1
    rel = _baseline(tmp_path, [entry, entry])
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 0


@pytest.mark.unit
def test_stale_baseline_entry_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "src/pkg/a.py", "VALUE = 1\n")
    stale_sha = _sha1('HOST = "gone"')
    rel = _baseline(
        tmp_path,
        [{"path": "src/pkg/a.py", "family": "E-LAN", "content_sha1": stale_sha}],
    )
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 1
    out = capsys.readouterr().out
    assert "stale" in out
    assert stale_sha in out


@pytest.mark.unit
def test_entry_for_deleted_file_is_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "src/pkg/a.py", "VALUE = 1\n")
    rel = _baseline(
        tmp_path,
        [{"path": "src/pkg/gone.py", "family": "M", "content_sha1": _sha1("x")}],
    )
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 1


@pytest.mark.unit
def test_entry_for_unscanned_existing_file_is_not_judged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staged-file run does not see every file; it judges only what it read."""
    monkeypatch.chdir(tmp_path)
    line = 'MODEL = "qwen3-coder"'
    _write(tmp_path, "src/pkg/a.py", "VALUE = 1\n")
    _write(tmp_path, "src/pkg/b.py", line + "\n")
    rel = _baseline(
        tmp_path,
        [{"path": "src/pkg/b.py", "family": "M", "content_sha1": _sha1(line)}],
    )
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 0


@pytest.mark.unit
def test_retired_value_not_baselinable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    line = 'BACKEND = "local-ds-v4-flash"'
    _write(tmp_path, "src/pkg/a.py", line + "\n")
    rel = "config/hardcoded_model_config_baseline.yaml"

    # Writing a baseline over a retired value is refused and writes nothing.
    assert runtime.main(["--baseline", rel, "--write-baseline", "src/pkg/a.py"]) == 1
    assert not (tmp_path / rel).exists()

    # A baseline that already carries a retired-value entry is refused on read.
    _baseline(
        tmp_path,
        [{"path": "src/pkg/a.py", "family": "R", "content_sha1": _sha1(line)}],
    )
    assert runtime.main(["--baseline", rel, "src/pkg/a.py"]) == 1
    assert "retired" in capsys.readouterr().out


@pytest.mark.unit
def test_write_baseline_then_check_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "src/pkg/a.py", 'MODEL = "qwen3-coder"\n')
    _write(tmp_path, "tests/test_a.py", f'H = "http://{LAB_HOST}:8000"\n')
    rel = "config/hardcoded_model_config_baseline.yaml"
    files = ["src/pkg/a.py", "tests/test_a.py"]
    assert runtime.main(["--baseline", rel, "--write-baseline", *files]) == 0
    written = yaml.safe_load((tmp_path / rel).read_text(encoding="utf-8"))
    assert len(written["entries"]) == 2
    assert runtime.main(["--baseline", rel, *files]) == 0


@pytest.mark.unit
def test_missing_baseline_file_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "src/pkg/a.py", "VALUE = 1\n")
    assert runtime.main(["--baseline", "config/absent.yaml", "src/pkg/a.py"]) == 1


@pytest.mark.unit
def test_baseline_growth_against_base_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    line = 'MODEL = "qwen3-coder"'
    _write(tmp_path, "src/pkg/a.py", line + "\n")
    entry = {"path": "src/pkg/a.py", "family": "M", "content_sha1": _sha1(line)}
    rel = _baseline(tmp_path, [entry])

    empty_base = yaml.safe_dump({"schema_version": 1, "entries": []})
    monkeypatch.setattr(runtime, "read_baseline_at_ref", lambda ref, path: empty_base)
    assert (
        runtime.main(["--baseline", rel, "--base", "origin/dev", "src/pkg/a.py"]) == 1
    )
    assert "added" in capsys.readouterr().out

    same_base = yaml.safe_dump({"schema_version": 1, "entries": [entry]})
    monkeypatch.setattr(runtime, "read_baseline_at_ref", lambda ref, path: same_base)
    assert (
        runtime.main(["--baseline", rel, "--base", "origin/dev", "src/pkg/a.py"]) == 0
    )


@pytest.mark.unit
def test_baseline_shrink_against_base_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "src/pkg/a.py", "VALUE = 1\n")
    rel = _baseline(tmp_path, [])
    old = {"path": "src/pkg/a.py", "family": "M", "content_sha1": _sha1("x")}
    base = yaml.safe_dump({"schema_version": 1, "entries": [old]})
    monkeypatch.setattr(runtime, "read_baseline_at_ref", lambda ref, path: base)
    assert (
        runtime.main(["--baseline", rel, "--base", "origin/dev", "src/pkg/a.py"]) == 0
    )


@pytest.mark.unit
def test_no_bypass_option_exists() -> None:
    parser = runtime.build_parser()
    options = {s for action in parser._actions for s in action.option_strings}
    assert options == {
        "-h",
        "--help",
        "--all",
        "--baseline",
        "--write-baseline",
        "--base",
    }
