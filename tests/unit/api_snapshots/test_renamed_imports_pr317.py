"""Import validation tests for PR #317 file renames.

This module validates that all import paths work correctly after the file renames
performed in PR #317 (OMN-1217, OMN-1218, OMN-1219):

decorators/ (OMN-1217):
- allow_dict_any.py -> decorator_allow_dict_any.py
- convert_to_schema.py -> decorator_convert_to_schema.py
- error_handling.py -> decorator_error_handling.py
- pattern_exclusions.py -> decorator_pattern_exclusions.py

errors/ (OMN-1218):
- declarative_errors.py -> error_declarative.py
- exceptions.py -> exception_base.py
- runtime_errors.py -> error_runtime.py

protocols/ (OMN-1219):
- core.py -> protocol_core.py

Tests verify both:
1. Direct imports from the new file paths
2. Re-exports from __init__.py modules
"""

import pytest


@pytest.mark.unit
class TestDecoratorRenamedImports:
    """Verify decorator imports work after OMN-1217 renames."""

    def test_decorator_error_handling_direct_import(self) -> None:
        """Verify direct import from decorator_error_handling.py works."""
        from omnibase_core.decorators.decorator_error_handling import (
            io_error_handling,
            standard_error_handling,
            validation_error_handling,
        )

        # All should be callable decorators
        assert callable(standard_error_handling)
        assert callable(validation_error_handling)
        assert callable(io_error_handling)

    def test_decorator_error_handling_reexport(self) -> None:
        """Verify decorators are re-exported from __init__.py."""
        from omnibase_core.decorators import (
            io_error_handling,
            standard_error_handling,
            validation_error_handling,
        )

        # All should be callable decorators
        assert callable(standard_error_handling)
        assert callable(validation_error_handling)
        assert callable(io_error_handling)

    def test_decorator_allow_dict_any_direct_import(self) -> None:
        """Verify direct import from decorator_allow_dict_any.py works."""
        from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any

        assert callable(allow_dict_any)

    def test_decorator_allow_dict_any_reexport(self) -> None:
        """Verify allow_dict_any is re-exported from __init__.py."""
        from omnibase_core.decorators import allow_dict_any

        assert callable(allow_dict_any)

    def test_decorator_convert_to_schema_direct_import(self) -> None:
        """Verify direct import from decorator_convert_to_schema.py works."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            convert_dict_to_schema,
            convert_list_to_schema,
            convert_to_schema,
        )

        assert callable(convert_to_schema)
        assert callable(convert_dict_to_schema)
        assert callable(convert_list_to_schema)

    def test_decorator_convert_to_schema_reexport(self) -> None:
        """Verify convert_to_schema decorators are re-exported from __init__.py."""
        from omnibase_core.decorators import (
            convert_dict_to_schema,
            convert_list_to_schema,
            convert_to_schema,
        )

        assert callable(convert_to_schema)
        assert callable(convert_dict_to_schema)
        assert callable(convert_list_to_schema)

    def test_decorator_pattern_exclusions_direct_import(self) -> None:
        """Verify direct import from decorator_pattern_exclusions.py works."""
        from omnibase_core.decorators.decorator_pattern_exclusions import (
            allow_any_type,
            allow_legacy_pattern,
            allow_mixed_types,
            exclude_from_onex_standards,
        )

        assert callable(allow_any_type)
        assert callable(allow_legacy_pattern)
        assert callable(allow_mixed_types)
        assert callable(exclude_from_onex_standards)

    def test_decorator_pattern_exclusions_reexport(self) -> None:
        """Verify pattern exclusion decorators are re-exported from __init__.py."""
        from omnibase_core.decorators import (
            allow_any_type,
            allow_legacy_pattern,
            allow_mixed_types,
            exclude_from_onex_standards,
        )

        assert callable(allow_any_type)
        assert callable(allow_legacy_pattern)
        assert callable(allow_mixed_types)
        assert callable(exclude_from_onex_standards)

    def test_decorator_enforce_execution_shape_direct_import(self) -> None:
        """Verify direct import from decorator_enforce_execution_shape.py works."""
        from omnibase_core.decorators.decorator_enforce_execution_shape import (
            enforce_execution_shape,
        )

        assert callable(enforce_execution_shape)

    def test_decorator_enforce_execution_shape_reexport(self) -> None:
        """Verify enforce_execution_shape is re-exported from __init__.py."""
        from omnibase_core.decorators import enforce_execution_shape

        assert callable(enforce_execution_shape)

    def test_decorators_module_all_exports(self) -> None:
        """Verify __all__ in decorators module contains expected exports."""
        from omnibase_core import decorators

        expected_exports = [
            "allow_any_type",
            "allow_dict_any",
            "allow_legacy_pattern",
            "allow_mixed_types",
            "convert_dict_to_schema",
            "convert_list_to_schema",
            "convert_to_schema",
            "enforce_execution_shape",
            "exclude_from_onex_standards",
            "io_error_handling",
            "standard_error_handling",
            "validation_error_handling",
        ]

        assert hasattr(decorators, "__all__")
        for export_name in expected_exports:
            assert export_name in decorators.__all__, (
                f"{export_name} should be in decorators.__all__"
            )


@pytest.mark.unit
class TestErrorsRenamedImports:
    """Verify error imports work after OMN-1218 renames."""

    def test_error_declarative_direct_import(self) -> None:
        """Verify direct import from error_declarative.py works."""
        from omnibase_core.errors.error_declarative import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )

        # All should be exception classes
        assert issubclass(AdapterBindingError, Exception)
        assert issubclass(PurityViolationError, Exception)
        assert issubclass(NodeExecutionError, Exception)
        assert issubclass(UnsupportedCapabilityError, Exception)

    def test_error_declarative_reexport(self) -> None:
        """Verify declarative errors are re-exported from errors.__init__.py."""
        from omnibase_core.errors import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )

        assert issubclass(AdapterBindingError, Exception)
        assert issubclass(PurityViolationError, Exception)
        assert issubclass(NodeExecutionError, Exception)
        assert issubclass(UnsupportedCapabilityError, Exception)

    def test_error_runtime_direct_import(self) -> None:
        """Verify direct import from error_runtime.py works."""
        from omnibase_core.errors.error_runtime import (
            ContractValidationError,
            EventBusError,
            HandlerExecutionError,
            InvalidOperationError,
            RuntimeHostError,
        )

        # All should be exception classes
        assert issubclass(RuntimeHostError, Exception)
        assert issubclass(HandlerExecutionError, Exception)
        assert issubclass(EventBusError, Exception)
        assert issubclass(InvalidOperationError, Exception)
        assert issubclass(ContractValidationError, Exception)

    def test_error_runtime_reexport(self) -> None:
        """Verify runtime errors are re-exported from errors.__init__.py."""
        from omnibase_core.errors import (
            ContractValidationError,
            EventBusError,
            HandlerExecutionError,
            InvalidOperationError,
            RuntimeHostError,
        )

        assert issubclass(RuntimeHostError, Exception)
        assert issubclass(HandlerExecutionError, Exception)
        assert issubclass(EventBusError, Exception)
        assert issubclass(InvalidOperationError, Exception)
        assert issubclass(ContractValidationError, Exception)

    def test_exception_base_direct_import(self) -> None:
        """Verify direct import from exception_base.py works.

        Note: exception_base.py re-exports validation framework exceptions,
        not OnexBaseException/OnexException (which don't exist).
        """
        from omnibase_core.errors.exception_base import (
            ExceptionConfigurationError,
            ExceptionFileProcessingError,
            ExceptionValidationFrameworkError,
        )

        # All should be exception classes
        assert issubclass(ExceptionValidationFrameworkError, Exception)
        assert issubclass(ExceptionConfigurationError, Exception)
        assert issubclass(ExceptionFileProcessingError, Exception)

    def test_model_onex_error_import(self) -> None:
        """Verify ModelOnexError is importable (core error class)."""
        from omnibase_core.errors import ModelOnexError

        assert issubclass(ModelOnexError, Exception)

    def test_errors_module_all_exports(self) -> None:
        """Verify __all__ in errors module contains expected exports."""
        from omnibase_core import errors

        expected_exports = [
            # Declarative errors
            "AdapterBindingError",
            "NodeExecutionError",
            "PurityViolationError",
            "UnsupportedCapabilityError",
            # Runtime errors
            "RuntimeHostError",
            "HandlerExecutionError",
            "EventBusError",
            "InvalidOperationError",
            "ContractValidationError",
            # Core error
            "ModelOnexError",
        ]

        assert hasattr(errors, "__all__")
        for export_name in expected_exports:
            assert export_name in errors.__all__, (
                f"{export_name} should be in errors.__all__"
            )


@pytest.mark.unit
class TestProtocolsRenamedImports:
    """Verify protocol imports work after OMN-1219 renames."""

    def test_protocol_core_direct_import(self) -> None:
        """Verify direct import from protocol_core.py works."""
        from omnibase_core.protocols.protocol_core import ProtocolCanonicalSerializer

        # Should be a class/protocol
        assert isinstance(ProtocolCanonicalSerializer, type)

    def test_protocol_core_reexport(self) -> None:
        """Verify ProtocolCanonicalSerializer is re-exported from protocols.__init__.py."""
        from omnibase_core.protocols import ProtocolCanonicalSerializer

        assert isinstance(ProtocolCanonicalSerializer, type)

    def test_protocol_from_event_direct_import(self) -> None:
        """Verify direct import from protocol_from_event.py works."""
        from omnibase_core.protocols.protocol_from_event import ProtocolFromEvent

        assert isinstance(ProtocolFromEvent, type)

    def test_protocol_generation_config_direct_import(self) -> None:
        """Verify direct import from protocol_generation_config.py works."""
        from omnibase_core.protocols.protocol_generation_config import (
            ProtocolGenerationConfig,
        )

        assert isinstance(ProtocolGenerationConfig, type)

    def test_protocol_import_tracker_direct_import(self) -> None:
        """Verify direct import from protocol_import_tracker.py works."""
        from omnibase_core.protocols.protocol_import_tracker import (
            ProtocolImportTracker,
        )

        assert isinstance(ProtocolImportTracker, type)

    def test_protocol_logger_like_direct_import(self) -> None:
        """Verify direct import from protocol_logger_like.py works."""
        from omnibase_core.protocols.protocol_logger_like import ProtocolLoggerLike

        assert isinstance(ProtocolLoggerLike, type)

    def test_protocol_payload_data_direct_import(self) -> None:
        """Verify direct import from protocol_payload_data.py works."""
        from omnibase_core.protocols.protocol_payload_data import ProtocolPayloadData

        assert isinstance(ProtocolPayloadData, type)

    def test_protocol_smart_log_formatter_direct_import(self) -> None:
        """Verify direct import from protocol_smart_log_formatter.py works."""
        from omnibase_core.protocols.protocol_smart_log_formatter import (
            ProtocolSmartLogFormatter,
        )

        assert isinstance(ProtocolSmartLogFormatter, type)

    def test_protocol_context_aware_output_handler_direct_import(self) -> None:
        """Verify direct import from protocol_context_aware_output_handler.py works."""
        from omnibase_core.protocols.protocol_context_aware_output_handler import (
            ProtocolContextAwareOutputHandler,
        )

        assert isinstance(ProtocolContextAwareOutputHandler, type)

    def test_protocol_contract_validation_invariant_checker_direct_import(self) -> None:
        """Verify direct import from protocol_contract_validation_invariant_checker.py."""
        from omnibase_core.protocols.protocol_contract_validation_invariant_checker import (
            ProtocolContractValidationInvariantChecker,
        )

        assert isinstance(ProtocolContractValidationInvariantChecker, type)

    def test_protocol_contract_profile_factory_direct_import(self) -> None:
        """Verify direct import from protocol_contract_profile_factory.py works."""
        from omnibase_core.protocols.protocol_contract_profile_factory import (
            ProtocolContractProfileFactory,
        )

        assert isinstance(ProtocolContractProfileFactory, type)

    def test_protocols_module_all_exports(self) -> None:
        """Verify __all__ in protocols module contains expected exports."""
        from omnibase_core import protocols

        expected_exports = [
            "ProtocolCanonicalSerializer",
            "ProtocolGenerationConfig",
            "ProtocolImportTracker",
            "ProtocolLoggerLike",
            "ProtocolPayloadData",
            "ProtocolSmartLogFormatter",
            "ProtocolContextAwareOutputHandler",
            "ProtocolContractValidationInvariantChecker",
        ]

        assert hasattr(protocols, "__all__")
        for export_name in expected_exports:
            assert export_name in protocols.__all__, (
                f"{export_name} should be in protocols.__all__"
            )


@pytest.mark.unit
class TestImportConsistencyAcrossRenames:
    """Verify imports from different paths resolve to the same objects."""

    def test_standard_error_handling_same_object(self) -> None:
        """Verify standard_error_handling from module and init are identical."""
        from omnibase_core.decorators import (
            standard_error_handling as init_seh,
        )
        from omnibase_core.decorators.decorator_error_handling import (
            standard_error_handling as module_seh,
        )

        assert module_seh is init_seh

    def test_adapter_binding_error_same_object(self) -> None:
        """Verify AdapterBindingError from module and init are identical."""
        from omnibase_core.errors import (
            AdapterBindingError as InitABE,
        )
        from omnibase_core.errors.error_declarative import (
            AdapterBindingError as ModuleABE,
        )

        assert ModuleABE is InitABE

    def test_runtime_host_error_same_object(self) -> None:
        """Verify RuntimeHostError from module and init are identical."""
        from omnibase_core.errors import (
            RuntimeHostError as InitRHE,
        )
        from omnibase_core.errors.error_runtime import (
            RuntimeHostError as ModuleRHE,
        )

        assert ModuleRHE is InitRHE

    def test_protocol_canonical_serializer_same_object(self) -> None:
        """Verify ProtocolCanonicalSerializer from module and init are identical."""
        from omnibase_core.protocols import (
            ProtocolCanonicalSerializer as InitPCS,
        )
        from omnibase_core.protocols.protocol_core import (
            ProtocolCanonicalSerializer as ModulePCS,
        )

        assert ModulePCS is InitPCS


@pytest.mark.unit
class TestCircularImportPreventionWithRenames:
    """Verify renames don't cause circular import issues."""

    def test_no_circular_imports_decorators(self) -> None:
        """Verify decorators can be imported without circular issues."""
        from omnibase_core.decorators import (
            io_error_handling,
            standard_error_handling,
            validation_error_handling,
        )
        from omnibase_core.errors import ModelOnexError

        # If we get here without ImportError, circular imports are prevented
        assert callable(standard_error_handling)
        assert callable(validation_error_handling)
        assert callable(io_error_handling)
        assert issubclass(ModelOnexError, Exception)

    def test_no_circular_imports_errors_with_decorators(self) -> None:
        """Verify errors and decorators can be imported together."""
        from omnibase_core.decorators import standard_error_handling
        from omnibase_core.errors import (
            AdapterBindingError,
            ModelOnexError,
            NodeExecutionError,
            RuntimeHostError,
        )

        # All should be accessible
        assert callable(standard_error_handling)
        assert issubclass(ModelOnexError, Exception)
        assert issubclass(RuntimeHostError, Exception)
        assert issubclass(AdapterBindingError, Exception)
        assert issubclass(NodeExecutionError, Exception)

    def test_no_circular_imports_protocols_with_errors(self) -> None:
        """Verify protocols and errors can be imported together."""
        from omnibase_core.errors import ModelOnexError, RuntimeHostError
        from omnibase_core.protocols import (
            ProtocolCanonicalSerializer,
            ProtocolValidationResult,
        )

        # All should be accessible
        assert isinstance(ProtocolCanonicalSerializer, type)
        assert isinstance(ProtocolValidationResult, type)
        assert issubclass(ModelOnexError, Exception)
        assert issubclass(RuntimeHostError, Exception)

    def test_no_circular_imports_all_modules(self) -> None:
        """Verify all renamed modules can be imported together."""
        from omnibase_core.decorators import (
            allow_any_type,
            standard_error_handling,
        )
        from omnibase_core.errors import (
            AdapterBindingError,
            ModelOnexError,
            RuntimeHostError,
        )
        from omnibase_core.protocols import (
            ProtocolCanonicalSerializer,
            ProtocolGenerationConfig,
        )

        # All imports should succeed without circular import errors
        assert callable(standard_error_handling)
        assert callable(allow_any_type)
        assert issubclass(ModelOnexError, Exception)
        assert issubclass(RuntimeHostError, Exception)
        assert issubclass(AdapterBindingError, Exception)
        assert isinstance(ProtocolCanonicalSerializer, type)
        assert isinstance(ProtocolGenerationConfig, type)


@pytest.mark.unit
class TestDecoratorFunctionality:
    """Verify renamed decorators actually work as expected."""

    def test_standard_error_handling_wraps_function(self) -> None:
        """Verify standard_error_handling decorator works correctly."""
        from omnibase_core.decorators import standard_error_handling

        @standard_error_handling("Test operation")
        def test_func() -> str:
            return "success"

        assert test_func() == "success"

    def test_standard_error_handling_converts_exception(self) -> None:
        """Verify standard_error_handling converts exceptions to ModelOnexError."""
        from omnibase_core.decorators import standard_error_handling
        from omnibase_core.errors import ModelOnexError

        @standard_error_handling("Test operation")
        def failing_func() -> None:
            raise ValueError("test error")

        with pytest.raises(ModelOnexError) as exc_info:
            failing_func()

        assert "Test operation failed" in str(exc_info.value)

    def test_standard_error_handling_preserves_model_onex_error(self) -> None:
        """Verify standard_error_handling re-raises ModelOnexError as-is."""
        from omnibase_core.decorators import standard_error_handling
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors import ModelOnexError

        original_error = ModelOnexError(
            "Original error", EnumCoreErrorCode.INTERNAL_ERROR
        )

        @standard_error_handling("Test operation")
        def func_with_onex_error() -> None:
            raise original_error

        with pytest.raises(ModelOnexError) as exc_info:
            func_with_onex_error()

        # Should be the same error, not wrapped
        assert exc_info.value is original_error
