# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ValidatorUrlAuthority (OMN-12818).

Covers:
- Detection of all three violation classes (public-https-literal, env-url-read,
  url-const-assignment)
- Suppression annotations (# url-authority-ok:, # contract-config-ok:)
- Authority-path and test-path exclusions
- Ratchet: new fingerprints fail, grandfathered fingerprints pass
- Baseline helpers: load_baseline, serialize_baseline, assert_baseline_shrinks_only
- ValidatorBase integration (validate() returns ModelValidationResult)
- CLI entry point: --all, staged-files, exit codes
- Synthetic violation proves gate goes RED on new URL literal
- Baselined tip proves gate stays GREEN when fingerprint is in baseline
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_url_authority import (
    RULE_CONST_ASSIGNMENT,
    RULE_ENV_URL_READ,
    RULE_LOCALHOST_LITERAL,
    RULE_PUBLIC_HTTPS,
    ValidatorUrlAuthority,
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
        {"repo": "r", "path": "p", "rule": "public-https-literal", "fingerprint": fp}
        for fp in fingerprints
    ]
    b.write_text(
        json.dumps(
            {"schema_version": "1.0.0", "count": len(entries), "violations": entries}
        ),
        encoding="utf-8",
    )
    return b


def _open_contract() -> ModelValidatorSubcontract:
    """Minimal contract with all three url-authority rules enabled and no excludes.

    Used in ValidatorBase integration tests to avoid the default contract's
    exclude_patterns accidentally matching pytest temp directory names.
    """
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="url_authority",
        validator_name="Test",
        validator_description="Test",
        target_patterns=["**/*.py"],
        exclude_patterns=[],
        suppression_comments=["# url-authority-ok:", "# contract-config-ok:"],
        fail_on_error=True,
        fail_on_warning=False,
        severity_default=EnumSeverity.ERROR,
        rules=[
            ModelValidatorRule(
                rule_id=RULE_PUBLIC_HTTPS,
                description="test",
                severity=EnumSeverity.ERROR,
                enabled=True,
            ),
            ModelValidatorRule(
                rule_id=RULE_ENV_URL_READ,
                description="test",
                severity=EnumSeverity.ERROR,
                enabled=True,
            ),
            ModelValidatorRule(
                rule_id=RULE_CONST_ASSIGNMENT,
                description="test",
                severity=EnumSeverity.ERROR,
                enabled=True,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Unit: scan_source
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanSource:
    def test_public_https_literal_detected(self) -> None:
        src = 'url = "https://api.example-service.com/v1"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_PUBLIC_HTTPS

    def test_env_url_read_detected(self) -> None:
        src = 'base = os.environ["MY_SERVICE_URL"]\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_ENV_URL_READ

    def test_env_url_read_get_detected(self) -> None:
        src = 'base = os.environ.get("DOWNSTREAM_ENDPOINT", "")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_ENV_URL_READ

    def test_const_url_from_env_detected(self) -> None:
        # env-url-read fires before url-const-assignment when the line contains
        # both an os.environ[...] read AND a *_URL variable name — only one
        # violation per line is reported (the first matching rule wins).
        src = 'BASE_URL = os.environ["BASE_URL"]\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule in (RULE_CONST_ASSIGNMENT, RULE_ENV_URL_READ)

    def test_const_url_from_literal_detected(self) -> None:
        src = 'API_ENDPOINT = "https://api.service.io/v2"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_CONST_ASSIGNMENT

    def test_env_url_read_not_matched_for_api_key(self) -> None:
        src = 'key = os.environ["LINEAR_API_KEY"]\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_env_url_read_not_matched_for_token(self) -> None:
        src = 'tok = os.environ["GITHUB_TOKEN"]\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_comment_only_line_skipped(self) -> None:
        src = "# https://api.example-service.com/v1\n"
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_suppression_annotation_clears(self) -> None:
        src = 'url = "https://api.example-service.com/v1"  # url-authority-ok: legacy\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_config_path_annotation_clears_env_read(self) -> None:
        src = 'path = os.environ.get("CONTRACT_URL", "")  # contract-config-ok: path\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_example_host_excluded(self) -> None:
        src = 'x = "https://example.com/api"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_github_permalink_excluded(self) -> None:
        src = 'link = "https://github.com/OmniNode-ai/omnibase_core/pull/123"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_api_github_com_matched(self) -> None:
        # api.github.com is a connection target; github.com display links are not
        src = 'url = "https://api.github.com/repos"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_PUBLIC_HTTPS

    def test_test_path_skipped(self) -> None:
        src = 'url = "https://api.example-service.com/v1"\n'
        vs = scan_source("r", "tests/test_something.py", src)
        assert vs == []

    def test_authority_path_skipped(self) -> None:
        src = 'url = "https://api.example-service.com/v1"\n'
        vs = scan_source("r", "configs/bifrost_delegation.yaml", src)
        assert vs == []

    def test_schema_ref_excluded(self) -> None:
        src = 'schema = "https://json-schema.org/draft/2020-12/schema"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_fingerprint_is_deterministic(self) -> None:
        src = 'url = "https://api.example-service.com/v1"\n'
        vs1 = scan_source("r", "src/pkg/a.py", src)
        vs2 = scan_source("r", "src/pkg/a.py", src)
        assert vs1[0].fingerprint == vs2[0].fingerprint

    def test_fingerprint_changes_with_snippet(self) -> None:
        src1 = 'url = "https://api.example-service.com/v1"\n'
        src2 = 'url = "https://api.different-host.com/v1"\n'
        v1 = scan_source("r", "src/pkg/a.py", src1)[0]
        v2 = scan_source("r", "src/pkg/a.py", src2)[0]
        assert v1.fingerprint != v2.fingerprint


# ---------------------------------------------------------------------------
# Unit: localhost / loopback literal coverage (OMN-13480)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLocalhostLiteral:
    """OMN-13480: hardcoded loopback connection-target literals are flagged.

    The public-https rule deliberately skips localhost (no dotted TLD); these
    cases prove the dedicated localhost-literal rule closes that gap without
    re-firing for placeholders or suppressed lines (no false positives).
    """

    def test_http_localhost_with_port_detected(self) -> None:
        # Planted adversarial case: a bare loopback literal passed to a client
        # call — NOT a *_URL constant, so only the localhost rule can catch it.
        src = 'resp = httpx.get("http://localhost:9000/v1/chat")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_LOCALHOST_LITERAL

    def test_https_localhost_detected(self) -> None:
        src = 'client.post("https://localhost/health")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_LOCALHOST_LITERAL

    def test_ipv4_loopback_detected(self) -> None:
        src = 'conn = connect("http://127.0.0.1:5432")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_LOCALHOST_LITERAL

    def test_wildcard_bind_address_detected(self) -> None:
        src = 'probe("http://0.0.0.0:8080/ready")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_LOCALHOST_LITERAL

    def test_ipv6_loopback_detected(self) -> None:
        src = 'ping("http://[::1]:6379")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_LOCALHOST_LITERAL

    def test_localhost_url_const_still_const_assignment(self) -> None:
        # A *_URL constant holding a localhost literal stays url-const-assignment
        # (env-url-read / const rules win earlier in _match_rule) — behavior is
        # unchanged for the case that was already covered.
        src = 'LOCAL_LLM_URL = "http://localhost:8000"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_CONST_ASSIGNMENT

    def test_localhost_suppression_annotation_clears(self) -> None:
        src = (
            'resp = httpx.get("http://localhost:9000")'
            "  # url-authority-ok: dev-only probe\n"
        )
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_localhost_in_comment_skipped(self) -> None:
        src = "# call http://localhost:9000 during local dev\n"
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_localhost_in_test_path_skipped(self) -> None:
        src = 'resp = httpx.get("http://localhost:9000")\n'
        vs = scan_source("r", "tests/test_thing.py", src)
        assert vs == []

    def test_non_loopback_host_not_localhost_rule(self) -> None:
        # A real public host that merely starts with 'localhost' must not trip
        # the loopback rule; the public-https rule owns it (dotted TLD present).
        src = 'url = "https://localhost-proxy.service.io/api"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_PUBLIC_HTTPS


# ---------------------------------------------------------------------------
# Unit: ratchet helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRatchet:
    def test_partition_new_vs_grandfathered(self) -> None:
        src = 'url = "https://api.example-service.com/v1"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        fp = vs[0].fingerprint

        new, grand = partition_against_baseline(vs, {fp})
        assert new == []
        assert len(grand) == 1

        new2, grand2 = partition_against_baseline(vs, set())
        assert len(new2) == 1
        assert grand2 == []

    def test_assert_baseline_shrinks_only_pass(self) -> None:
        # Shrinking is allowed
        assert_baseline_shrinks_only({"a", "b"}, {"a"})

    def test_assert_baseline_shrinks_only_same(self) -> None:
        # Staying same is allowed
        assert_baseline_shrinks_only({"a"}, {"a"})

    def test_assert_baseline_shrinks_only_fails_on_growth(self) -> None:
        with pytest.raises(ValueError, match="grew"):
            assert_baseline_shrinks_only({"a"}, {"a", "b"})

    def test_load_baseline_missing_file(self, tmp_path: Path) -> None:
        result = load_baseline(tmp_path / "missing.json")
        assert result == set()

    def test_load_baseline_reads_fingerprints(self, tmp_path: Path) -> None:
        b = _baseline_with({"abc123", "def456"}, tmp_path)
        result = load_baseline(b)
        assert result == {"abc123", "def456"}

    def test_serialize_baseline_deduplicates(self) -> None:
        src = 'url = "https://api.example-service.com/v1"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        # Duplicate the same violation
        doc = serialize_baseline(vs + vs)
        assert doc["count"] == 1

    def test_make_fingerprint_stable(self) -> None:
        fp1 = make_fingerprint("repo", "path/to/file.py", 'url = "https://api.svc.com"')
        fp2 = make_fingerprint("repo", "path/to/file.py", 'url = "https://api.svc.com"')
        assert fp1 == fp2

    def test_make_fingerprint_whitespace_normalized(self) -> None:
        fp1 = make_fingerprint("r", "p", 'url  =  "https://api.svc.com"')
        fp2 = make_fingerprint("r", "p", 'url = "https://api.svc.com"')
        assert fp1 == fp2


# ---------------------------------------------------------------------------
# Integration: ValidatorUrlAuthority (ValidatorBase subclass)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatorUrlAuthorityIntegration:
    def test_synthetic_violation_gate_red(self, tmp_path: Path) -> None:
        """Synthetic URL env literal — gate must be RED (new fingerprint).

        Uses an open contract (no exclude_patterns) so pytest temp dirs with
        'test' in their name don't accidentally suppress the file.
        """
        f = _write(
            tmp_path, 'BASE_URL = "https://api.totally-new-host.io/v1"\n', "src/m.py"
        )
        empty_baseline = tmp_path / "baseline.json"
        empty_baseline.write_text(
            json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
            encoding="utf-8",
        )

        v = ValidatorUrlAuthority(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=empty_baseline,
        )
        result = v.validate_file(f)
        assert not result.is_valid, f"Expected RED but got: {result.issues}"
        assert len(result.issues) == 1
        assert result.issues[0].code in (RULE_CONST_ASSIGNMENT, RULE_PUBLIC_HTTPS)

    def test_baselined_violation_gate_green(self, tmp_path: Path) -> None:
        """Baselined tip — gate must stay GREEN (fingerprint in baseline).

        repo_root=tmp_path ensures the validator computes the same repo-relative
        path ('src/m.py') that make_fingerprint uses here.
        """
        snippet = 'BASE_URL = "https://api.totally-new-host.io/v1"'
        f = _write(tmp_path, snippet + "\n", "src/m.py")
        fp = make_fingerprint("test_repo", "src/m.py", snippet)
        baseline_path = _baseline_with({fp}, tmp_path)

        v = ValidatorUrlAuthority(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=baseline_path,
            repo_root=tmp_path,
        )
        result = v.validate_file(f)
        assert result.is_valid, f"Expected green but got: {result.issues}"

    def test_suppressed_line_gate_green(self, tmp_path: Path) -> None:
        """Suppressed line — gate stays GREEN regardless of baseline."""
        f = _write(
            tmp_path,
            'BASE_URL = "https://api.service.com/v1"  # url-authority-ok: legacy-migration\n',
            "src/m.py",
        )
        empty_baseline = tmp_path / "baseline.json"
        empty_baseline.write_text(
            json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
            encoding="utf-8",
        )

        v = ValidatorUrlAuthority(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=empty_baseline,
        )
        result = v.validate_file(f)
        assert result.is_valid

    def test_validator_id(self) -> None:
        assert ValidatorUrlAuthority.validator_id == "url_authority"

    def test_multiple_rules_reported(self, tmp_path: Path) -> None:
        """Multiple violation types in one file are all reported."""
        src = textwrap.dedent(
            """\
            import os
            API_URL = os.environ["REMOTE_URL"]
            KEY = os.environ["API_KEY"]
            PUBLIC_ENDPOINT = "https://api.service.io/v1"
            """
        )
        f = _write(tmp_path, src, "src/m.py")
        empty_baseline = tmp_path / "baseline.json"
        empty_baseline.write_text(
            json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
            encoding="utf-8",
        )
        v = ValidatorUrlAuthority(
            contract=_open_contract(),
            repo="test_repo",
            baseline_path=empty_baseline,
        )
        result = v.validate_file(f)
        assert not result.is_valid
        # API_KEY read is NOT a violation; REMOTE_URL and PUBLIC_ENDPOINT are
        codes = {i.code for i in result.issues}
        assert RULE_ENV_URL_READ in codes or RULE_CONST_ASSIGNMENT in codes


# ---------------------------------------------------------------------------
# Integration: scan_tree
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanTree:
    def test_scan_tree_finds_violations(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        f = tmp_path / "src" / "module.py"
        f.write_text('url = "https://api.example-service.com/v1"\n', encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        assert any(v.path.endswith("module.py") for v in vs)

    def test_scan_tree_excludes_tests(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        f = tmp_path / "tests" / "test_m.py"
        f.write_text('url = "https://api.example-service.com/v1"\n', encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        assert vs == []

    def test_scan_tree_uses_relative_paths(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        f = tmp_path / "src" / "pkg.py"
        f.write_text('url = "https://api.example-service.com/v1"\n', encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        # Paths must be relative (no absolute prefix)
        for v in vs:
            assert not v.path.startswith("/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCLI:
    def test_no_files_exit_0(self, capsys: pytest.CaptureFixture[str]) -> None:
        from omnibase_core.validation.validator_url_authority import main

        rc = main([])
        assert rc == 0
        captured = capsys.readouterr()
        assert "no files" in captured.out.lower()

    def test_new_violation_exit_1(self, tmp_path: Path) -> None:
        from omnibase_core.validation.validator_url_authority import main

        f = _write(tmp_path, 'BASE_URL = "https://api.new-host.io/v1"\n', "mod.py")
        baseline = tmp_path / "baseline.json"
        baseline.write_text(
            json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
            encoding="utf-8",
        )
        rc = main(
            [
                str(f),
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(baseline),
            ]
        )
        assert rc == 1

    def test_grandfathered_violation_exit_0(self, tmp_path: Path) -> None:
        from omnibase_core.validation.validator_url_authority import main

        snippet = 'BASE_URL = "https://api.new-host.io/v1"'
        f = _write(tmp_path, snippet + "\n", "mod.py")
        fp = make_fingerprint("r", "mod.py", snippet)
        baseline = _baseline_with({fp}, tmp_path)
        rc = main(
            [
                str(f),
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(baseline),
            ]
        )
        assert rc == 0

    def test_seed_creates_baseline(self, tmp_path: Path) -> None:
        from omnibase_core.validation.validator_url_authority import main

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text(
            'url = "https://api.example-service.com/v1"\n', encoding="utf-8"
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
        data = json.loads(baseline.read_text())
        assert data["count"] >= 1

    def test_update_baseline_rejects_growth(self, tmp_path: Path) -> None:
        from omnibase_core.validation.validator_url_authority import main

        # Baseline has one fingerprint; repo has a different one (growing the set)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text(
            'url = "https://api.example-service.com/v1"\n', encoding="utf-8"
        )
        # Pre-seed so baseline has a DIFFERENT fingerprint
        pre_seed_fp = make_fingerprint(
            "r", "src/fake.py", "FAKE_URL = os.environ['X_URL']"
        )
        baseline = _baseline_with({pre_seed_fp}, tmp_path)
        rc = main(
            [
                "--update-baseline",
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(baseline),
            ]
        )
        # Growth detected — must reject
        assert rc == 1


# ---------------------------------------------------------------------------
# Integration catalog structure (OMN-12804)
# ---------------------------------------------------------------------------

_CATALOG_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "omnibase_core"
    / "contracts"
    / "integrations"
    / "catalog.yaml"
)


@pytest.mark.unit
class TestIntegrationCatalogStructure:
    """Verify the non-model URL authority catalog is structurally valid.

    These tests do NOT import the catalog resolver (which doesn't ship yet)
    — they validate the YAML document shape so any future parser has a stable
    contract to target (OMN-12804).
    """

    def test_catalog_file_exists(self) -> None:
        """The authority catalog must be checked in at the canonical path."""
        assert _CATALOG_PATH.exists(), (
            f"Integration catalog not found at {_CATALOG_PATH}. "
            "Every non-model URL must resolve from this authority file."
        )

    def test_catalog_is_valid_yaml(self) -> None:
        """The catalog must parse as valid YAML."""
        raw = _CATALOG_PATH.read_text(encoding="utf-8")
        doc = yaml.safe_load(raw)
        assert isinstance(doc, dict), "Catalog root must be a YAML mapping"

    def test_catalog_has_required_top_level_keys(self) -> None:
        """The catalog must declare catalog_version and schema_version."""
        doc = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
        assert "catalog_version" in doc, "Missing catalog_version"
        assert "schema_version" in doc, "Missing schema_version"
        # catalog_version must be a semver dict {major, minor, patch}
        cv = doc["catalog_version"]
        assert isinstance(cv, dict) and {"major", "minor", "patch"} <= cv.keys(), (
            f"catalog_version must be {{major: X, minor: Y, patch: Z}}, got: {cv!r}"
        )

    def test_catalog_has_at_least_one_category(self) -> None:
        """The catalog must have at least one of: external_apis, internal_infra, env_resolved."""
        doc = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
        categories = {"external_apis", "internal_infra", "env_resolved"}
        found = categories & set(doc.keys())
        assert found, (
            f"No known category found in catalog. Expected one of: {categories}"
        )

    def test_every_entry_has_id_and_description(self) -> None:
        """Every entry in every category must have id and description fields."""
        doc = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
        for category in ("external_apis", "internal_infra", "env_resolved"):
            entries = doc.get(category) or []
            for entry in entries:
                assert "id" in entry, f"Missing 'id' in {category} entry: {entry}"
                assert "description" in entry, (
                    f"Missing 'description' in {category} entry: {entry.get('id', entry)}"
                )

    def test_every_entry_has_endpoint_url_or_env(self) -> None:
        """Every entry must declare endpoint_url and/or endpoint_url_env — never neither."""
        doc = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
        for category in ("external_apis", "internal_infra", "env_resolved"):
            entries = doc.get(category) or []
            for entry in entries:
                has_url = "endpoint_url" in entry
                has_env = "endpoint_url_env" in entry
                assert has_url or has_env, (
                    f"Entry {entry.get('id', '?')} in {category} must have "
                    "at least one of: endpoint_url, endpoint_url_env"
                )

    def test_catalog_path_suffix_matches_authority_allowlist(self) -> None:
        """The catalog path must end with the suffix recognized by ValidatorUrlAuthority.

        This ensures URLs placed in the catalog are treated as canonical by the
        gate and not flagged as violations.
        """
        from omnibase_core.validation.validator_url_authority import (
            _AUTHORITY_PATH_SUFFIXES,
        )

        catalog_rel = str(_CATALOG_PATH).replace("\\", "/")
        matched = any(
            catalog_rel.endswith(suffix) for suffix in _AUTHORITY_PATH_SUFFIXES
        )
        assert matched, (
            f"Catalog path {catalog_rel!r} does not end with any known authority "
            f"suffix: {_AUTHORITY_PATH_SUFFIXES}.  "
            "Add the suffix to _AUTHORITY_PATH_SUFFIXES in validator_url_authority.py."
        )

    def test_catalog_contains_github_entry(self) -> None:
        """A GitHub API entry must exist — it is the highest-frequency integration."""
        doc = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
        ids = {e["id"] for e in (doc.get("external_apis") or [])}
        assert "github.rest_api" in ids, (
            "github.rest_api entry missing from external_apis. "
            "Every GitHub API call must resolve from this catalog."
        )

    def test_catalog_contains_linear_entry(self) -> None:
        """A Linear GraphQL entry must exist."""
        doc = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
        ids = {e["id"] for e in (doc.get("external_apis") or [])}
        assert "linear.graphql_api" in ids, (
            "linear.graphql_api entry missing from external_apis."
        )
