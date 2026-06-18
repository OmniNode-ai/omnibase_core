# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ValidatorCanonicalInference (OMN-13219).

Covers:
- Detection of both violation classes (model-cli-shellout, model-id-env-read)
- Suppression annotation (# canonical-inference-ok:)
- Test-path exclusion
- Fail-closed: a shelled-CLI inference tier and a hardcoded/env model each trip
  the gate (exit 1); the canonical contract-resolved path passes (exit 0)
- Ratchet: new fingerprints fail, grandfathered fingerprints pass
- Baseline helpers: load_baseline, serialize_baseline, assert_baseline_shrinks_only
- ValidatorBase integration (validate() returns ModelValidationResult)
- CLI entry point: --all, staged-files, exit codes, seed, baseline-growth reject
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_canonical_inference import (
    RULE_MODEL_CLI_SHELLOUT,
    RULE_MODEL_ENV_READ,
    ValidatorCanonicalInference,
    assert_baseline_shrinks_only,
    load_baseline,
    make_fingerprint,
    partition_against_baseline,
    scan_source,
    scan_tree,
    serialize_baseline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, content: str, name: str = "mod.py") -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _baseline_with(fingerprints: set[str], tmp_path: Path) -> Path:
    b = tmp_path / "baseline.json"
    entries = [
        {"repo": "r", "path": "p", "rule": RULE_MODEL_CLI_SHELLOUT, "fingerprint": fp}
        for fp in fingerprints
    ]
    b.write_text(
        json.dumps(
            {"schema_version": "1.0.0", "count": len(entries), "violations": entries}
        ),
        encoding="utf-8",
    )
    return b


def _empty_baseline(tmp_path: Path) -> Path:
    b = tmp_path / "baseline.json"
    b.write_text(
        json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
        encoding="utf-8",
    )
    return b


def _open_contract() -> ModelValidatorSubcontract:
    """Minimal contract with both canonical-inference rules enabled and no excludes."""
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="canonical_inference",
        validator_name="Test",
        validator_description="Test",
        target_patterns=["**/*.py"],
        exclude_patterns=[],
        suppression_comments=["# canonical-inference-ok:"],
        fail_on_error=True,
        fail_on_warning=False,
        severity_default=EnumSeverity.ERROR,
        rules=[
            ModelValidatorRule(
                rule_id=RULE_MODEL_CLI_SHELLOUT,
                description="test",
                severity=EnumSeverity.ERROR,
                enabled=True,
            ),
            ModelValidatorRule(
                rule_id=RULE_MODEL_ENV_READ,
                description="test",
                severity=EnumSeverity.ERROR,
                enabled=True,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Unit: scan_source — model-cli-shellout
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanShellout:
    def test_subprocess_run_codex_detected(self) -> None:
        src = 'subprocess.run(["codex", "exec", prompt])\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_CLI_SHELLOUT

    def test_subprocess_run_codex_str_program_detected(self) -> None:
        src = 'subprocess.run("codex exec", shell=True)\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_CLI_SHELLOUT

    def test_popen_claude_detected(self) -> None:
        src = 'proc = subprocess.Popen(["claude", "-p", prompt])\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_CLI_SHELLOUT

    def test_create_subprocess_exec_gemini_detected(self) -> None:
        src = 'await asyncio.create_subprocess_exec("gemini", "-p", prompt)\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_CLI_SHELLOUT

    def test_os_system_codex_detected(self) -> None:
        src = 'os.system("codex exec hi")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_CLI_SHELLOUT

    def test_shutil_which_codex_detected(self) -> None:
        src = 'executable = shutil.which("codex")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_CLI_SHELLOUT

    def test_abs_path_codex_detected(self) -> None:
        src = 'subprocess.run(["/usr/local/bin/codex", "exec"])\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_CLI_SHELLOUT

    def test_non_model_cli_not_detected(self) -> None:
        # git/docker/etc. are NOT model CLIs — not this gate's concern.
        src = 'subprocess.run(["git", "status"])\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_codex_as_arg_not_program_not_detected(self) -> None:
        # "codex" appears as a non-head list element (an argument, not the
        # program) — not a shell-out of the codex binary.
        src = 'subprocess.run(["echo", "codex"])\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_codex_string_in_unrelated_call_not_detected(self) -> None:
        src = 'logger.info("codex")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_shellout_suppressed(self) -> None:
        src = 'subprocess.run(["codex", "exec"])  # canonical-inference-ok: legacy\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []


# ---------------------------------------------------------------------------
# Unit: scan_source — model-id-env-read
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanEnvRead:
    def test_env_model_read_detected(self) -> None:
        src = 'model = os.environ["LLM_MODEL"]\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_ENV_READ

    def test_env_provider_read_get_detected(self) -> None:
        src = 'provider = os.environ.get("INFERENCE_PROVIDER", "")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MODEL_ENV_READ

    def test_env_api_key_not_detected(self) -> None:
        # api-key reads stay legal — secrets resolve at the effect boundary.
        src = 'key = os.environ["LINEAR_API_KEY"]\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_env_url_not_this_gate(self) -> None:
        # *_URL is the URL-authority gate's concern, not this one.
        src = 'base = os.environ["LLM_URL"]\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_comment_only_env_read_skipped(self) -> None:
        src = '# model = os.environ["LLM_MODEL"]\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_env_read_suppressed(self) -> None:
        src = 'm = os.environ["LLM_MODEL"]  # canonical-inference-ok: bootstrap\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []


# ---------------------------------------------------------------------------
# Unit: path handling + fingerprints
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPathsAndFingerprints:
    def test_test_path_skipped(self) -> None:
        src = 'subprocess.run(["codex", "exec"])\n'
        vs = scan_source("r", "tests/test_something.py", src)
        assert vs == []

    def test_fingerprint_is_deterministic(self) -> None:
        src = 'shutil.which("codex")\n'
        v1 = scan_source("r", "src/pkg/a.py", src)[0]
        v2 = scan_source("r", "src/pkg/a.py", src)[0]
        assert v1.fingerprint == v2.fingerprint

    def test_fingerprint_changes_with_snippet(self) -> None:
        v1 = scan_source("r", "src/pkg/a.py", 'shutil.which("codex")\n')[0]
        v2 = scan_source("r", "src/pkg/a.py", 'shutil.which("claude")\n')[0]
        assert v1.fingerprint != v2.fingerprint

    def test_make_fingerprint_whitespace_normalized(self) -> None:
        # _normalize collapses internal whitespace RUNS to a single space and
        # strips ends; double-space vs single-space hash identically.
        fp1 = make_fingerprint("r", "p", '  shutil.which("codex")  ')
        fp2 = make_fingerprint("r", "p", 'shutil.which("codex")')
        assert fp1 == fp2


# ---------------------------------------------------------------------------
# Unit: ratchet helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRatchet:
    def test_partition_new_vs_grandfathered(self) -> None:
        vs = scan_source("r", "src/pkg/a.py", 'shutil.which("codex")\n')
        assert len(vs) == 1
        fp = vs[0].fingerprint

        new, grand = partition_against_baseline(vs, {fp})
        assert new == []
        assert len(grand) == 1

        new2, grand2 = partition_against_baseline(vs, set())
        assert len(new2) == 1
        assert grand2 == []

    def test_assert_baseline_shrinks_only_pass(self) -> None:
        assert_baseline_shrinks_only({"a", "b"}, {"a"})

    def test_assert_baseline_shrinks_only_same(self) -> None:
        assert_baseline_shrinks_only({"a"}, {"a"})

    def test_assert_baseline_shrinks_only_fails_on_growth(self) -> None:
        with pytest.raises(ValueError, match="grew"):
            assert_baseline_shrinks_only({"a"}, {"a", "b"})

    def test_load_baseline_missing_file(self, tmp_path: Path) -> None:
        assert load_baseline(tmp_path / "missing.json") == set()

    def test_load_baseline_reads_fingerprints(self, tmp_path: Path) -> None:
        b = _baseline_with({"abc123", "def456"}, tmp_path)
        assert load_baseline(b) == {"abc123", "def456"}

    def test_serialize_baseline_deduplicates(self) -> None:
        vs = scan_source("r", "src/pkg/a.py", 'shutil.which("codex")\n')
        doc = serialize_baseline(vs + vs)
        assert doc["count"] == 1


# ---------------------------------------------------------------------------
# Integration: ValidatorCanonicalInference (ValidatorBase subclass)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatorIntegration:
    def test_shellout_gate_red(self, tmp_path: Path) -> None:
        """Fail-closed: a NEW shelled-CLI inference tier trips the gate."""
        f = _write(tmp_path, 'subprocess.run(["codex", "exec", p])\n', "src/m.py")
        v = ValidatorCanonicalInference(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=_empty_baseline(tmp_path),
        )
        result = v.validate_file(f)
        assert not result.is_valid, f"Expected RED but got: {result.issues}"
        assert result.issues[0].code == RULE_MODEL_CLI_SHELLOUT

    def test_env_model_gate_red(self, tmp_path: Path) -> None:
        """Fail-closed: a NEW env-resolved model trips the gate."""
        f = _write(tmp_path, 'model = os.environ["LLM_MODEL"]\n', "src/m.py")
        v = ValidatorCanonicalInference(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=_empty_baseline(tmp_path),
        )
        result = v.validate_file(f)
        assert not result.is_valid
        assert result.issues[0].code == RULE_MODEL_ENV_READ

    def test_canonical_path_gate_green(self, tmp_path: Path) -> None:
        """The contract-resolved tier (OMN-13215 target shape) passes the gate.

        Resolving model/provider/endpoint from the routing contract + dispatching
        over the bus contains no shell-out and no env read — zero violations.
        """
        src = textwrap.dedent(
            """\
            tier = routing.resolve_tier(task_type)
            envelope = build_inference_envelope(
                model=tier.selected_model,
                provider=tier.provider,
                endpoint_url=tier.endpoint_url,
                api_key_ref=tier.api_key_ref,
            )
            response = await event_bus.publish(envelope)
            """
        )
        f = _write(tmp_path, src, "src/m.py")
        v = ValidatorCanonicalInference(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=_empty_baseline(tmp_path),
        )
        result = v.validate_file(f)
        assert result.is_valid, f"Expected GREEN but got: {result.issues}"

    def test_baselined_shellout_gate_green(self, tmp_path: Path) -> None:
        """Grandfathered (baselined) shell-out passes — burn-down tracked elsewhere."""
        snippet = 'subprocess.run(["codex", "exec", p])'
        f = _write(tmp_path, snippet + "\n", "src/m.py")
        fp = make_fingerprint("test_repo", "src/m.py", snippet)
        v = ValidatorCanonicalInference(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=_baseline_with({fp}, tmp_path),
            repo_root=tmp_path,
        )
        result = v.validate_file(f)
        assert result.is_valid, f"Expected green but got: {result.issues}"

    def test_suppressed_line_gate_green(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'subprocess.run(["codex", "exec"])  # canonical-inference-ok: legacy\n',
            "src/m.py",
        )
        v = ValidatorCanonicalInference(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=_empty_baseline(tmp_path),
        )
        result = v.validate_file(f)
        assert result.is_valid

    def test_validator_id(self) -> None:
        assert ValidatorCanonicalInference.validator_id == "canonical_inference"


# ---------------------------------------------------------------------------
# Integration: scan_tree
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanTree:
    def test_scan_tree_finds_violations(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text(
            'shutil.which("codex")\n', encoding="utf-8"
        )
        vs = scan_tree("r", tmp_path)
        assert any(v.path.endswith("module.py") for v in vs)

    def test_scan_tree_excludes_tests(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_m.py").write_text(
            'subprocess.run(["codex"])\n', encoding="utf-8"
        )
        assert scan_tree("r", tmp_path) == []

    def test_scan_tree_uses_relative_paths(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "pkg.py").write_text(
            'shutil.which("codex")\n', encoding="utf-8"
        )
        for v in scan_tree("r", tmp_path):
            assert not v.path.startswith("/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCLI:
    def test_no_files_exit_0(self, capsys: pytest.CaptureFixture[str]) -> None:
        from omnibase_core.validation.validator_canonical_inference import main

        rc = main([])
        assert rc == 0
        assert "no files" in capsys.readouterr().out.lower()

    def test_new_violation_exit_1(self, tmp_path: Path) -> None:
        from omnibase_core.validation.validator_canonical_inference import main

        f = _write(tmp_path, 'subprocess.run(["codex", "exec"])\n', "mod.py")
        rc = main(
            [
                str(f),
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(_empty_baseline(tmp_path)),
            ]
        )
        assert rc == 1

    def test_grandfathered_violation_exit_0(self, tmp_path: Path) -> None:
        from omnibase_core.validation.validator_canonical_inference import main

        snippet = 'subprocess.run(["codex", "exec"])'
        f = _write(tmp_path, snippet + "\n", "mod.py")
        fp = make_fingerprint("r", "mod.py", snippet)
        rc = main(
            [
                str(f),
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(_baseline_with({fp}, tmp_path)),
            ]
        )
        assert rc == 0

    def test_seed_creates_baseline(self, tmp_path: Path) -> None:
        from omnibase_core.validation.validator_canonical_inference import main

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text(
            'shutil.which("codex")\n', encoding="utf-8"
        )
        baseline = tmp_path / "baseline.json"
        rc = main(
            [
                "--seed",
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(baseline),
            ]
        )
        assert rc == 0
        assert baseline.exists()
        assert json.loads(baseline.read_text())["count"] >= 1

    def test_update_baseline_rejects_growth(self, tmp_path: Path) -> None:
        from omnibase_core.validation.validator_canonical_inference import main

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text(
            'shutil.which("codex")\n', encoding="utf-8"
        )
        # Pre-seed baseline with a DIFFERENT fingerprint so the repo scan grows it.
        pre_seed_fp = make_fingerprint("r", "src/fake.py", 'shutil.which("claude")')
        rc = main(
            [
                "--update-baseline",
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(_baseline_with({pre_seed_fp}, tmp_path)),
            ]
        )
        assert rc == 1
