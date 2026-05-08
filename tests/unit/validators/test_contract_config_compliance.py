# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for contract_config_compliance validator (OMN-10688)."""

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_contract_config_compliance_finding import (
    ModelContractConfigComplianceFinding,
)
from omnibase_core.validators.contract_config_compliance import (
    INFRA_ALLOWLIST,
    generate_allowlist,
    validate_file,
    validate_paths,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _handler(tmp_path: Path, name: str, content: str) -> Path:
    return _write(tmp_path, f"nodes/my_node/handlers/{name}", content)


def _script(tmp_path: Path, name: str, content: str) -> Path:
    return _write(tmp_path, f"scripts/{name}", content)


# ---------------------------------------------------------------------------
# Rule: bare_env_read
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBareEnvRead:
    def test_getenv_not_in_allowlist_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.getenv('MY_SERVICE_URL')\n",
        )
        findings = validate_file(p, frozenset({"bare_env_read"}))
        assert len(findings) == 1
        assert findings[0].rule == "bare_env_read"
        assert "MY_SERVICE_URL" in findings[0].message

    def test_environ_get_not_in_allowlist_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.environ.get('MY_DB_HOST')\n",
        )
        findings = validate_file(p, frozenset({"bare_env_read"}))
        assert len(findings) == 1
        assert "MY_DB_HOST" in findings[0].message

    def test_environ_subscript_not_in_allowlist_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.environ['MY_SECRET']\n",
        )
        findings = validate_file(p, frozenset({"bare_env_read"}))
        assert len(findings) == 1
        assert "MY_SECRET" in findings[0].message

    def test_allowlist_key_not_flagged(self, tmp_path: Path) -> None:
        for key in list(INFRA_ALLOWLIST)[:3]:
            p = _handler(
                tmp_path,
                f"handler_{key.lower()}.py",
                f"import os\nval = os.getenv('{key}')\n",
            )
            findings = validate_file(p, frozenset({"bare_env_read"}))
            assert findings == [], f"{key} should be in allowlist"

    def test_non_handler_file_not_checked(self, tmp_path: Path) -> None:
        # A file not inside handlers/ should NOT trigger bare_env_read
        p = _write(
            tmp_path, "services/service_foo.py", "import os\nx = os.getenv('MY_KEY')\n"
        )
        findings = validate_file(p, frozenset({"bare_env_read"}))
        assert findings == []

    def test_suppression_marker_silences(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.getenv('MY_KEY')  # contract-config-ok: legacy compat\n",
        )
        findings = validate_file(p, frozenset({"bare_env_read"}))
        assert findings == []

    def test_unknown_var_name_no_string_arg_not_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nkey = 'MY_KEY'\nval = os.getenv(key)\n",
        )
        findings = validate_file(p, frozenset({"bare_env_read"}))
        # Non-literal key can't be statically determined — not flagged
        assert findings == []


# ---------------------------------------------------------------------------
# Rule: bus_bypass_import
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBusBypassImport:
    def test_script_importing_handler_flagged(self, tmp_path: Path) -> None:
        p = _script(
            tmp_path,
            "run_something.py",
            "from omnibase_infra.nodes.node_foo.handlers.handler_bar import HandlerBar\n",
        )
        findings = validate_file(p, frozenset({"bus_bypass_import"}))
        assert len(findings) == 1
        assert findings[0].rule == "bus_bypass_import"
        assert "handlers" in findings[0].message

    def test_script_not_importing_handler_clean(self, tmp_path: Path) -> None:
        p = _script(
            tmp_path,
            "run_something.py",
            "from omnibase_infra.nodes.node_foo import NodeFoo\n",
        )
        findings = validate_file(p, frozenset({"bus_bypass_import"}))
        assert findings == []

    def test_handler_importing_sibling_handler_clean(self, tmp_path: Path) -> None:
        # handlers/ importing handlers/ — rule only fires on script files
        p = _handler(
            tmp_path,
            "handler_a.py",
            "from omnibase_infra.nodes.node_foo.handlers.handler_b import HandlerB\n",
        )
        findings = validate_file(p, frozenset({"bus_bypass_import"}))
        assert findings == []

    def test_suppression_marker_silences(self, tmp_path: Path) -> None:
        p = _script(
            tmp_path,
            "run_something.py",
            "from omnibase_infra.nodes.node_foo.handlers.handler_bar import HandlerBar  # contract-config-ok: test helper\n",
        )
        findings = validate_file(p, frozenset({"bus_bypass_import"}))
        assert findings == []


