# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidatorBannedComposeVars [OMN-9062].

Tests bidirectional compose↔contract topic drift detection:

- Synthetic contract + compose that agree → 0 violations
- Compose references banned topic (not in any contract) → BANNED_VAR
- Contract declares topic missing from compose → MISSING_VAR
- Multi-repo scan (contracts in one dir, compose in another)

Trigger incident: OMN-8840 — ``ONEX_INPUT_TOPIC`` persisted in compose
after OMN-8784 removed it from code. A bidirectional validator would
have caught the drift at review time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums.enum_compose_drift_kind import EnumComposeDriftKind
from omnibase_core.validation.validator_banned_compose_vars import (
    ValidatorBannedComposeVars,
    main,
)


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Produce an empty scratch repo directory."""
    (tmp_path / "contracts").mkdir()
    (tmp_path / "docker").mkdir()
    return tmp_path


def _write_contract(
    root: Path, rel: str, subscribe: list[str], publish: list[str]
) -> Path:
    contract_path = root / rel
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "name: node_example",
        "event_bus:",
        "  subscribe_topics:",
    ]
    lines.extend(f"    - {topic!r}" for topic in subscribe)
    lines.append("  publish_topics:")
    lines.extend(f"    - {topic!r}" for topic in publish)
    contract_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return contract_path


def _write_compose(root: Path, rel: str, env: dict[str, str]) -> Path:
    compose_path = root / rel
    compose_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "services:",
        "  example:",
        "    image: example:latest",
        "    environment:",
    ]
    for key, val in env.items():
        lines.append(f"      {key}: {val!r}")
    compose_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return compose_path


class TestValidatorBannedComposeVars:
    def test_agreement_yields_zero_violations(self, tmp_repo: Path) -> None:
        _write_contract(
            tmp_repo,
            "contracts/node_a/contract.yaml",
            subscribe=["onex.cmd.service-a.do-thing.v1"],
            publish=["onex.evt.service-a.thing-done.v1"],
        )
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={
                "ONEX_INPUT_TOPIC": "onex.cmd.service-a.do-thing.v1",
                "ONEX_OUTPUT_TOPIC": "onex.evt.service-a.thing-done.v1",
            },
        )

        validator = ValidatorBannedComposeVars()
        violations = validator.check_paths([tmp_repo])
        assert violations == []

    def test_banned_var_detected_when_compose_references_undeclared_topic(
        self, tmp_repo: Path
    ) -> None:
        _write_contract(
            tmp_repo,
            "contracts/node_a/contract.yaml",
            subscribe=["onex.cmd.service-a.do-thing.v1"],
            publish=[],
        )
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={
                "ONEX_INPUT_TOPIC": "onex.cmd.service-a.do-thing.v1",
                # Stale — no contract declares this topic (OMN-8840 pattern)
                "ONEX_OUTPUT_TOPIC": "onex.evt.service-a.stale-thing.v1",
            },
        )

        validator = ValidatorBannedComposeVars()
        violations = validator.check_paths([tmp_repo])

        banned = [v for v in violations if v.kind is EnumComposeDriftKind.BANNED_VAR]
        assert len(banned) == 1
        assert banned[0].var_name == "ONEX_OUTPUT_TOPIC"
        assert banned[0].compose_path is not None
        assert banned[0].compose_path.name == "docker-compose.yml"
        assert banned[0].contract_path is None
        assert "onex.evt.service-a.stale-thing.v1" in banned[0].message

    def test_missing_var_detected_when_contract_topic_not_exposed(
        self, tmp_repo: Path
    ) -> None:
        _write_contract(
            tmp_repo,
            "contracts/node_a/contract.yaml",
            subscribe=["onex.cmd.service-a.do-thing.v1"],
            publish=["onex.evt.service-a.thing-done.v1"],
        )
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={
                # Only subscribe topic exposed — publish is orphaned
                "ONEX_INPUT_TOPIC": "onex.cmd.service-a.do-thing.v1",
            },
        )

        validator = ValidatorBannedComposeVars()
        violations = validator.check_paths([tmp_repo])

        missing = [v for v in violations if v.kind is EnumComposeDriftKind.MISSING_VAR]
        assert len(missing) == 1
        assert missing[0].contract_path is not None
        assert missing[0].compose_path is None
        assert "onex.evt.service-a.thing-done.v1" in missing[0].message

    def test_multi_repo_scan_separates_contract_and_compose_roots(
        self, tmp_path: Path
    ) -> None:
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        repo_a.mkdir()
        repo_b.mkdir()

        _write_contract(
            repo_a,
            "src/node_a/contract.yaml",
            subscribe=["onex.cmd.service-a.do-thing.v1"],
            publish=[],
        )
        _write_compose(
            repo_b,
            "deploy/docker-compose.yml",
            env={"ONEX_INPUT_TOPIC": "onex.cmd.service-a.do-thing.v1"},
        )

        validator = ValidatorBannedComposeVars()
        violations = validator.check_paths([repo_a, repo_b])
        assert violations == []

    def test_k8s_manifest_environment_block_scanned(self, tmp_repo: Path) -> None:
        _write_contract(
            tmp_repo,
            "contracts/node_a/contract.yaml",
            subscribe=["onex.cmd.service-a.do-thing.v1"],
            publish=[],
        )
        k8s_path = tmp_repo / "k8s" / "deployment.yaml"
        k8s_path.parent.mkdir(parents=True, exist_ok=True)
        k8s_path.write_text(
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "spec:\n"
            "  template:\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: svc\n"
            "          env:\n"
            "            - name: ONEX_INPUT_TOPIC\n"
            "              value: 'onex.cmd.service-a.do-thing.v1'\n"
            "            - name: ONEX_STALE_TOPIC\n"
            "              value: 'onex.evt.service-a.undeclared.v1'\n",
            encoding="utf-8",
        )

        validator = ValidatorBannedComposeVars()
        violations = validator.check_paths([tmp_repo])

        banned = [v for v in violations if v.kind is EnumComposeDriftKind.BANNED_VAR]
        assert len(banned) == 1
        assert banned[0].var_name == "ONEX_STALE_TOPIC"
        assert banned[0].compose_path is not None
        assert banned[0].compose_path.name == "deployment.yaml"

    def test_cli_exits_2_on_drift(
        self, tmp_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_contract(
            tmp_repo,
            "contracts/node_a/contract.yaml",
            subscribe=["onex.cmd.service-a.do-thing.v1"],
            publish=[],
        )
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={"ONEX_STALE": "onex.evt.undeclared.service.v1"},
        )

        exit_code = main([str(tmp_repo)])
        captured = capsys.readouterr()

        assert exit_code == 2
        assert "BANNED_VAR" in captured.out
        assert "onex.evt.undeclared.service.v1" in captured.out

    def test_cli_exits_0_on_clean(
        self, tmp_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_contract(
            tmp_repo,
            "contracts/node_a/contract.yaml",
            subscribe=["onex.cmd.service-a.do-thing.v1"],
            publish=[],
        )
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={"ONEX_INPUT_TOPIC": "onex.cmd.service-a.do-thing.v1"},
        )

        exit_code = main([str(tmp_repo)])
        assert exit_code == 0
