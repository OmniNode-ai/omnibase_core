# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for OmniGate configuration models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.gate import (
    EnumGateEnforcementAction,
    EnumGateResponse,
    EnumOmniGateCheckType,
    ModelOmniGateCheck,
    ModelOmniGateConfig,
    ModelOmniGateGateDecision,
    ModelOmniGateGatePolicy,
    ModelOmniGateIdentityPolicy,
    ModelOmniGateReceiptPolicy,
    ModelOmniGateValidatorRef,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelOmniGateConfig:
    def test_minimal_config_defaults(self) -> None:
        config = ModelOmniGateConfig(
            version=ModelSemVer.parse("1.0.0"),
            project_name="my-project",
            project_url="https://github.com/org/repo",
            checks=(ModelOmniGateCheck(name="lint", run="npm run lint"),),
        )

        assert config.project_name == "my-project"
        assert len(config.checks) == 1
        assert config.checks[0].check_type == EnumOmniGateCheckType.SHELL
        assert config.checks[0].timeout_seconds == 300
        assert config.gate.on_missing_receipt == EnumGateResponse.AUTO_CLOSE
        assert config.receipt.allow_unsigned is False
        assert config.receipt.advisory_blocks is False
        assert config.receipt.max_receipt_bytes == 65536

    def test_frozen(self) -> None:
        config = ModelOmniGateConfig(
            version=ModelSemVer.parse("1.0.0"),
            project_name="test",
            project_url="https://github.com/org/repo",
            checks=(),
        )

        with pytest.raises(ValidationError):
            config.project_name = "changed"  # type: ignore[misc]

    def test_full_config_with_validators_and_gate_policy(self) -> None:
        config = ModelOmniGateConfig(
            version=ModelSemVer.parse("1.0.0"),
            project_name="my-project",
            project_url="https://github.com/org/repo",
            max_checks=10,
            denied_command_patterns=("rm -rf", "printenv"),
            checks=(
                ModelOmniGateCheck(
                    name="lint",
                    run="npm run lint",
                    timeout_seconds=120,
                    allowed_env=("NODE_ENV",),
                ),
                ModelOmniGateCheck(
                    name="test",
                    run="npm test",
                    advisory_is_blocking=True,
                ),
            ),
            validators=(
                ModelOmniGateValidatorRef(id="local-paths"),
                ModelOmniGateValidatorRef(
                    id="any-type",
                    config={"max_violations": 10},
                ),
            ),
            gate=ModelOmniGateGatePolicy(
                scope="forks-only",
                on_missing_receipt=EnumGateResponse.LABEL,
                grace_period_minutes=10,
                exempt_users=("dependabot[bot]", "renovate[bot]"),
            ),
            receipt=ModelOmniGateReceiptPolicy(
                max_age_minutes=120,
                require_diff_binding=True,
                signing="sigstore",
                advisory_blocks=True,
                identity=ModelOmniGateIdentityPolicy(
                    expected_issuer="https://token.actions.githubusercontent.com",
                    allowed_identities=(
                        "https://github.com/org/repo/.github/workflows/omnigate.yml@refs/heads/main",
                    ),
                ),
            ),
        )

        assert len(config.checks) == 2
        assert len(config.validators) == 2
        assert config.gate.scope == "forks-only"
        assert config.receipt.identity is not None
        assert config.receipt.advisory_blocks is True

    def test_check_count_cannot_exceed_policy(self) -> None:
        checks = tuple(
            ModelOmniGateCheck(name=f"check-{index}", run="echo ok")
            for index in range(3)
        )

        with pytest.raises(ValidationError):
            ModelOmniGateConfig(
                version=ModelSemVer.parse("1.0.0"),
                project_name="test",
                project_url="https://github.com/org/repo",
                max_checks=2,
                checks=checks,
            )

    def test_gate_decision_is_typed(self) -> None:
        decision = ModelOmniGateGateDecision(
            action=EnumGateEnforcementAction.LABEL,
            reason="Receipt missing",
            label="omnigate-missing",
        )

        assert decision.action == EnumGateEnforcementAction.LABEL
