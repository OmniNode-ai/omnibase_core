# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-12189: Parity tests verifying compat enum values match canonical core definitions.

These tests guard the migration contract: the compat copies of EnumNodeKind,
EnumExecutionStatus, and EnumMessageCategory must have identical string values
to the canonical omnibase_core versions. When compat is removed on 2026-07-01,
these tests are also removed.
"""

import pytest

pytest.importorskip(
    "omnibase_compat",
    reason="omnibase-compat optional extra not installed; run `uv sync --all-extras`",
)


@pytest.mark.unit
class TestCompatEnumNodeKindParity:
    """Verify omnibase_compat.EnumNodeKind values match omnibase_core.EnumNodeKind."""

    def test_all_compat_values_exist_in_core(self) -> None:
        from omnibase_compat.enums.enum_node_kind import (
            EnumNodeKind as CompatEnumNodeKind,
        )

        from omnibase_core.enums.enum_node_kind import EnumNodeKind as CoreEnumNodeKind

        core_values = {m.value for m in CoreEnumNodeKind}
        for member in CompatEnumNodeKind:
            assert member.value in core_values, (
                f"Compat EnumNodeKind.{member.name}={member.value!r} "
                f"not found in core enum values: {sorted(core_values)}"
            )

    def test_all_compat_values_round_trip_via_core(self) -> None:
        from omnibase_compat.enums.enum_node_kind import (
            EnumNodeKind as CompatEnumNodeKind,
        )

        from omnibase_core.enums.enum_node_kind import EnumNodeKind as CoreEnumNodeKind

        for member in CompatEnumNodeKind:
            core_member = CoreEnumNodeKind(member.value)
            assert core_member.value == member.value


@pytest.mark.unit
class TestCompatEnumExecutionStatusParity:
    """Verify omnibase_compat.EnumExecutionStatus values match omnibase_core."""

    def test_all_compat_values_exist_in_core(self) -> None:
        from omnibase_compat.enums.enum_execution_status import (
            EnumExecutionStatus as CompatEnumExecutionStatus,
        )

        from omnibase_core.enums.enum_execution_status import (
            EnumExecutionStatus as CoreEnumExecutionStatus,
        )

        core_values = {m.value for m in CoreEnumExecutionStatus}
        for member in CompatEnumExecutionStatus:
            assert member.value in core_values, (
                f"Compat EnumExecutionStatus.{member.name}={member.value!r} "
                f"not found in core enum values: {sorted(core_values)}"
            )

    def test_all_compat_values_round_trip_via_core(self) -> None:
        from omnibase_compat.enums.enum_execution_status import (
            EnumExecutionStatus as CompatEnumExecutionStatus,
        )

        from omnibase_core.enums.enum_execution_status import (
            EnumExecutionStatus as CoreEnumExecutionStatus,
        )

        for member in CompatEnumExecutionStatus:
            core_member = CoreEnumExecutionStatus(member.value)
            assert core_member.value == member.value


@pytest.mark.unit
class TestCompatEnumMessageCategoryParity:
    """Verify omnibase_compat.EnumMessageCategory values match omnibase_core."""

    def test_all_compat_values_exist_in_core(self) -> None:
        from omnibase_compat.enums.enum_message_category import (
            EnumMessageCategory as CompatEnumMessageCategory,
        )

        from omnibase_core.enums.enum_execution_shape import (
            EnumMessageCategory as CoreEnumMessageCategory,
        )

        core_values = {m.value for m in CoreEnumMessageCategory}
        for member in CompatEnumMessageCategory:
            assert member.value in core_values, (
                f"Compat EnumMessageCategory.{member.name}={member.value!r} "
                f"not found in core enum values: {sorted(core_values)}"
            )

    def test_all_compat_values_round_trip_via_core(self) -> None:
        from omnibase_compat.enums.enum_message_category import (
            EnumMessageCategory as CompatEnumMessageCategory,
        )

        from omnibase_core.enums.enum_execution_shape import (
            EnumMessageCategory as CoreEnumMessageCategory,
        )

        for member in CompatEnumMessageCategory:
            core_member = CoreEnumMessageCategory(member.value)
            assert core_member.value == member.value

    def test_migration_target_note(self) -> None:
        """EnumMessageCategory lives in enum_execution_shape per canonical ownership docs (OMN-4032)."""
        from omnibase_core.enums import EnumMessageCategory

        assert EnumMessageCategory.EVENT.value == "event"
        assert EnumMessageCategory.COMMAND.value == "command"
        assert EnumMessageCategory.INTENT.value == "intent"
