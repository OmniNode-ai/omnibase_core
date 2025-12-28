# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Backwards compatibility tests for OMN-1071 class renames.

This module verifies that all deprecated import paths from PR #261 continue
to work and resolve to their new canonical class names. These tests ensure
that existing code using the old names will not break.

OMN-1071 renamed the following classes to follow ONEX naming conventions:
- Util* prefix for utility classes
- Service* prefix for service classes

The backwards compatibility aliases should remain until at least v0.5.0.

See Also:
    - PR #261: Initial class renames
    - OMN-1071: Rename non-conforming Model/Protocol classes
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestBackwardsCompatibilityOMN1071:
    """
    Test backwards compatibility for OMN-1071 class renames.

    Each test verifies that importing via the deprecated path resolves
    to the same class as the new canonical path.
    """

    def test_model_cli_result_formatter_alias(self) -> None:
        """
        Test ModelCliResultFormatter -> UtilCliResultFormatter alias.

        Old path: omnibase_core.models.cli.ModelCliResultFormatter
        New path: omnibase_core.utils.util_cli_result_formatter.UtilCliResultFormatter
        """
        from omnibase_core.models.cli import ModelCliResultFormatter
        from omnibase_core.utils.util_cli_result_formatter import UtilCliResultFormatter

        assert ModelCliResultFormatter is UtilCliResultFormatter, (
            "ModelCliResultFormatter should be an alias for UtilCliResultFormatter"
        )

    def test_model_security_utils_alias(self) -> None:
        """
        Test ModelSecurityUtils -> UtilSecurity alias.

        Old path: omnibase_core.models.security.ModelSecurityUtils
        New path: omnibase_core.utils.util_security.UtilSecurity
        """
        from omnibase_core.models.security import ModelSecurityUtils
        from omnibase_core.utils.util_security import UtilSecurity

        assert ModelSecurityUtils is UtilSecurity, (
            "ModelSecurityUtils should be an alias for UtilSecurity"
        )

    def test_protocol_contract_loader_alias(self) -> None:
        """
        Test ProtocolContractLoader -> UtilContractLoader alias.

        Old path: omnibase_core.utils.ProtocolContractLoader
        New path: omnibase_core.utils.util_contract_loader.UtilContractLoader
        """
        from omnibase_core.utils import ProtocolContractLoader
        from omnibase_core.utils.util_contract_loader import UtilContractLoader

        assert ProtocolContractLoader is UtilContractLoader, (
            "ProtocolContractLoader should be an alias for UtilContractLoader"
        )

    def test_model_protocol_auditor_alias(self) -> None:
        """
        Test ModelProtocolAuditor -> ServiceProtocolAuditor alias.

        Old path: omnibase_core.validation.ModelProtocolAuditor
        New path: omnibase_core.services.service_protocol_auditor.ServiceProtocolAuditor
        """
        from omnibase_core.services.service_protocol_auditor import (
            ServiceProtocolAuditor,
        )
        from omnibase_core.validation import ModelProtocolAuditor

        assert ModelProtocolAuditor is ServiceProtocolAuditor, (
            "ModelProtocolAuditor should be an alias for ServiceProtocolAuditor"
        )

    def test_protocol_contract_validator_alias(self) -> None:
        """
        Test ProtocolContractValidator -> ServiceContractValidator alias.

        Old path: omnibase_core.validation.ProtocolContractValidator
        New path: omnibase_core.services.service_contract_validator.ServiceContractValidator
        """
        from omnibase_core.services.service_contract_validator import (
            ServiceContractValidator,
        )
        from omnibase_core.validation import ProtocolContractValidator

        assert ProtocolContractValidator is ServiceContractValidator, (
            "ProtocolContractValidator should be an alias for ServiceContractValidator"
        )

    def test_model_conflict_resolver_alias(self) -> None:
        """
        Test ModelConflictResolver -> UtilConflictResolver alias.

        Old path: omnibase_core.models.reducer.ModelConflictResolver
        New path: omnibase_core.utils.util_conflict_resolver.UtilConflictResolver
        """
        from omnibase_core.models.reducer import ModelConflictResolver
        from omnibase_core.utils.util_conflict_resolver import UtilConflictResolver

        assert ModelConflictResolver is UtilConflictResolver, (
            "ModelConflictResolver should be an alias for UtilConflictResolver"
        )

    def test_model_streaming_window_alias(self) -> None:
        """
        Test ModelStreamingWindow -> UtilStreamingWindow alias.

        Old path: omnibase_core.models.reducer.ModelStreamingWindow
        New path: omnibase_core.utils.util_streaming_window.UtilStreamingWindow
        """
        from omnibase_core.models.reducer import ModelStreamingWindow
        from omnibase_core.utils.util_streaming_window import UtilStreamingWindow

        assert ModelStreamingWindow is UtilStreamingWindow, (
            "ModelStreamingWindow should be an alias for UtilStreamingWindow"
        )

    def test_model_validation_suite_alias(self) -> None:
        """
        Test ModelValidationSuite -> ServiceValidationSuite alias.

        Old path: omnibase_core.validation.ModelValidationSuite
        New path: omnibase_core.services.service_validation_suite.ServiceValidationSuite
        """
        from omnibase_core.services.service_validation_suite import (
            ServiceValidationSuite,
        )
        from omnibase_core.validation import ModelValidationSuite

        assert ModelValidationSuite is ServiceValidationSuite, (
            "ModelValidationSuite should be an alias for ServiceValidationSuite"
        )

    def test_protocol_migrator_alias(self) -> None:
        """
        Test ProtocolMigrator -> ServiceProtocolMigrator alias.

        Old path: omnibase_core.validation.ProtocolMigrator
        New path: omnibase_core.services.service_protocol_migrator.ServiceProtocolMigrator
        """
        from omnibase_core.services.service_protocol_migrator import (
            ServiceProtocolMigrator,
        )
        from omnibase_core.validation import ProtocolMigrator

        assert ProtocolMigrator is ServiceProtocolMigrator, (
            "ProtocolMigrator should be an alias for ServiceProtocolMigrator"
        )


