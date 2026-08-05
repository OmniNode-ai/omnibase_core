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
    RULE_MSK_DIRECT_BROKER,
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

    def test_localhost_query_literal_detected(self) -> None:
        src = 'resp = httpx.get("http://localhost?probe=1")\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_LOCALHOST_LITERAL

    def test_loopback_fragment_literal_detected(self) -> None:
        src = 'resp = httpx.get("http://127.0.0.1#dev")\n'
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

    def test_localhost_in_json_object_literal_skipped(self) -> None:
        src = '{"callback":"http://localhost:9000"}\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_non_loopback_host_not_localhost_rule(self) -> None:
        # A real public host that merely starts with 'localhost' must not trip
        # the loopback rule; the public-https rule owns it (dotted TLD present).
        src = 'url = "https://localhost-proxy.service.io/api"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_PUBLIC_HTTPS


# ---------------------------------------------------------------------------
# Unit: msk-direct-broker-endpoint (OMN-15692, ruling 39)
# ---------------------------------------------------------------------------

# Real fixture strings, deliberately reconstructed from parts so this test
# file itself does not trip the rule it is proving (see the validator's own
# module docstring for the identical self-collision concern).
_MSK_BASTION_IP_LITERAL = "100" + "." + "53" + "." + "215" + "." + "198"
_MSK_HOSTNAME_LITERAL = (
    "b-1.omninodedevmsk.7ozyd3.c14.kafka.us-east-1" + "." + "amazonaws" + "." + "com"
)


