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

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_private_vocabulary_resolution import (
    build_container,
    capture_environment,
    resolve_private_vocabulary,
)
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
    container = build_container()
    return runtime.load_policy(
        resolve_private_vocabulary(
            container,
            "hardcoded_model_config_lab_denylist",
            environment=capture_environment(container),
            now=datetime.now(UTC),
        )
    )


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
    assert families == {"M", "E", "E-LAN", "R", "L", "T", "N", None}


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
        # OMN-21147: the work ledger is append-only history and is never rewritten; the
        # private denylist names the retired values it exists to refuse.
        ("docs/tracking/ROLLING_WORK_LEDGER.md", "HISTORICAL"),
        ("docs/tracking/archive/ROLLING_WORK_LEDGER_2026-10-12-split.md", "HISTORICAL"),
        ("vocabularies/hardcoded_model_config_lab_denylist.yaml", "GUARD"),
        # A note beside the ledger is ordinary prose, not history.
        ("docs/tracking/notes.md", "DOC"),
        ("config/lane.example.yaml", "EXAMPLE"),
        (".env.example", "EXAMPLE"),
        # OMN-21147: the former vendor-default files are ordinary source.
        ("src/omnimarket/configs/bifrost_delegation.yaml", "SOURCE"),
        ("src/omnimarket/inference/openrouter_models.py", "SOURCE"),
        ("plugins/onex/skills/_bin/lab-onboarding.sh", "SOURCE"),
        ("deploy/systemd/vllm-gpu0.service", "LAUNCH"),
        ("README.md", "DOC"),
        ("docs/guide.rst", "DOC"),
        # Code under docs/ or a marketing route is code, not prose (OMN-21147).
        ("docs/tools/gen.py", "SOURCE"),
        ("app/(marketing)/page.tsx", "SOURCE"),
        ("tests/unit/test_x.py", "TEST"),
        ("src/pkg/tests/data.yaml", "TEST"),
        ("src/pkg/router.py", "SOURCE"),
        # OMN-20910: the contract overlay tree is where a deployment fact belongs.
        ("config/onex/overlays/node_x_compute/overlay.yaml", "OVERLAY"),
        ("config/onex/overlays/README.md", "OVERLAY"),
        # Only that tree, from the repository root: a look-alike is source.
        ("src/pkg/config/onex/overlays/node_x_compute/overlay.yaml", "SOURCE"),
        ("config/onex/overlay.yaml", "SOURCE"),
        ("config/onex/node_x_compute/overlay.yaml", "SOURCE"),
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
    nothing. DOC is prose (markdown and reStructuredText only) and refuses
    retired values. Every other class refuses model ids (M), private and
    lab-subnet hosts (E-LAN) and lab deployment facts (D).
    """
    for path_class in policy.path_classes:
        if path_class.name in ("HISTORICAL", "GUARD"):
            assert path_class.families == ()
        elif path_class.name == "OVERLAY":
            # OMN-20910: the overlay is the sanctioned home of model ids,
            # endpoints and lab facts, so it refuses retired values only, and
            # the class covers the contract overlay tree and nothing else.
            assert set(path_class.families) == {"R"}
            assert path_class.globs == ("config/onex/overlays/**",)
        elif path_class.name == "DOC":
            assert set(path_class.families) == {"R"}
            assert all(g.endswith((".md", ".mdx", ".rst")) for g in path_class.globs), (
                path_class.globs
            )
        else:
            assert {"M", "E-LAN", "D", "R"} <= set(path_class.families), path_class.name


@pytest.mark.unit
def test_tests_may_use_only_declared_fixture_ids(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    clean = 'MODEL = "fixture-model-a"\n'
    assert scan("tests/unit/test_router.py", clean, policy) == []
    real = 'MODEL = "gpt-5-mini"\n'
    found = scan("tests/unit/test_router.py", real, policy)
    assert [f.family for f in found] == ["M"]


def _overlay_lines() -> str:
    """A review-voter overlay entry: an endpoint on the lab subnet and a model id."""
    return (
        "voters:\n"
        "  - voter_id: correctness\n"
        f'    endpoint_url: "http://{LAB_HOST}:8000/v1/chat/completions"\n'
        '    api_model_id: "qwen3-coder"\n'
    )


@pytest.mark.unit
def test_an_overlay_may_name_an_endpoint_and_a_model(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    """OMN-20910: deployment facts belong in a contract overlay, so the overlay
    tree is not source; the same lines in a shipped file are still refused."""
    overlay = "config/onex/overlays/node_review_voters_overlay_compute/overlay.yaml"
    assert scan(overlay, _overlay_lines(), policy) == []
    shipped = "src/pkg/configs/review_voters.yaml"
    families = sorted({f.family for f in scan(shipped, _overlay_lines(), policy)})
    assert families == ["E", "E-LAN", "M"]


@pytest.mark.unit
def test_an_overlay_still_refuses_a_retired_value(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    overlay = "config/onex/overlays/node_x_compute/overlay.yaml"
    retired = policy.retired_values[0]
    found = scan(overlay, f'model: "{retired}"\n', policy)
    assert [f.family for f in found] == ["R"]


@pytest.mark.unit
def test_ratchet_passes_an_overlay_and_refuses_the_same_lines_in_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    overlay = "config/onex/overlays/node_review_voters_overlay_compute/overlay.yaml"
    shipped = "src/pkg/configs/review_voters.yaml"
    _write(tmp_path, overlay, _overlay_lines())
    _write(tmp_path, shipped, _overlay_lines())
    rel = _baseline(tmp_path, [])
    assert runtime.main(["--baseline", rel, overlay]) == 0
    capsys.readouterr()
    assert runtime.main(["--baseline", rel, overlay, shipped]) == 1
    out = capsys.readouterr().out
    assert f"{shipped}:3: [E in SOURCE]" in out
    assert f"{shipped}:3: [E-LAN in SOURCE]" in out
    assert overlay not in out


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
    monkeypatch.setattr(runtime, "read_file_at_ref", lambda ref, path: None)
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
def test_baseline_may_take_a_line_that_existed_at_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """OMN-21147: a tightened policy reclassifies lines already in the tree.

    Such a line may enter the baseline; a line the change itself adds may not.
    """
    monkeypatch.chdir(tmp_path)
    line = 'MODEL = "qwen3-coder"'
    _write(tmp_path, "tests/unit/test_a.py", line + "\n")
    entry = {"path": "tests/unit/test_a.py", "family": "M", "content_sha1": _sha1(line)}
    rel = _baseline(tmp_path, [entry])
    empty_base = yaml.safe_dump({"schema_version": 1, "entries": []})
    monkeypatch.setattr(runtime, "read_baseline_at_ref", lambda ref, path: empty_base)

    monkeypatch.setattr(runtime, "read_file_at_ref", lambda ref, path: line + "\n")
    argv = ["--baseline", rel, "--base", "origin/dev", "tests/unit/test_a.py"]
    assert runtime.main(argv) == 0
    assert "existed at origin/dev" in capsys.readouterr().out

    monkeypatch.setattr(runtime, "read_file_at_ref", lambda ref, path: None)
    assert runtime.main(argv) == 1
    assert "entries only leave" in capsys.readouterr().out

    _write(tmp_path, "tests/unit/test_a.py", line + "\n" + line + "\n")
    rel = _baseline(tmp_path, [entry, entry])
    monkeypatch.setattr(runtime, "read_file_at_ref", lambda ref, path: line + "\n")
    assert runtime.main(argv) == 1


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


@pytest.mark.unit
def test_model_id_pattern_does_not_name_the_retired_gpt_oss_model(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    """OMN-19432: the family regex lists only model families still in use.

    gpt-oss-120b left the lab on 2026-10-08. The positive control proves the
    regex still matches the families that remain.
    """
    pattern = re.compile(policy.model_id_pattern, re.IGNORECASE)
    assert pattern.search("qwen3-coder") is not None
    assert pattern.search("gpt-4o") is not None
    assert "oss" not in policy.model_id_pattern.lower()


# ---------------------------------------------------------------------------
# OMN-21463 (K6): families T (tier aliases) and N (engine names)
# ---------------------------------------------------------------------------

_TN_VIOLATIONS = sorted(
    name
    for name, spec in FIXTURES.items()
    if spec["family"] in ("T", "N") and name.startswith("violation_")
)


def _scan_fixture(name: str, policy: ModelHardcodedModelConfigPolicy) -> list[str]:
    path = FIXTURES[name]["path"]
    assert isinstance(path, str)
    text = (CORPUS_DIR / name).read_text(encoding="utf-8")
    return [f.family for f in scan(path, text, policy)]


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", _TN_VIOLATIONS)
def test_tn_comment_form_of_a_violation_passes(
    fixture_name: str, policy: ModelHardcodedModelConfigPolicy
) -> None:
    """The same text in a comment is allowed as provenance (no marker needed)."""
    path = FIXTURES[fixture_name]["path"]
    assert isinstance(path, str)
    text = (CORPUS_DIR / fixture_name).read_text(encoding="utf-8")
    prefix = "# "
    commented = "\n".join(
        prefix + line if line.strip() else line for line in text.splitlines()
    )
    assert scan(path, commented + "\n", policy) == []


# The vocabulary keys that decide each violation fixture's verdict.
_DECIDED_BY: dict[str, frozenset[str]] = {
    "violation_t_key.fixture": frozenset({"tier_aliases", "tier_keys"}),
    "violation_t_assign.fixture": frozenset({"tier_aliases", "tier_keys"}),
    "violation_t_literal.fixture": frozenset({"tier_aliases"}),
    "violation_t_tuple.fixture": frozenset({"tier_aliases"}),
    "violation_t_set.fixture": frozenset({"tier_aliases"}),
    "violation_t_yaml_list.fixture": frozenset({"tier_aliases"}),
    "violation_t_yaml_flow.fixture": frozenset({"tier_aliases"}),
    "violation_n_enum.fixture": frozenset({"engine_names"}),
    "violation_n_alias_key.fixture": frozenset({"engine_names"}),
    "violation_n_alias_tier_key.fixture": frozenset({"tier_aliases"}),
    "violation_n_literal.fixture": frozenset({"engine_names"}),
    "violation_n_keyword.fixture": frozenset({"engine_names", "tier_keys"}),
    "violation_n_yaml_value.fixture": frozenset({"engine_names", "tier_keys"}),
    "violation_n_yaml_list.fixture": frozenset({"engine_names", "tier_keys"}),
}


@pytest.mark.unit
def test_every_tn_violation_fixture_declares_what_decides_it() -> None:
    assert set(_DECIDED_BY) == set(_TN_VIOLATIONS)


@pytest.mark.unit
@pytest.mark.parametrize(
    "vocabulary_key", ["tier_aliases", "tier_keys", "engine_names"]
)
def test_each_tn_vocabulary_key_decides_its_verdict(
    vocabulary_key: str, policy: ModelHardcodedModelConfigPolicy
) -> None:
    """Mutate every vocabulary key in turn: the fixtures it decides stop failing
    without it, and no other fixture's verdict changes."""
    emptied = policy.model_copy(update={vocabulary_key: ()})
    for name in _TN_VIOLATIONS:
        before = _scan_fixture(name, policy)
        after = _scan_fixture(name, emptied)
        assert before == [FIXTURES[name]["family"]]
        if vocabulary_key in _DECIDED_BY[name]:
            assert after == [], f"{vocabulary_key} must decide {name}"
        else:
            assert after == before, f"{vocabulary_key} must not decide {name}"