# ---------------------------------------------------------------------------
# Rule: missing_contract_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMissingContractConfig:
    def test_env_read_with_no_contract_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.getenv('MY_SERVICE_URL')\n",
        )
        findings = validate_file(p, frozenset({"missing_contract_config"}))
        assert len(findings) == 1
        assert findings[0].rule == "missing_contract_config"
        assert "MY_SERVICE_URL" in findings[0].message

    def test_env_read_declared_in_contract_clean(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "nodes/my_node/contract.yaml",
            "dependencies:\n  - name: svc\n    type: environment\n    env_var: MY_SERVICE_URL\n    required: true\n",
        )
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.getenv('MY_SERVICE_URL')\n",
        )
        findings = validate_file(p, frozenset({"missing_contract_config"}))
        assert findings == []

    def test_allowlist_key_not_checked(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.getenv('KAFKA_BOOTSTRAP_SERVERS')\n",
        )
        findings = validate_file(p, frozenset({"missing_contract_config"}))
        assert findings == []

    def test_suppression_marker_silences(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.getenv('MY_KEY')  # contract-config-ok: bootstrapped externally\n",
        )
        findings = validate_file(p, frozenset({"missing_contract_config"}))
        assert findings == []

    def test_contract_with_config_section_key(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "nodes/my_node/contract.yaml",
            "config:\n  poll_interval: 60\n  token_env_var: MY_SERVICE_TOKEN\n",
        )
        p = _handler(
            tmp_path,
            "handler_foo.py",
            "import os\nval = os.getenv('MY_SERVICE_TOKEN')\n",
        )
        findings = validate_file(p, frozenset({"missing_contract_config"}))
        assert findings == []


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelContractConfigComplianceFinding:
    def test_format_output(self, tmp_path: Path) -> None:
        f = ModelContractConfigComplianceFinding(
            path=Path("src/nodes/n/handlers/h.py"),
            line=42,
            column=4,
            rule="bare_env_read",
            message="bare env read of 'X'",
        )
        formatted = f.format()
        assert "src/nodes/n/handlers/h.py:42:5" in formatted
        assert "bare_env_read" in formatted
        assert "bare env read of 'X'" in formatted

    def test_finding_is_frozen(self) -> None:
        f = ModelContractConfigComplianceFinding(
            path=Path("a.py"),
            line=1,
            column=0,
            rule="bare_env_read",
            message="msg",
        )
        with pytest.raises(Exception):
            # NOTE(OMN-10688): frozen dataclass assignment raises FrozenInstanceError at runtime;
            # mypy[misc] suppressed because the static type-checker correctly rejects this line.
            f.rule = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# validate_paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatePaths:
    def test_directory_scan_finds_violations(self, tmp_path: Path) -> None:
        _handler(tmp_path, "handler_a.py", "import os\nval = os.getenv('FOO_URL')\n")
        _handler(tmp_path, "handler_b.py", "import os\nval = os.getenv('BAR_URL')\n")
        findings = validate_paths([tmp_path])
        assert len(findings) >= 2

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        findings = validate_paths([tmp_path])
        assert findings == []

    def test_non_python_files_ignored(self, tmp_path: Path) -> None:
        p = tmp_path / "nodes" / "my_node" / "handlers"
        p.mkdir(parents=True)
        (p / "readme.md").write_text("some text", encoding="utf-8")
        findings = validate_paths([tmp_path])
        assert findings == []

    def test_syntax_error_file_skipped(self, tmp_path: Path) -> None:
        p = _handler(tmp_path, "broken.py", "def bad(\n")
        findings = validate_file(p)
        assert findings == []

    def test_excluded_pycache_ignored(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            "nodes/my_node/handlers/__pycache__/handler_foo.cpython-312.pyc",
            "import os\nval = os.getenv('SECRET')\n",
        )
        findings = validate_file(p)
        assert findings == []


# ---------------------------------------------------------------------------
# generate_allowlist
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateAllowlist:
    def test_empty_findings_produces_empty_allowlist(self) -> None:
        output = generate_allowlist([])
        assert output.strip() == "allowlist: {}"

    def test_findings_grouped_by_rule(self, tmp_path: Path) -> None:
        findings = [
            ModelContractConfigComplianceFinding(
                path=Path("a/handlers/h.py"),
                line=1,
                column=0,
                rule="bare_env_read",
                message="bare env read of 'X'",
            ),
            ModelContractConfigComplianceFinding(
                path=Path("scripts/s.py"),
                line=5,
                column=0,
                rule="bus_bypass_import",
                message="direct handler import",
            ),
        ]
        output = generate_allowlist(findings)
        assert "bare_env_read" in output
        assert "bus_bypass_import" in output
        assert "a/handlers/h.py" in output