@pytest.mark.unit
class TestMskDirectBrokerEndpoint:
    """OMN-15692 (operator ruling 2026-08-04): on-prem hosts must never hold a
    direct MSK broker literal — everything routes through the gateway.

    Proves the rule fires on the two cited literal shapes (hostname+port,
    bare bastion IP) AND does not fire on unrelated content — a guard that
    fires everywhere is as broken as one that fires nowhere.
    """

    # -- RED: the two AC(e)-cited trigger shapes ---------------------------

    def test_bastion_ip_alone_detected_in_yaml(self) -> None:
        # Real shape: Docker Compose `extra_hosts` maps hostname -> bare IP,
        # no port literal at all (docker-compose.gateway.yml L50-52).
        src = f'    - "{_MSK_HOSTNAME_LITERAL}:{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("omnibase_infra", "docker/docker-compose.gateway.yml", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_broker_hostname_with_msk_iam_port_detected(self) -> None:
        src = f'BOOTSTRAP = "{_MSK_HOSTNAME_LITERAL}:9098"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_broker_hostname_with_sasl_ssl_port_9096_detected(self) -> None:
        src = f'BOOTSTRAP = "{_MSK_HOSTNAME_LITERAL}:9096"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_detected_in_shell_script(self) -> None:
        src = f'echo "connecting to {_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "scripts/probe.sh", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_detected_in_toml(self) -> None:
        src = f'bootstrap_ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "config/gateway.toml", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_detected_in_python_too(self) -> None:
        # Rule 5 is NOT Python-exclusive — it also fires on .py, unlike the
        # file-scope restriction going the other direction (rules 1-4 do not
        # fire on non-.py).
        src = f'BASTION_IP = "{_MSK_BASTION_IP_LITERAL}"  # nosec\n'
        vs = scan_source("r", "src/pkg/gateway.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    # -- RED: the evasion classes a hostname/port-gated rule missed --------
    # (verifier round #2, 2026-08-04): the hostname trigger is deliberately
    # NOT gated on a co-occurring port literal. These four cases were the
    # cited evasions of the prior (port-gated) implementation; they must now
    # all detect.

    def test_hostname_with_arbitrary_port_detected(self) -> None:
        # Hostname present, port is neither 9098 nor 9096 — still MSK.
        src = f'BOOTSTRAP = "{_MSK_HOSTNAME_LITERAL}:9999"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_hostname_with_no_port_at_all_detected(self) -> None:
        # Hostname on its own, no port literal anywhere on the line.
        src = f'MSK_HOST: "{_MSK_HOSTNAME_LITERAL}"\n'
        vs = scan_source("r", "gateway/config.yaml", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_hostname_on_broker_tls_port_9094_detected(self) -> None:
        # MSK TLS port (not SASL_SSL/MSK-IAM 9098/9096) — equally direct.
        src = f'BOOTSTRAP = "{_MSK_HOSTNAME_LITERAL}:9094"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_split_key_host_port_config_shape_detected(self) -> None:
        # The default Docker Compose / .env shape: host and port declared as
        # separate keys on separate lines, not one hostname:port literal.
        src = f'MSK_HOST: "{_MSK_HOSTNAME_LITERAL}"\nMSK_PORT: "9098"\n'
        vs = scan_source("r", "gateway/config.yaml", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER
        assert vs[0].line == 1  # fires on the MSK_HOST line itself

    def test_other_aws_region_hostname_detected(self) -> None:
        # A different AWS region's kafka MSK hostname is equally "contacting
        # MSK directly" under the ruling — not scoped to us-east-1.
        src = 'BOOTSTRAP = "b-1.someothercluster.kafka.us-west-2.amazonaws.com:9098"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_hostname_substring_with_trailing_suffix_not_flagged(self) -> None:
        # CodeRabbit round-#3: an unbounded substring match on the hostname
        # pattern would false-positive on a longer, unrelated hostname that
        # merely contains the MSK suffix as a prefix — e.g. a doc/example
        # domain. The negative-lookahead token boundary must reject this.
        src = 'EXAMPLE = "b-1.somecluster.kafka.us-east-1.amazonaws.com.example"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 0

    def test_bastion_ip_substring_with_trailing_suffix_not_flagged(self) -> None:
        # Same class for the bastion-IP literal: a longer IP-like token that
        # merely starts with the bastion IP must not match.
        src = f'HOST = "{_MSK_BASTION_IP_LITERAL}.5"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 0

    def test_bastion_ip_substring_with_leading_prefix_not_flagged(self) -> None:
        # And the symmetric leading-digit case (e.g. an IP that ends with the
        # bastion IP's digits but is actually a longer, unrelated address).
        src = f'HOST = "1.{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 0

    def test_suppression_annotation_does_not_clear_msk_rule(self) -> None:
        # Rule 5 has no free-text escape hatch — a self-authored justification
        # comment must not waive a hard operator ruling (OMN-15692).
        src = (
            f'    - "{_MSK_HOSTNAME_LITERAL}:{_MSK_BASTION_IP_LITERAL}"  '
            "# url-authority-ok: needed for now\n"
        )
        vs = scan_source("r", "docker-compose.gateway.yml", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_other_rules_remain_suppressible(self) -> None:
        # Non-regression: the suppression carve-out is rule-5-scoped only —
        # rules 1-4 must still honor # url-authority-ok:.
        src = (
            'url = "https://api.example-service.com/v1"  '
            "# url-authority-ok: legacy, tracked\n"
        )
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    # -- GREEN: negative controls — must NOT fire ---------------------------

    def test_unrelated_ip_not_detected(self) -> None:
        src = 'gateway_ip = "10.40.139.135"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert vs == []

    def test_unrelated_https_url_not_detected(self) -> None:
        src = 'url = "https://api.example-service.com/v1"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert not any(v.rule == RULE_MSK_DIRECT_BROKER for v in vs)

    def test_unrelated_yaml_content_not_detected(self) -> None:
        # A generic compose file with no MSK/bastion literal at all.
        src = (
            "services:\n"
            "  web:\n"
            '    image: "nginx:latest"\n'
            "    ports:\n"
            '      - "8080:80"\n'
        )
        vs = scan_source("r", "docker-compose.yml", src)
        assert vs == []

    def test_comment_line_skipped(self) -> None:
        src = f"# bastion was {_MSK_BASTION_IP_LITERAL}, now retired\n"
        vs = scan_source("r", "docker-compose.yml", src)
        assert vs == []

    def test_test_path_skipped(self) -> None:
        src = f'ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "tests/fixtures/msk.yaml", src)
        assert vs == []

    # -- multi-line documentation spans (CodeRabbit round-#3, major) -------

    def test_interior_line_of_multiline_python_docstring_skipped(self) -> None:
        # A prior revision only recognized a docstring by checking whether
        # EACH line individually starts with '"""'/"'''" — an interior line
        # (this one) starts with ordinary text, so it was still scanned.
        src = (
            '"""Example config.\n'
            f"    Historically the bastion was {_MSK_BASTION_IP_LITERAL}.\n"
            '"""\n'
        )
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_single_quote_multiline_docstring_interior_skipped(self) -> None:
        src = (
            "'''Example config.\n"
            f"    Historically the bastion was {_MSK_BASTION_IP_LITERAL}.\n"
            "'''\n"
        )
        vs = scan_source("r", "src/pkg/a.py", src)
        assert vs == []

    def test_code_after_closed_docstring_still_scanned(self) -> None:
        # Non-regression: once a docstring closes, subsequent lines are
        # ordinary code again and must still be scanned.
        src = f'"""Example config."""\nBASTION_IP = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "src/pkg/a.py", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_ini_semicolon_comment_skipped(self) -> None:
        src = f"; bastion was {_MSK_BASTION_IP_LITERAL}, now retired\n"
        vs = scan_source("r", "gateway/config.ini", src)
        assert vs == []

    def test_cfg_semicolon_comment_skipped(self) -> None:
        src = f"; historical: {_MSK_HOSTNAME_LITERAL}\n"
        vs = scan_source("r", "gateway/config.cfg", src)
        assert vs == []

    def test_ini_semicolon_does_not_suppress_other_file_types(self) -> None:
        # Non-regression: ';' is only a comment marker for .ini/.cfg — a
        # line starting with ';' in a .env file is NOT a comment and must
        # still be scanned (defensive; '.env' files don't normally start
        # lines with ';', but the gate must not silently over-suppress).
        src = f';BASTION_IP="{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_tf_line_comment_skipped(self) -> None:
        src = f"// bastion was {_MSK_BASTION_IP_LITERAL}, now retired\n"
        vs = scan_source("r", "infra/gateway.tf", src)
        assert vs == []

    def test_tf_single_line_block_comment_skipped(self) -> None:
        src = f"/* bastion was {_MSK_BASTION_IP_LITERAL} */\n"
        vs = scan_source("r", "infra/gateway.tf", src)
        assert vs == []

    def test_tf_multiline_block_comment_interior_skipped(self) -> None:
        src = (
            "/* Example config.\n"
            f"   Historically the bastion was {_MSK_BASTION_IP_LITERAL}.\n"
            "*/\n"
        )
        vs = scan_source("r", "infra/gateway.tf", src)
        assert vs == []

    def test_tf_code_after_closed_block_comment_still_scanned(self) -> None:
        src = f'/* doc */\nbastion_ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "infra/gateway.tf", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_tf_slash_slash_does_not_suppress_other_file_types(self) -> None:
        # Non-regression: '//' is only a comment marker for .tf.
        src = f'// BASTION_IP="{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "gateway/config.env", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    # -- scan_tree: file-set widening, still narrow-match ---------------

    def test_scan_tree_finds_msk_violation_in_yaml(self, tmp_path: Path) -> None:
        (tmp_path / "docker").mkdir()
        f = tmp_path / "docker" / "docker-compose.gateway.yml"
        f.write_text(
            f'extra_hosts:\n  - "{_MSK_HOSTNAME_LITERAL}:{_MSK_BASTION_IP_LITERAL}"\n',
            encoding="utf-8",
        )
        vs = scan_tree("omnibase_infra", tmp_path)
        assert any(
            v.path.endswith("docker-compose.gateway.yml")
            and v.rule == RULE_MSK_DIRECT_BROKER
            for v in vs
        )

    def test_scan_tree_control_yaml_produces_no_violations(
        self, tmp_path: Path
    ) -> None:
        """Same tree shape, unrelated content — proves the widened file-glob
        does not resurrect rules 1-4's un-triaged match surface on YAML."""
        (tmp_path / "docker").mkdir()
        f = tmp_path / "docker" / "unrelated.yml"
        f.write_text(
            'services:\n  app:\n    environment:\n      API_URL: "https://api.svc.io"\n',
            encoding="utf-8",
        )
        vs = scan_tree("r", tmp_path)
        # A *_URL-shaped key in YAML would be a rule-2/3 match if those rules
        # applied to non-.py files; they must not, so this stays clean.
        assert vs == []

    def test_scan_tree_still_scans_py_rules_1_to_4(self, tmp_path: Path) -> None:
        """Non-regression: widening scan_tree's glob must not silently drop
        the existing four Python-source rules."""
        (tmp_path / "src").mkdir()
        f = tmp_path / "src" / "m.py"
        f.write_text('url = "https://api.example-service.com/v1"\n', encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        assert any(v.rule == RULE_PUBLIC_HTTPS for v in vs)


# ---------------------------------------------------------------------------
# Unit: _is_test_path anchoring (OMN-15692 verifier round #3 evasion fix)
# ---------------------------------------------------------------------------
#
# A bare "test" substring check waived real, non-test on-prem-facing files
# whose name coincidentally contains the four characters "test": each of the
# four cases below was PROVEN to evade the prior implementation.


@pytest.mark.unit
class TestIsTestPathAnchoring:
    def test_deploy_latest_yaml_not_exempted(self) -> None:
        # "la-TEST-.yaml" — bare substring match, not a test path.
        src = f'BOOTSTRAP = "{_MSK_HOSTNAME_LITERAL}:9098"\n'
        vs = scan_source("omnibase_infra", "deploy/latest.yaml", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_stability_test_lane_docker_compose_not_exempted(self) -> None:
        # "stability-test" is a real deployment LANE name (see CLAUDE.md
        # runtime lane map), not a test-code directory.
        src = f'BOOTSTRAP = "{_MSK_HOSTNAME_LITERAL}:9098"\n'
        vs = scan_source(
            "omnibase_infra", "docker/stability-test/docker-compose.yml", src
        )
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_stability_test_lane_env_not_exempted(self) -> None:
        src = f'ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("omnibase_infra", "docker/stability-test/gateway.env", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    def test_attestation_yaml_not_exempted(self) -> None:
        # "at-TEST-ation.yaml" — bare substring match, not a test path.
        src = f'ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("omnibase_infra", "attestation.yaml", src)
        assert len(vs) == 1
        assert vs[0].rule == RULE_MSK_DIRECT_BROKER

    # -- non-regression: real test paths must still be skipped -------------

    def test_real_tests_dir_still_skipped(self) -> None:
        src = f'ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "tests/fixtures/msk.yaml", src)
        assert vs == []

    def test_real_test_prefix_file_still_skipped(self) -> None:
        src = f'ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "src/pkg/test_gateway.py", src)
        assert vs == []

    def test_real_test_suffix_file_still_skipped(self) -> None:
        src = f'ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "src/pkg/gateway_test.py", src)
        assert vs == []

    def test_conftest_still_skipped(self) -> None:
        src = f'ip = "{_MSK_BASTION_IP_LITERAL}"\n'
        vs = scan_source("r", "tests/conftest.py", src)
        assert vs == []

    # -- direct unit coverage of the helper itself --------------------------

    def test_is_test_path_direct_true_cases(self) -> None:
        from omnibase_core.validation.validator_url_authority import _is_test_path

        assert _is_test_path("tests/test_foo.py")
        assert _is_test_path("tests/fixtures/x.yaml")
        assert _is_test_path("src/pkg/test_gateway.py")
        assert _is_test_path("src/pkg/gateway_test.py")
        assert _is_test_path("conftest.py")
        assert _is_test_path("tests/conftest.py")

    def test_is_test_path_direct_false_cases(self) -> None:
        from omnibase_core.validation.validator_url_authority import _is_test_path

        assert not _is_test_path("deploy/latest.yaml")
        assert not _is_test_path("docker/stability-test/docker-compose.yml")
        assert not _is_test_path("attestation.yaml")
        assert not _is_test_path("src/pkg/a.py")


# ---------------------------------------------------------------------------
# Unit: MSK file-selection gaps (OMN-15692 verifier round #3 evasion fix)
# ---------------------------------------------------------------------------
#
# Path.suffix returns "" for an extensionless dotfile (".env") and returns
# the PROFILE for the ".env.<profile>" family — neither is caught by a pure
# suffix check. "Dockerfile" has no extension at all. Each case below was
# PROVEN to evade the prior _MSK_SCAN_SUFFIXES-only selection.


@pytest.mark.unit
class TestMskFileSelectionGaps:
    def test_bare_dotenv_file_detected(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text(f'MSK_HOST="{_MSK_HOSTNAME_LITERAL}"\n', encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        assert any(v.rule == RULE_MSK_DIRECT_BROKER for v in vs)

    def test_env_profile_file_detected(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.production"
        f.write_text(f'MSK_HOST="{_MSK_HOSTNAME_LITERAL}"\n', encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        assert any(v.rule == RULE_MSK_DIRECT_BROKER for v in vs)

    def test_dockerfile_bare_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "Dockerfile"
        f.write_text(f"ENV MSK_HOST={_MSK_HOSTNAME_LITERAL}\n", encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        assert any(v.rule == RULE_MSK_DIRECT_BROKER for v in vs)

    def test_dockerfile_variant_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "Dockerfile.gateway"
        f.write_text(f"ENV MSK_HOST={_MSK_HOSTNAME_LITERAL}\n", encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        assert any(v.rule == RULE_MSK_DIRECT_BROKER for v in vs)

    def test_json_file_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "config.json"
        f.write_text(
            f'{{"bootstrap": "{_MSK_HOSTNAME_LITERAL}:9098"}}\n', encoding="utf-8"
        )
        vs = scan_tree("r", tmp_path)
        assert any(v.rule == RULE_MSK_DIRECT_BROKER for v in vs)

    def test_terraform_file_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "main.tf"
        f.write_text(f'bootstrap = "{_MSK_HOSTNAME_LITERAL}:9098"\n', encoding="utf-8")
        vs = scan_tree("r", tmp_path)
        assert any(v.rule == RULE_MSK_DIRECT_BROKER for v in vs)

    def test_unrelated_extension_not_scannable(self) -> None:
        from omnibase_core.validation.validator_url_authority import (
            _is_msk_scannable,
        )

        assert not _is_msk_scannable(Path("readme.md"))
        assert not _is_msk_scannable(Path("notes.txt"))

    def test_is_msk_scannable_direct(self) -> None:
        from omnibase_core.validation.validator_url_authority import (
            _is_msk_scannable,
        )

        assert _is_msk_scannable(Path(".env"))
        assert _is_msk_scannable(Path(".env.production"))
        assert _is_msk_scannable(Path(".env.local"))
        assert _is_msk_scannable(Path("Dockerfile"))
        assert _is_msk_scannable(Path("Dockerfile.gateway"))
        assert _is_msk_scannable(Path("config.json"))
        assert _is_msk_scannable(Path("main.tf"))


# ---------------------------------------------------------------------------
# Unit: baseline must never grandfather the rule it exists to catch
# (OMN-15692 verifier round #3 — baseline self-defeat)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBaselineDoesNotGrandfatherMskRule:
    def test_committed_baseline_has_no_msk_entries(self) -> None:
        from omnibase_core.validation.validator_url_authority import (
            _DEFAULT_BASELINE,
        )

        data = json.loads(_DEFAULT_BASELINE.read_text(encoding="utf-8"))
        msk_entries = [
            e for e in data["violations"] if e.get("rule") == RULE_MSK_DIRECT_BROKER
        ]
        assert msk_entries == [], (
            "The committed baseline must not grandfather "
            "msk-direct-broker-endpoint violations — doing so self-defeats "
            f"the gate on exactly the cases it exists to catch: {msk_entries}"
        )


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

    def test_msk_fixture_red_then_green_cli(self, tmp_path: Path) -> None:
        """CLI-level reproduction of the exact adversarial defect proof: a
        fixture containing both the bastion IP and an MSK hostname:9098
        literal must fail the gate (RED); the identical fixture with those
        two lines removed must pass (GREEN). Uses the real --all full-repo
        path, matching how the CI job invokes this gate."""
        from omnibase_core.validation.validator_url_authority import main

        (tmp_path / "docker").mkdir()
        fixture = tmp_path / "docker" / "docker-compose.gateway.yml"
        fixture.write_text(
            "extra_hosts:\n"
            f'  - "{_MSK_HOSTNAME_LITERAL}:{_MSK_BASTION_IP_LITERAL}"\n'
            f'  - "b-2.omninodedevmsk.7ozyd3.c14.kafka.us-east-1.amazonaws.com:9098"\n',
            encoding="utf-8",
        )
        baseline = tmp_path / "baseline.json"
        baseline.write_text(
            json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
            encoding="utf-8",
        )
        rc_red = main(
            [
                "--all",
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(baseline),
            ]
        )
        assert rc_red == 1, "RED expected: fixture carries the exact ruling-39 literal"

        fixture.write_text("services:\n  app:\n    image: nginx\n", encoding="utf-8")
        rc_green = main(
            [
                "--all",
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(baseline),
            ]
        )
        assert rc_green == 0, "GREEN expected: fixture no longer carries the literal"

    def test_control_fixture_unaffected_cli(self, tmp_path: Path) -> None:
        """Negative control: an unrelated public-https literal in a .py file
        (rules 1-4's existing territory) is untouched by this change and the
        MSK rule does not fire on ordinary infra config."""
        from omnibase_core.validation.validator_url_authority import main

        (tmp_path / "docker").mkdir()
        (tmp_path / "docker" / "unrelated.yml").write_text(
            'services:\n  app:\n    environment:\n      LOG_LEVEL: "info"\n',
            encoding="utf-8",
        )
        baseline = tmp_path / "baseline.json"
        baseline.write_text(
            json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
            encoding="utf-8",
        )
        rc = main(
            [
                "--all",
                "--repo",
                "r",
                "--repo-root",
                str(tmp_path),
                "--baseline",
                str(baseline),
            ]
        )
        assert rc == 0

    def test_dotenv_fixture_detected_via_staged_file_cli(self, tmp_path: Path) -> None:
        """CLI-layer (pre-commit staged-file mode) proof, not just
        scan_source: a real ``.env`` file passed as a positional arg — the
        exact invocation shape pre-commit's ``pass_filenames: true`` uses —
        must be scanned. ``Path(".env").suffix`` is EMPTY (OMN-15692
        verifier round #3), so the CLI's own file-selection filter is the
        thing under test here, independent of scan_source's correctness."""
        from omnibase_core.validation.validator_url_authority import main

        f = tmp_path / ".env"
        f.write_text(f'MSK_HOST="{_MSK_HOSTNAME_LITERAL}"\n', encoding="utf-8")
        baseline = tmp_path / "baseline.json"
        baseline.write_text(
            json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
            encoding="utf-8",
        )
        rc_red = main(
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
        assert rc_red == 1, "RED expected: staged .env fixture carries the MSK literal"

        f.write_text('LOG_LEVEL="info"\n', encoding="utf-8")
        rc_green = main(
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
        assert rc_green == 0, "GREEN expected: no MSK literal in the fixture"

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
