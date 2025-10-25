"""
Tests for protocol compliance in validation domain.

Tests that validators implement the required SPI protocols:
- ProtocolComplianceValidator for contract validation
- ProtocolQualityValidator for protocol auditing
"""

import pytest
from omnibase_spi.protocols.validation.protocol_compliance_validator import (
    ProtocolComplianceValidator,
)
from omnibase_spi.protocols.validation.protocol_quality_validator import (
    ProtocolQualityValidator,
)

from omnibase_core.validation.auditor_protocol import ModelProtocolAuditor
from omnibase_core.validation.contract_validator import ProtocolContractValidator


class TestProtocolComplianceValidatorImplementation:
    """Test ProtocolContractValidator implements ProtocolComplianceValidator."""

    def test_contract_validator_implements_protocol(self) -> None:
        """Test that ProtocolContractValidator implements ProtocolComplianceValidator."""
        validator = ProtocolContractValidator()
        assert isinstance(validator, ProtocolComplianceValidator)

    def test_contract_validator_has_required_attributes(self) -> None:
        """Test that ProtocolContractValidator has all required protocol attributes."""
        validator = ProtocolContractValidator()

        # Check required attributes exist
        assert hasattr(validator, "onex_standards")
        assert hasattr(validator, "architecture_rules")
        assert hasattr(validator, "custom_rules")
        assert hasattr(validator, "strict_mode")

        # Check default values
        assert validator.onex_standards is None
        assert validator.architecture_rules is None
        assert validator.custom_rules == []
        assert validator.strict_mode is False

    def test_contract_validator_has_required_methods(self) -> None:
        """Test that ProtocolContractValidator has all required protocol methods."""
        validator = ProtocolContractValidator()

        # Check all required methods exist
        assert hasattr(validator, "validate_file_compliance")
        assert callable(validator.validate_file_compliance)

        assert hasattr(validator, "validate_repository_compliance")
        assert callable(validator.validate_repository_compliance)

        assert hasattr(validator, "validate_onex_naming")
        assert callable(validator.validate_onex_naming)

        assert hasattr(validator, "validate_architecture_compliance")
        assert callable(validator.validate_architecture_compliance)

        assert hasattr(validator, "validate_directory_structure")
        assert callable(validator.validate_directory_structure)

        assert hasattr(validator, "validate_dependency_compliance")
        assert callable(validator.validate_dependency_compliance)

        assert hasattr(validator, "aggregate_compliance_results")
        assert callable(validator.aggregate_compliance_results)

        assert hasattr(validator, "add_custom_rule")
        assert callable(validator.add_custom_rule)

        assert hasattr(validator, "configure_onex_standards")
        assert callable(validator.configure_onex_standards)

        assert hasattr(validator, "get_compliance_summary")
        assert callable(validator.get_compliance_summary)

    def test_contract_validator_backward_compatibility(self) -> None:
        """Test that existing methods still work (backward compatibility)."""
        validator = ProtocolContractValidator()

        # Test that existing methods still exist and work
        assert hasattr(validator, "validate_contract_yaml")
        assert callable(validator.validate_contract_yaml)

        assert hasattr(validator, "validate_model_compliance")
        assert callable(validator.validate_model_compliance)

        assert hasattr(validator, "validate_contract_file")
        assert callable(validator.validate_contract_file)

    def test_contract_validator_with_optional_parameters(self) -> None:
        """Test that ProtocolContractValidator can be initialized with optional parameters."""
        # Test initialization with None values (backward compatible)
        validator = ProtocolContractValidator()
        assert validator.onex_standards is None
        assert validator.architecture_rules is None
        assert validator.strict_mode is False

        # Test initialization with strict mode
        validator_strict = ProtocolContractValidator(strict_mode=True)
        assert validator_strict.strict_mode is True

    @pytest.mark.asyncio
    async def test_protocol_methods_raise_not_implemented(self) -> None:
        """Test that unimplemented protocol methods raise NotImplementedError."""
        validator = ProtocolContractValidator()

        # These methods should raise NotImplementedError with helpful messages
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await validator.validate_file_compliance("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await validator.validate_repository_compliance(".")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await validator.validate_onex_naming("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await validator.validate_architecture_compliance("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await validator.validate_directory_structure(".")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await validator.validate_dependency_compliance("test.py", [])

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await validator.aggregate_compliance_results([])

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await validator.get_compliance_summary([])


class TestProtocolQualityValidatorImplementation:
    """Test ModelProtocolAuditor implements ProtocolQualityValidator."""

    def test_protocol_auditor_implements_protocol(self) -> None:
        """Test that ModelProtocolAuditor implements ProtocolQualityValidator."""
        auditor = ModelProtocolAuditor()
        assert isinstance(auditor, ProtocolQualityValidator)

    def test_protocol_auditor_has_required_attributes(self) -> None:
        """Test that ModelProtocolAuditor has all required protocol attributes."""
        auditor = ModelProtocolAuditor()

        # Check required attributes exist
        assert hasattr(auditor, "standards")
        assert hasattr(auditor, "enable_complexity_analysis")
        assert hasattr(auditor, "enable_duplication_detection")
        assert hasattr(auditor, "enable_style_checking")

        # Check default values
        assert auditor.standards is None
        assert auditor.enable_complexity_analysis is True
        assert auditor.enable_duplication_detection is True
        assert auditor.enable_style_checking is True

    def test_protocol_auditor_has_required_methods(self) -> None:
        """Test that ModelProtocolAuditor has all required protocol methods."""
        auditor = ModelProtocolAuditor()

        # Check all required methods exist
        assert hasattr(auditor, "validate_file_quality")
        assert callable(auditor.validate_file_quality)

        assert hasattr(auditor, "validate_directory_quality")
        assert callable(auditor.validate_directory_quality)

        assert hasattr(auditor, "calculate_quality_metrics")
        assert callable(auditor.calculate_quality_metrics)

        assert hasattr(auditor, "detect_code_smells")
        assert callable(auditor.detect_code_smells)

        assert hasattr(auditor, "check_naming_conventions")
        assert callable(auditor.check_naming_conventions)

        assert hasattr(auditor, "analyze_complexity")
        assert callable(auditor.analyze_complexity)

        assert hasattr(auditor, "validate_documentation")
        assert callable(auditor.validate_documentation)

        assert hasattr(auditor, "suggest_refactoring")
        assert callable(auditor.suggest_refactoring)

        assert hasattr(auditor, "configure_standards")
        assert callable(auditor.configure_standards)

        assert hasattr(auditor, "get_validation_summary")
        assert callable(auditor.get_validation_summary)

    def test_protocol_auditor_backward_compatibility(self) -> None:
        """Test that existing methods still work (backward compatibility)."""
        auditor = ModelProtocolAuditor()

        # Test that existing methods still exist and work
        assert hasattr(auditor, "check_current_repository")
        assert callable(auditor.check_current_repository)

        assert hasattr(auditor, "check_against_spi")
        assert callable(auditor.check_against_spi)

        assert hasattr(auditor, "audit_ecosystem")
        assert callable(auditor.audit_ecosystem)

    def test_protocol_auditor_with_optional_parameters(self) -> None:
        """Test that ModelProtocolAuditor can be initialized with optional parameters."""
        # Test initialization with default values
        auditor = ModelProtocolAuditor()
        assert auditor.standards is None
        assert auditor.enable_complexity_analysis is True
        assert auditor.enable_duplication_detection is True
        assert auditor.enable_style_checking is True

        # Test initialization with custom values
        auditor_custom = ModelProtocolAuditor(
            enable_complexity_analysis=False,
            enable_duplication_detection=False,
            enable_style_checking=False,
        )
        assert auditor_custom.enable_complexity_analysis is False
        assert auditor_custom.enable_duplication_detection is False
        assert auditor_custom.enable_style_checking is False

    @pytest.mark.asyncio
    async def test_protocol_methods_raise_not_implemented(self) -> None:
        """Test that unimplemented protocol methods raise NotImplementedError."""
        auditor = ModelProtocolAuditor()

        # These methods should raise NotImplementedError with helpful messages
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await auditor.validate_file_quality("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await auditor.validate_directory_quality(".")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            auditor.calculate_quality_metrics("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            auditor.detect_code_smells("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await auditor.check_naming_conventions("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await auditor.analyze_complexity("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await auditor.validate_documentation("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            auditor.suggest_refactoring("test.py")

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await auditor.get_validation_summary([])


class TestProtocolIntegration:
    """Integration tests for protocol compliance."""

    def test_both_validators_implement_protocols(self) -> None:
        """Test that both validators implement their respective protocols."""
        contract_validator = ProtocolContractValidator()
        protocol_auditor = ModelProtocolAuditor()

        # Verify protocol implementations
        assert isinstance(contract_validator, ProtocolComplianceValidator)
        assert isinstance(protocol_auditor, ProtocolQualityValidator)

    def test_validators_can_be_used_polymorphically(self) -> None:
        """Test that validators can be used through protocol interfaces."""
        # This tests that the validators can be assigned to protocol types
        compliance_validator: ProtocolComplianceValidator = ProtocolContractValidator()
        quality_validator: ProtocolQualityValidator = ModelProtocolAuditor()

        # Verify they maintain their protocol interfaces
        assert isinstance(compliance_validator, ProtocolComplianceValidator)
        assert isinstance(quality_validator, ProtocolQualityValidator)