@pytest.mark.unit
def test_tn_vocabularies_are_policy_data_not_checker_code(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    assert {"sonnet", "opus", "haiku", "claude_opus", "claude_sonnet"} <= set(
        policy.tier_aliases
    )
    assert {"ceiling", "model", "engine", "ladder", "order"} <= set(policy.tier_keys)
    assert {"codex", "glm", "code-edit"} <= set(policy.engine_names)
    handler_source = (
        Path(__file__).parents[4]
        / "src/omnibase_core/validation/hardcoded_model_config/handler.py"
    ).read_text(encoding="utf-8")
    for name in ("sonnet", "opus", "codex", "glm", "ceiling"):
        assert f'"{name}"' not in handler_source


@pytest.mark.unit
def test_tn_families_apply_to_source_only(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    for path_class in policy.path_classes:
        has = {"T", "N"} & set(path_class.families)
        assert has == ({"T", "N"} if path_class.name == "SOURCE" else set()), (
            path_class.name
        )


@pytest.mark.unit
def test_tn_findings_baseline_by_content_like_every_family(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    from omnibase_core.validation.hardcoded_model_config.handler import (
        compare_with_baseline,
    )
    from omnibase_core.validation.hardcoded_model_config.models import (
        ModelHardcodedModelConfigBaselineEntry,
    )

    findings = scan("src/pkg/a.py", 'ceiling = "opus"\n', policy)
    assert [f.family for f in findings] == ["T"]
    new, stale = compare_with_baseline(
        findings, [], frozenset({"src/pkg/a.py"}), frozenset()
    )
    assert new == findings and stale == []
    entry = ModelHardcodedModelConfigBaselineEntry(
        path="src/pkg/a.py", family="T", content_sha1=findings[0].content_sha1
    )
    new, stale = compare_with_baseline(
        findings, [entry], frozenset({"src/pkg/a.py"}), frozenset()
    )
    assert new == [] and stale == []


@pytest.mark.unit
def test_committed_baseline_holds_no_tier_or_engine_entry() -> None:
    """OMN-21463: the current tree was fixed, not baselined, for families T and N."""
    baseline = yaml.safe_load(
        (
            Path(__file__).parents[4] / "config/hardcoded_model_config_baseline.yaml"
        ).read_text(encoding="utf-8")
    )
    assert {e["family"] for e in baseline["entries"]}.isdisjoint({"T", "N"})


@pytest.mark.unit
def test_tn_findings_equal_the_committed_golden_report(
    policy: ModelHardcodedModelConfigPolicy,
) -> None:
    golden = yaml.safe_load(
        (CORPUS_DIR / "golden_tn_findings.yaml").read_text(encoding="utf-8")
    )["findings"]
    actual: dict[str, list[dict[str, object]]] = {}
    for name in golden:
        path = FIXTURES[name]["path"]
        assert isinstance(path, str)
        text = (CORPUS_DIR / name).read_text(encoding="utf-8")
        actual[name] = [
            {
                "line": f.line,
                "family": f.family,
                "matched_text": f.matched_text,
                "path_class": f.path_class,
            }
            for f in scan(path, text, policy)
        ]
    assert actual == golden
    assert set(golden) >= set(_TN_VIOLATIONS)