@pytest.mark.unit
class TestBackwardsCompatibilityAliasesInAll:
    """
    Test that backwards compatibility aliases are properly exported in __all__.

    These tests verify that the deprecated names are included in the module's
    __all__ list, ensuring they appear in star imports and autocomplete.
    """

    def test_model_cli_in_all(self) -> None:
        """Test ModelCliResultFormatter is in models.cli.__all__."""
        from omnibase_core.models import cli

        assert "ModelCliResultFormatter" in cli.__all__

    def test_model_security_in_all(self) -> None:
        """Test ModelSecurityUtils is in models.security.__all__."""
        from omnibase_core.models import security

        assert "ModelSecurityUtils" in security.__all__

    def test_utils_protocol_contract_loader_in_all(self) -> None:
        """Test ProtocolContractLoader is in utils.__all__."""
        from omnibase_core import utils

        assert "ProtocolContractLoader" in utils.__all__

    def test_validation_aliases_in_all(self) -> None:
        """Test backwards compatibility aliases are in validation.__all__."""
        from omnibase_core import validation

        assert "ModelProtocolAuditor" in validation.__all__
        assert "ProtocolContractValidator" in validation.__all__
        assert "ModelValidationSuite" in validation.__all__
        assert "ProtocolMigrator" in validation.__all__
        # Also verify the canonical names are exported
        assert "ServiceProtocolAuditor" in validation.__all__
        assert "ServiceContractValidator" in validation.__all__
        assert "ServiceValidationSuite" in validation.__all__
        assert "ServiceProtocolMigrator" in validation.__all__

    def test_reducer_aliases_in_all(self) -> None:
        """Test backwards compatibility aliases are in models.reducer.__all__."""
        from omnibase_core.models import reducer

        assert "ModelConflictResolver" in reducer.__all__
        assert "ModelStreamingWindow" in reducer.__all__
