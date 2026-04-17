# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidatorBannedComposeVars [OMN-9062].

Tests kernel-sourced banned env var detection against compose / k8s manifests.

Trigger incident: OMN-8840 — ``ONEX_INPUT_TOPIC`` persisted in compose after
OMN-8784 removed it from code. This validator flags any compose env var whose
name is in the kernel's ``_DEPRECATED_TOPIC_ENV_VARS`` constant (single source
of truth — parsed via static ``ast`` walk to respect compat/core/spi/infra
layering).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums.enum_compose_drift_kind import EnumComposeDriftKind
from omnibase_core.validation.validator_banned_compose_vars import (
    ValidatorBannedComposeVars,
    extract_banned_env_vars_from_kernel,
    main,
)


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Produce an empty scratch repo directory with a synthetic kernel."""
    (tmp_path / "docker").mkdir()
    return tmp_path


def _write_kernel_with_banned_set(root: Path, banned: list[str]) -> Path:
    """Emit a fake ``service_kernel.py`` carrying ``_DEPRECATED_TOPIC_ENV_VARS``."""
    kernel_path = root / "service_kernel.py"
    literals = ", ".join(f'"{name}"' for name in banned)
    kernel_path.write_text(
        f"# Synthetic kernel for tests.\n"
        f"_DEPRECATED_TOPIC_ENV_VARS: tuple[str, ...] = ({literals},)\n",
        encoding="utf-8",
    )
    return kernel_path


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


class TestExtractBannedEnvVarsFromKernel:
    def test_extracts_tuple_literal(self, tmp_path: Path) -> None:
        kernel = _write_kernel_with_banned_set(
            tmp_path, ["ONEX_INPUT_TOPIC", "ONEX_OUTPUT_TOPIC"]
        )
        assert extract_banned_env_vars_from_kernel(kernel) == frozenset(
            {"ONEX_INPUT_TOPIC", "ONEX_OUTPUT_TOPIC"}
        )

    def test_extracts_list_literal(self, tmp_path: Path) -> None:
        kernel = tmp_path / "service_kernel.py"
        kernel.write_text(
            '_DEPRECATED_TOPIC_ENV_VARS = ["VAR_ONE", "VAR_TWO"]\n',
            encoding="utf-8",
        )
        assert extract_banned_env_vars_from_kernel(kernel) == frozenset(
            {"VAR_ONE", "VAR_TWO"}
        )

    def test_missing_file_returns_empty_set(self, tmp_path: Path) -> None:
        assert extract_banned_env_vars_from_kernel(tmp_path / "nope.py") == frozenset()

    def test_missing_constant_returns_empty_set(self, tmp_path: Path) -> None:
        kernel = tmp_path / "service_kernel.py"
        kernel.write_text("OTHER_CONSTANT = ('X',)\n", encoding="utf-8")
        assert extract_banned_env_vars_from_kernel(kernel) == frozenset()

    def test_syntax_error_returns_empty_set(self, tmp_path: Path) -> None:
        kernel = tmp_path / "service_kernel.py"
        kernel.write_text("def broken(\n", encoding="utf-8")
        assert extract_banned_env_vars_from_kernel(kernel) == frozenset()

    def test_ignores_non_literal_elements(self, tmp_path: Path) -> None:
        kernel = tmp_path / "service_kernel.py"
        kernel.write_text(
            'OTHER = "X"\n_DEPRECATED_TOPIC_ENV_VARS = ("STRING_LITERAL", OTHER, 42)\n',
            encoding="utf-8",
        )
        assert extract_banned_env_vars_from_kernel(kernel) == frozenset(
            {"STRING_LITERAL"}
        )


class TestValidatorBannedComposeVars:
    def test_no_kernel_source_yields_empty_banned_set(self, tmp_repo: Path) -> None:
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={"ONEX_INPUT_TOPIC": "requests"},
        )
        validator = ValidatorBannedComposeVars()
        assert validator.banned_env_vars() == frozenset()
        assert validator.check_paths([tmp_repo]) == []

    def test_banned_var_flagged_regardless_of_value(self, tmp_repo: Path) -> None:
        kernel = _write_kernel_with_banned_set(
            tmp_repo, ["ONEX_INPUT_TOPIC", "ONEX_OUTPUT_TOPIC"]
        )
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={
                # Both are banned — regardless of their values.
                "ONEX_INPUT_TOPIC": "requests",
                "ONEX_OUTPUT_TOPIC": "responses",
                # Not banned — left alone.
                "OMNI_LOG_LEVEL": "INFO",
            },
        )

        validator = ValidatorBannedComposeVars(kernel_source_path=kernel)
        violations = validator.check_paths([tmp_repo])

        assert sorted(v.var_name for v in violations) == [
            "ONEX_INPUT_TOPIC",
            "ONEX_OUTPUT_TOPIC",
        ]
        for v in violations:
            assert v.kind is EnumComposeDriftKind.BANNED_VAR
            assert v.compose_path is not None
            assert v.compose_path.name == "docker-compose.yml"
            assert v.contract_path is None
            assert "_DEPRECATED_TOPIC_ENV_VARS" in v.message

    def test_allowed_vars_ignored(self, tmp_repo: Path) -> None:
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={
                "OMNI_LOG_LEVEL": "INFO",
                "DATABASE_URL": "postgresql://x",
                "ONEX_GROUP_ID": "some-group",
            },
        )

        validator = ValidatorBannedComposeVars(kernel_source_path=kernel)
        assert validator.check_paths([tmp_repo]) == []

    def test_k8s_manifest_env_list_form_scanned(self, tmp_repo: Path) -> None:
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
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
            "              value: 'anything'\n"
            "            - name: OMNI_LOG_LEVEL\n"
            "              value: INFO\n",
            encoding="utf-8",
        )

        validator = ValidatorBannedComposeVars(kernel_source_path=kernel)
        violations = validator.check_paths([tmp_repo])

        assert len(violations) == 1
        assert violations[0].var_name == "ONEX_INPUT_TOPIC"
        assert violations[0].compose_path is not None
        assert violations[0].compose_path.name == "deployment.yaml"

    def test_compose_environment_list_form_scanned(self, tmp_repo: Path) -> None:
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
        compose_path = tmp_repo / "docker" / "docker-compose.yml"
        compose_path.write_text(
            "services:\n"
            "  example:\n"
            "    image: example:latest\n"
            "    environment:\n"
            "      - ONEX_INPUT_TOPIC=requests\n"
            "      - OMNI_LOG_LEVEL=INFO\n",
            encoding="utf-8",
        )

        validator = ValidatorBannedComposeVars(kernel_source_path=kernel)
        violations = validator.check_paths([tmp_repo])
        assert len(violations) == 1
        assert violations[0].var_name == "ONEX_INPUT_TOPIC"

    def test_compose_pass_through_list_form_scanned(self, tmp_repo: Path) -> None:
        """Compose `- VAR_NAME` (no `=`) passes value from host env; still banned."""
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
        compose_path = tmp_repo / "docker" / "docker-compose.yml"
        compose_path.write_text(
            "services:\n"
            "  example:\n"
            "    image: example:latest\n"
            "    environment:\n"
            "      - ONEX_INPUT_TOPIC\n"
            "      - OMNI_LOG_LEVEL\n",
            encoding="utf-8",
        )

        validator = ValidatorBannedComposeVars(kernel_source_path=kernel)
        violations = validator.check_paths([tmp_repo])
        assert [v.var_name for v in violations] == ["ONEX_INPUT_TOPIC"]

    def test_k8s_value_from_form_scanned(self, tmp_repo: Path) -> None:
        """k8s `valueFrom` (no `value`) must not bypass the ban."""
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
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
            "              valueFrom:\n"
            "                configMapKeyRef:\n"
            "                  name: some-cm\n"
            "                  key: topic\n"
            "            - name: OMNI_LOG_LEVEL\n"
            "              value: INFO\n",
            encoding="utf-8",
        )

        validator = ValidatorBannedComposeVars(kernel_source_path=kernel)
        violations = validator.check_paths([tmp_repo])
        assert [v.var_name for v in violations] == ["ONEX_INPUT_TOPIC"]

    def test_multi_doc_k8s_manifest_scanned(self, tmp_repo: Path) -> None:
        """k8s manifests often bundle multiple documents with `---` separators."""
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
        k8s_path = tmp_repo / "k8s" / "bundle.yaml"
        k8s_path.parent.mkdir(parents=True, exist_ok=True)
        k8s_path.write_text(
            "apiVersion: v1\n"
            "kind: ConfigMap\n"
            "metadata:\n"
            "  name: cfg\n"
            "---\n"
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "spec:\n"
            "  template:\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: svc\n"
            "          env:\n"
            "            - name: ONEX_INPUT_TOPIC\n"
            "              value: requests\n"
            "---\n"
            "apiVersion: v1\n"
            "kind: Service\n"
            "metadata:\n"
            "  name: svc\n",
            encoding="utf-8",
        )

        validator = ValidatorBannedComposeVars(kernel_source_path=kernel)
        violations = validator.check_paths([tmp_repo])
        assert len(violations) == 1
        assert violations[0].var_name == "ONEX_INPUT_TOPIC"

    def test_compose_name_only_dict_scanned(self, tmp_repo: Path) -> None:
        """Compose ``- {name: KEY}`` (dict, no ``value``) is pass-through; still banned."""
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
        compose_path = tmp_repo / "docker" / "docker-compose.yml"
        compose_path.write_text(
            "services:\n"
            "  example:\n"
            "    image: example:latest\n"
            "    environment:\n"
            "      - name: ONEX_INPUT_TOPIC\n",
            encoding="utf-8",
        )

        validator = ValidatorBannedComposeVars(kernel_source_path=kernel)
        violations = validator.check_paths([tmp_repo])
        assert [v.var_name for v in violations] == ["ONEX_INPUT_TOPIC"]

    def test_extra_banned_merges_with_kernel_set(self, tmp_repo: Path) -> None:
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={
                "ONEX_INPUT_TOPIC": "x",  # from kernel
                "EXTRA_FORBIDDEN": "y",  # from --extra-banned
                "OKAY_VAR": "z",
            },
        )

        validator = ValidatorBannedComposeVars(
            kernel_source_path=kernel,
            extra_banned=frozenset({"EXTRA_FORBIDDEN"}),
        )
        violations = validator.check_paths([tmp_repo])
        assert sorted(v.var_name for v in violations) == [
            "EXTRA_FORBIDDEN",
            "ONEX_INPUT_TOPIC",
        ]

    def test_cli_exits_2_on_violation(
        self, tmp_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={"ONEX_INPUT_TOPIC": "requests"},
        )

        exit_code = main(
            ["--kernel-source", str(kernel), str(tmp_repo)],
        )
        out = capsys.readouterr().out
        assert exit_code == 2
        assert "BANNED_VAR" in out
        assert "ONEX_INPUT_TOPIC" in out

    def test_cli_exits_0_on_clean(
        self, tmp_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        kernel = _write_kernel_with_banned_set(tmp_repo, ["ONEX_INPUT_TOPIC"])
        _write_compose(
            tmp_repo,
            "docker/docker-compose.yml",
            env={"OMNI_LOG_LEVEL": "INFO"},
        )

        exit_code = main(
            ["--kernel-source", str(kernel), str(tmp_repo)],
        )
        assert exit_code == 0

    def test_cli_exits_2_on_empty_banned_set(
        self, tmp_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Empty banned set is a misconfiguration — fail loudly, not silently pass."""
        empty_kernel = tmp_repo / "empty_kernel.py"
        empty_kernel.write_text("# no constant here\n", encoding="utf-8")

        exit_code = main(
            ["--kernel-source", str(empty_kernel), str(tmp_repo)],
        )
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "banned set is empty" in err
