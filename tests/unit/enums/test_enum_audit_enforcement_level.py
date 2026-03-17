# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumAuditEnforcementLevel."""

import pytest

from omnibase_core.enums.audit.enum_audit_enforcement_level import (
    EnumAuditEnforcementLevel,
)


@pytest.mark.unit
class TestEnumAuditEnforcementLevel:
    """Tests for EnumAuditEnforcementLevel enum."""

    def test_permissive_value(self) -> None:
        assert EnumAuditEnforcementLevel.PERMISSIVE.value == "permissive"

    def test_warn_value(self) -> None:
        assert EnumAuditEnforcementLevel.WARN.value == "warn"

    def test_strict_value(self) -> None:
        assert EnumAuditEnforcementLevel.STRICT.value == "strict"

    def test_paranoid_value(self) -> None:
        assert EnumAuditEnforcementLevel.PARANOID.value == "paranoid"

    def test_all_values_present(self) -> None:
        values = {e.value for e in EnumAuditEnforcementLevel}
        assert values == {"permissive", "warn", "strict", "paranoid"}

    def test_is_blocking_permissive(self) -> None:
        assert not EnumAuditEnforcementLevel.PERMISSIVE.is_blocking

    def test_is_blocking_warn(self) -> None:
        assert not EnumAuditEnforcementLevel.WARN.is_blocking

    def test_is_blocking_strict(self) -> None:
        assert EnumAuditEnforcementLevel.STRICT.is_blocking

    def test_is_blocking_paranoid(self) -> None:
        assert EnumAuditEnforcementLevel.PARANOID.is_blocking

    def test_should_rollback_permissive(self) -> None:
        assert not EnumAuditEnforcementLevel.PERMISSIVE.should_rollback

    def test_should_rollback_warn(self) -> None:
        assert not EnumAuditEnforcementLevel.WARN.should_rollback

    def test_should_rollback_strict(self) -> None:
        assert not EnumAuditEnforcementLevel.STRICT.should_rollback

    def test_should_rollback_paranoid(self) -> None:
        assert EnumAuditEnforcementLevel.PARANOID.should_rollback

    def test_should_alert_permissive(self) -> None:
        assert not EnumAuditEnforcementLevel.PERMISSIVE.should_alert

    def test_should_alert_warn(self) -> None:
        assert EnumAuditEnforcementLevel.WARN.should_alert

    def test_should_alert_strict(self) -> None:
        assert not EnumAuditEnforcementLevel.STRICT.should_alert

    def test_should_alert_paranoid(self) -> None:
        assert EnumAuditEnforcementLevel.PARANOID.should_alert

    def test_is_str_enum(self) -> None:
        """Verify it's a string enum for serialization."""
        assert isinstance(EnumAuditEnforcementLevel.STRICT, str)
        assert (
            str(EnumAuditEnforcementLevel.STRICT) == "EnumAuditEnforcementLevel.STRICT"
        )

    def test_re_export_from_enums_init(self) -> None:
        """Verify re-export from enums __init__.py."""
        from omnibase_core.enums import EnumAuditEnforcementLevel as ReExported

        assert ReExported is EnumAuditEnforcementLevel
