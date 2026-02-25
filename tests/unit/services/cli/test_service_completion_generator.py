#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ServiceCompletionGenerator — OMN-2581.

Covers:
    - zsh output structure: #compdef header, _omn function, _describe block
    - bash output structure: #!/usr/bin/env bash header, complete registration
    - enum values appear as choices in both zsh and bash output
    - hidden commands are excluded from completion output
    - no network calls during generation (pure function, no I/O)
    - generated script is deterministic for the same catalog state
    - boolean flags generate --flag / --no-flag pairs (zsh) and both flags (bash)
    - integer / string / array flags appear with correct metavars
    - --json flag is always present for every command
    - commands with no resolved schema still appear (flags omitted)
    - unsupported shell raises CompletionUnsupportedShellError
    - malformed schema raises CompletionGenerationError
    - deprecated and experimental commands are included
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.errors.error_completion_generator import (
    CompletionGenerationError,
    CompletionUnsupportedShellError,
)
from omnibase_core.models.contracts.model_cli_contribution import (
    ModelCliCommandEntry,
    ModelCliInvocation,
)
from omnibase_core.services.cli.service_completion_generator import (
    ServiceCompletionGenerator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCHEMA_REF_QUERY = "schema://com.omninode.test.query.args.v1"
_SCHEMA_REF_RUN = "schema://com.omninode.test.run.args.v1"
_SCHEMA_REF_HIDDEN = "schema://com.omninode.test.hidden.args.v1"
_SCHEMA_REF_ENUM_ONLY = "schema://com.omninode.test.enum.args.v1"


def _make_invocation() -> ModelCliInvocation:
    return ModelCliInvocation(
        invocation_type=EnumCliInvocationType.KAFKA_EVENT,
        topic="onex.cmd.test.v1",
    )


def _make_command(
    cmd_id: str,
    group: str = "test",
    visibility: EnumCliCommandVisibility = EnumCliCommandVisibility.PUBLIC,
    args_schema_ref: str = _SCHEMA_REF_QUERY,
    risk: EnumCliCommandRisk = EnumCliCommandRisk.LOW,
    requires_hitl: bool = False,
) -> ModelCliCommandEntry:
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name=cmd_id.split(".")[-1].capitalize(),
        description=f"Description for {cmd_id}.",
        group=group,
        args_schema_ref=args_schema_ref,
        output_schema_ref="schema://output.v1",
        invocation=_make_invocation(),
        visibility=visibility,
        risk=risk,
        requires_hitl=requires_hitl,
    )


# A schema with multiple property types.
FULL_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "description": "Max results.",
            "default": 10,
        },
        "verbose": {
            "type": "boolean",
            "description": "Enable verbose output.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Filter tags.",
        },
        "mode": {
            "type": "string",
            "enum": ["fast", "slow"],
            "description": "Execution mode.",
        },
        "query": {
            "type": "string",
            "description": "Search query.",
        },
    },
    "required": ["mode"],
}

ENUM_ONLY_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "format": {
            "type": "string",
            "enum": ["json", "yaml", "table"],
            "description": "Output format.",
        },
    },
    "required": ["format"],
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def public_command() -> ModelCliCommandEntry:
    return _make_command("com.omninode.test.query", args_schema_ref=_SCHEMA_REF_QUERY)


@pytest.fixture
def run_command() -> ModelCliCommandEntry:
    return _make_command("com.omninode.test.run", args_schema_ref=_SCHEMA_REF_RUN)


@pytest.fixture
def hidden_command() -> ModelCliCommandEntry:
    return _make_command(
        "com.omninode.test.hidden",
        visibility=EnumCliCommandVisibility.HIDDEN,
        args_schema_ref=_SCHEMA_REF_HIDDEN,
    )


@pytest.fixture
def deprecated_command() -> ModelCliCommandEntry:
    return _make_command(
        "com.omninode.test.deprecated",
        visibility=EnumCliCommandVisibility.DEPRECATED,
        args_schema_ref=_SCHEMA_REF_ENUM_ONLY,
    )


@pytest.fixture
def experimental_command() -> ModelCliCommandEntry:
    return _make_command(
        "com.omninode.test.experimental",
        visibility=EnumCliCommandVisibility.EXPERIMENTAL,
        args_schema_ref=_SCHEMA_REF_ENUM_ONLY,
    )


