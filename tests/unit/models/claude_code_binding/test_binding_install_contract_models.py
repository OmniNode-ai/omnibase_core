# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract tests for the Claude Code binding install model family (OMN-21093).

The family moved from omnimarket so omnibase_infra's skill mapping can name
the result model without a cross-repo node reach-in (the layering rule the
node-boundary gate enforces: shared wire models live in core). Field names,
types, constraints and defaults are pinned here verbatim against the shapes
omnimarket shipped (OMN-18531), so the move is a relocation, not a redesign.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.claude_code_binding import (
    EnumBindingKind,
    EnumClientMaxMode,
    EnumClientVerdictAction,
    ModelBindingInstallRequest,
    ModelBindingInstallResult,
    ModelClientArgument,
    ModelClientBinding,
)


def _binding(name: str = "session_delegate") -> ModelClientBinding:
    return ModelClientBinding(
        name=name,
        hook_event="SessionStart",
        command_topic="onex.cmd.demo.session_delegate.v1",
        command_type="ModelSessionDelegateCommand",
        verdict_compute="compute_session_delegate_verdict",
        deadline_ms=30000,
    )


def _request() -> ModelBindingInstallRequest:
    return ModelBindingInstallRequest(
        bindings=(_binding(),),
        max_mode=EnumClientMaxMode.SELECTIVE,
        mods_dir="/opt/demo/mods",
        settings_path="/opt/demo/settings.json",
        supported_probe_rows=("row.demo",),
    )


class TestModelClientBinding:
    def test_minimal_row_round_trips_with_defaults(self) -> None:
        row = _binding()
        assert row.kind is EnumBindingKind.REPLACING
        assert row.arguments == ()
        assert row.awaited_events == ()
        assert row.probe_rows == ()
        assert row.unverified_action is EnumClientVerdictAction.NATIVE
        assert row.deny_text == "delegation adapter unavailable"

    def test_deadline_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ModelClientBinding(
                name="x",
                hook_event="SessionStart",
                command_topic="t",
                command_type="C",
                verdict_compute="v",
                deadline_ms=0,
            )

    def test_extra_fields_are_refused(self) -> None:
        with pytest.raises(ValidationError):
            ModelClientBinding(
                name="x",
                hook_event="SessionStart",
                command_topic="t",
                command_type="C",
                verdict_compute="v",
                deadline_ms=1,
                surprise=True,
            )


class TestModelClientArgument:
    def test_argument_names_its_source_path(self) -> None:
        arg = ModelClientArgument(name="session_id", source="$.session.id")
        assert arg.name == "session_id"
        assert arg.source == "$.session.id"


class TestModelBindingInstallRequest:
    def test_request_round_trips(self) -> None:
        request = _request()
        assert request.max_mode is EnumClientMaxMode.SELECTIVE
        assert request.plugin_name == "onex-claude-code-bindings"
        assert request.bindings[0].name == "session_delegate"

    def test_request_is_frozen(self) -> None:
        request = _request()
        with pytest.raises(ValidationError):
            request.mods_dir = "/elsewhere"


class TestModelBindingInstallResult:
    def test_result_round_trips(self) -> None:
        result = ModelBindingInstallResult(
            module_path="/opt/demo/mods/onex_claude_code_bindings.py",
            render_sha256="sha256:abc",
            installed_sha256="sha256:abc",
            installed_bindings=("session_delegate",),
            skipped_bindings=(),
            registered_commands=("delegate",),
            removed_commands=(),
        )
        assert result.installed_bindings == ("session_delegate",)

    def test_result_fields_are_optional_or_defaulted(self) -> None:
        result = ModelBindingInstallResult(
            module_path=None,
            render_sha256=None,
            installed_sha256=None,
            installed_bindings=(),
            skipped_bindings=(),
            registered_commands=(),
            removed_commands=(),
        )
        assert result.module_path is None
        assert result.removed_commands == ()