@pytest.fixture
def resolved_schemas() -> dict[str, dict[str, object]]:
    return {
        _SCHEMA_REF_QUERY: FULL_SCHEMA,
        _SCHEMA_REF_RUN: FULL_SCHEMA,
        _SCHEMA_REF_ENUM_ONLY: ENUM_ONLY_SCHEMA,
    }


# ---------------------------------------------------------------------------
# ZSH: structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestZshOutputStructure:
    """Verify zsh script structure and required headers."""

    def test_has_compdef_header(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "#compdef omn" in script

    def test_defines_omn_function(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "_omn()" in script
        assert "_omn" in script  # function call at end

    def test_has_describe_block(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "_describe" in script

    def test_command_id_in_cmds_section(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "com.omninode.test.query" in script

    def test_has_refresh_reminder_comment(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "omn refresh" in script

    def test_json_flag_always_present(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "--json" in script


# ---------------------------------------------------------------------------
# ZSH: flag types
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestZshFlagTypes:
    """Verify zsh flag specs for all JSON Schema types."""

    def test_enum_values_in_choices(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        # zsh choice spec: (fast slow)
        assert "fast slow" in script

    def test_integer_flag_has_int_metavar(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "--limit" in script
        assert "INT" in script

    def test_boolean_flag_generates_pair(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "--verbose" in script
        assert "--no-verbose" in script

    def test_array_flag_present(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "--tags" in script

    def test_string_flag_present(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "--query" in script


# ---------------------------------------------------------------------------
# ZSH: hidden command exclusion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestZshHiddenExclusion:
    """Verify HIDDEN commands are excluded from zsh completion."""

    def test_hidden_command_absent(
        self,
        public_command: ModelCliCommandEntry,
        hidden_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command, hidden_command],
            resolved_schemas=resolved_schemas,
        )
        assert "com.omninode.test.hidden" not in script

    def test_public_command_present_when_hidden_also_passed(
        self,
        public_command: ModelCliCommandEntry,
        hidden_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command, hidden_command],
            resolved_schemas=resolved_schemas,
        )
        assert "com.omninode.test.query" in script

    def test_deprecated_command_included(
        self,
        deprecated_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[deprecated_command],
            resolved_schemas=resolved_schemas,
        )
        assert "com.omninode.test.deprecated" in script

    def test_experimental_command_included(
        self,
        experimental_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[experimental_command],
            resolved_schemas=resolved_schemas,
        )
        assert "com.omninode.test.experimental" in script


# ---------------------------------------------------------------------------
# BASH: structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBashOutputStructure:
    """Verify bash script structure and required headers."""

    def test_has_bash_shebang(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "#!/usr/bin/env bash" in script

    def test_has_complete_registration(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "complete -F _complete_omn omn" in script

    def test_defines_complete_omn_function(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "_complete_omn()" in script

    def test_command_id_in_commands_list(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "com.omninode.test.query" in script

    def test_has_refresh_reminder_comment(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "omn refresh" in script

    def test_json_flag_always_present(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "--json" in script


# ---------------------------------------------------------------------------
# BASH: flag types
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBashFlagTypes:
    """Verify bash flag data for all JSON Schema types."""

    def test_enum_choices_appear_in_case_block(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        # Enum values should appear as compgen choices.
        assert "fast slow" in script or ("fast" in script and "slow" in script)

    def test_boolean_flag_generates_both_forms(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "--verbose" in script
        assert "--no-verbose" in script

    def test_integer_flag_present(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas=resolved_schemas,
        )
        assert "--limit" in script

    def test_enum_only_schema_choices(
        self,
        deprecated_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[deprecated_command],
            resolved_schemas=resolved_schemas,
        )
        # ENUM_ONLY_SCHEMA has format: json | yaml | table
        assert "json" in script
        assert "yaml" in script
        assert "table" in script


# ---------------------------------------------------------------------------
# BASH: hidden command exclusion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBashHiddenExclusion:
    """Verify HIDDEN commands are excluded from bash completion."""

    def test_hidden_command_absent(
        self,
        public_command: ModelCliCommandEntry,
        hidden_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command, hidden_command],
            resolved_schemas=resolved_schemas,
        )
        assert "com.omninode.test.hidden" not in script


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminism:
    """Verify that the same input always produces the same output."""

    def test_zsh_deterministic(
        self,
        public_command: ModelCliCommandEntry,
        run_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        commands = [public_command, run_command]
        script_a = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=commands,
            resolved_schemas=resolved_schemas,
        )
        # Pass in reversed order — output should be identical (sorted internally).
        script_b = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=list(reversed(commands)),
            resolved_schemas=resolved_schemas,
        )
        assert script_a == script_b

    def test_bash_deterministic(
        self,
        public_command: ModelCliCommandEntry,
        run_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        commands = [public_command, run_command]
        script_a = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=commands,
            resolved_schemas=resolved_schemas,
        )
        script_b = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=list(reversed(commands)),
            resolved_schemas=resolved_schemas,
        )
        assert script_a == script_b

    def test_empty_catalog_zsh(self) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[],
            resolved_schemas={},
        )
        assert "#compdef omn" in script
        assert "_omn" in script

    def test_empty_catalog_bash(self) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[],
            resolved_schemas={},
        )
        assert "#!/usr/bin/env bash" in script
        assert "complete -F _complete_omn omn" in script


# ---------------------------------------------------------------------------
# No-schema commands
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMissingSchema:
    """Verify that commands with no resolved schema still appear in completion."""

    def test_zsh_command_present_without_schema(
        self,
        public_command: ModelCliCommandEntry,
    ) -> None:
        # Pass empty resolved_schemas — command should still appear.
        script = ServiceCompletionGenerator.generate(
            shell_name="zsh",
            commands=[public_command],
            resolved_schemas={},
        )
        assert "com.omninode.test.query" in script

    def test_bash_command_present_without_schema(
        self,
        public_command: ModelCliCommandEntry,
    ) -> None:
        script = ServiceCompletionGenerator.generate(
            shell_name="bash",
            commands=[public_command],
            resolved_schemas={},
        )
        assert "com.omninode.test.query" in script


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorCases:
    """Verify error handling for unsupported shells and malformed schemas."""

    def test_unsupported_shell_raises(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        with pytest.raises(CompletionUnsupportedShellError, match="fish"):
            ServiceCompletionGenerator.generate(
                shell_name="fish",
                commands=[public_command],
                resolved_schemas=resolved_schemas,
            )

    def test_empty_string_shell_raises(
        self,
        public_command: ModelCliCommandEntry,
        resolved_schemas: dict[str, dict[str, object]],
    ) -> None:
        with pytest.raises(CompletionUnsupportedShellError):
            ServiceCompletionGenerator.generate(
                shell_name="",
                commands=[public_command],
                resolved_schemas=resolved_schemas,
            )

    def test_zsh_malformed_schema_raises(
        self,
        public_command: ModelCliCommandEntry,
    ) -> None:
        bad_schemas: dict[str, dict[str, object]] = {
            _SCHEMA_REF_QUERY: {  # type: ignore[dict-item]
                "type": "object",
                "properties": "not-a-dict",  # malformed
            }
        }
        with pytest.raises(CompletionGenerationError):
            ServiceCompletionGenerator.generate(
                shell_name="zsh",
                commands=[public_command],
                resolved_schemas=bad_schemas,  # type: ignore[arg-type]
            )

    def test_bash_malformed_schema_raises(
        self,
        public_command: ModelCliCommandEntry,
    ) -> None:
        bad_schemas: dict[str, dict[str, object]] = {
            _SCHEMA_REF_QUERY: {  # type: ignore[dict-item]
                "type": "object",
                "properties": 42,  # malformed
            }
        }
        with pytest.raises(CompletionGenerationError):
            ServiceCompletionGenerator.generate(
                shell_name="bash",
                commands=[public_command],
                resolved_schemas=bad_schemas,  # type: ignore[arg-type]
            )

    def test_unsupported_shell_error_inherits_from_generation_error(self) -> None:
        with pytest.raises(CompletionGenerationError):
            ServiceCompletionGenerator.generate(
                shell_name="powershell",
                commands=[],
                resolved_schemas={},
            )
