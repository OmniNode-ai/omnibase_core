# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Import/export smoke tests for high-dependency omnibase_core packages (OMN-12388).

These tests verify that the symbol imports expected by downstream repos
(omnibase_infra, omnimarket, omniclaude) do not silently break. They are
deliberately shallow — no deep unit logic — so that a refactor that renames
or removes a public symbol fails loudly here before it propagates.

Covered packages:
- omnibase_core.enums.enum_core_error_code  (EnumCoreErrorCode, helpers)
- omnibase_core.errors  (__init__ re-exports via __getattr__)
- omnibase_core.models.container  (ModelONEXContainer, ModelContainer)
- omnibase_core.models.validation  (ModelContractValidationResult, etc.)
- omnibase_core.models.common  (ModelOnexWarning, ModelRegistryError)
- omnibase_core.models.errors  (ModelOnexError)
- omnibase_core.models.primitives  (ModelSemVer)
- omnibase_core.enums top-level re-exports  (EnumNodeType, etc.)
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# enum_core_error_code
# ---------------------------------------------------------------------------


class TestEnumCoreErrorCodeExports:
    """EnumCoreErrorCode is importable and has the expected structure."""

    def test_enum_core_error_code_importable(self) -> None:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        assert EnumCoreErrorCode is not None

    def test_core_error_code_has_validation_error(self) -> None:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        assert hasattr(EnumCoreErrorCode, "VALIDATION_ERROR")

    def test_core_error_code_has_configuration_error(self) -> None:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        assert hasattr(EnumCoreErrorCode, "CONFIGURATION_ERROR")

    def test_core_error_code_has_operation_failed(self) -> None:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        assert hasattr(EnumCoreErrorCode, "OPERATION_FAILED")

    def test_core_error_code_has_handler_execution_error(self) -> None:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        assert hasattr(EnumCoreErrorCode, "HANDLER_EXECUTION_ERROR")

    def test_get_core_error_description_importable(self) -> None:
        from omnibase_core.enums.enum_core_error_code import get_core_error_description

        assert callable(get_core_error_description)

    def test_get_exit_code_for_core_error_importable(self) -> None:
        from omnibase_core.enums.enum_core_error_code import (
            get_exit_code_for_core_error,
        )

        assert callable(get_exit_code_for_core_error)

    def test_enum_values_are_strings(self) -> None:
        """All EnumCoreErrorCode values must be non-empty strings (ONEX_CORE_*format)."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        for member in EnumCoreErrorCode:
            assert isinstance(member.value, str)
            assert member.value.startswith("ONEX_CORE_")

    def test_enum_extends_onex_error_code(self) -> None:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.enums.enum_onex_error_code import EnumOnexErrorCode

        assert issubclass(EnumCoreErrorCode, EnumOnexErrorCode)


# ---------------------------------------------------------------------------
# errors/__init__.py  — public re-exports
# ---------------------------------------------------------------------------


class TestErrorsInitExports:
    """errors/__init__.py re-exports the expected public symbols."""

    def test_errors_module_importable(self) -> None:
        import omnibase_core.errors as errs

        assert errs is not None

    def test_enum_core_error_code_reexported(self) -> None:
        from omnibase_core.errors import EnumCoreErrorCode

        assert EnumCoreErrorCode is not None

    def test_enum_cli_exit_code_reexported(self) -> None:
        from omnibase_core.errors import EnumCLIExitCode

        assert EnumCLIExitCode is not None

    def test_exception_groups_reexported(self) -> None:
        from omnibase_core.errors import FILE_IO_ERRORS

        assert isinstance(FILE_IO_ERRORS, tuple)
        assert len(FILE_IO_ERRORS) > 0

    def test_pydantic_model_errors_reexported(self) -> None:
        from omnibase_core.errors import PYDANTIC_MODEL_ERRORS

        assert isinstance(PYDANTIC_MODEL_ERRORS, tuple)

    def test_model_onex_error_lazy_import(self) -> None:
        """ModelOnexError is accessible from errors package (lazy import via __getattr__)."""
        from omnibase_core.errors import ModelOnexError

        assert ModelOnexError is not None

    def test_error_codes_helpers_reexported(self) -> None:
        from omnibase_core.errors import register_error_codes

        assert callable(register_error_codes)


# ---------------------------------------------------------------------------
# models.errors — ModelOnexError
# ---------------------------------------------------------------------------


class TestModelOnexErrorExports:
    """ModelOnexError is importable and constructable with required fields."""

    def test_model_onex_error_importable(self) -> None:
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        assert ModelOnexError is not None

    def test_model_onex_error_constructable(self) -> None:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        err = ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="smoke test error",
        )
        assert err.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert err.message == "smoke test error"

    def test_model_onex_error_is_exception(self) -> None:
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        assert issubclass(ModelOnexError, Exception)


# ---------------------------------------------------------------------------
# models.container — ModelONEXContainer, ModelContainer
# ---------------------------------------------------------------------------


class TestContainerModelExports:
    """Container models are importable from expected paths."""

    def test_model_onex_container_importable(self) -> None:
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )

        assert ModelONEXContainer is not None

    def test_model_onex_container_constructable(self) -> None:
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )

        c = ModelONEXContainer(enable_service_registry=False)
        assert c is not None

    def test_model_service_importable(self) -> None:
        """ModelService is importable from the container package."""
        from omnibase_core.models.container.model_service import ModelService

        assert ModelService is not None

    def test_model_onex_container_reexported_from_models(self) -> None:
        """Verify the import path used by omnibase_infra consumers."""
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )

        c = ModelONEXContainer(enable_service_registry=False)
        assert hasattr(c, "get_service")


# ---------------------------------------------------------------------------
# models.validation — ModelContractValidationResult
# ---------------------------------------------------------------------------


class TestValidationModelExports:
    """Validation result models importable from expected contract paths."""

    def test_model_contract_validation_result_importable(self) -> None:
        from omnibase_core.models.validation.model_contract_validation_result import (
            ModelContractValidationResult,
        )

        assert ModelContractValidationResult is not None

    def test_model_contract_validation_result_constructable(self) -> None:
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.validation.model_contract_validation_result import (
            ModelContractValidationResult,
        )

        result = ModelContractValidationResult(
            is_valid=True,
            score=1.0,
            interface_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert result.is_valid
        assert result.score == 1.0


# ---------------------------------------------------------------------------
# models.primitives — ModelSemVer
# ---------------------------------------------------------------------------


class TestModelSemVerExports:
    """ModelSemVer is the canonical version object used across all contracts."""

    def test_model_semver_importable(self) -> None:
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        assert ModelSemVer is not None

    def test_model_semver_constructable(self) -> None:
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        v = ModelSemVer(major=1, minor=2, patch=3)
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_model_semver_equality(self) -> None:
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        v1 = ModelSemVer(major=1, minor=0, patch=0)
        v2 = ModelSemVer(major=1, minor=0, patch=0)
        assert v1 == v2


# ---------------------------------------------------------------------------
# enums top-level re-exports (EnumNodeType etc.)
# ---------------------------------------------------------------------------


class TestEnumsTopLevelReexports:
    """Top-level enums __init__ re-exports the symbols used by downstream repos."""

    def test_enum_node_type_importable_from_enums(self) -> None:
        from omnibase_core.enums import EnumNodeType

        assert EnumNodeType is not None

    def test_enum_node_type_has_effect(self) -> None:
        from omnibase_core.enums import EnumNodeType

        assert hasattr(EnumNodeType, "EFFECT_GENERIC") or any(
            "effect" in m.name.lower() for m in EnumNodeType
        )

    def test_enum_receipt_status_importable(self) -> None:
        from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus

        assert hasattr(EnumReceiptStatus, "PASS")
        assert hasattr(EnumReceiptStatus, "FAIL")
        assert hasattr(EnumReceiptStatus, "ADVISORY")
        assert hasattr(EnumReceiptStatus, "PENDING")


# ---------------------------------------------------------------------------
# models.common — ModelOnexWarning, ModelRegistryError
# ---------------------------------------------------------------------------


class TestCommonModelExports:
    """Common utility models importable (used by error reporting infrastructure)."""

    def test_model_onex_warning_importable(self) -> None:
        from omnibase_core.models.common.model_onex_warning import ModelOnexWarning

        assert ModelOnexWarning is not None

    def test_model_registry_error_importable(self) -> None:
        from omnibase_core.models.common.model_registry_error import ModelRegistryError

        assert ModelRegistryError is not None


# ---------------------------------------------------------------------------
# Module-level importability checks (no symbol access needed)
# ---------------------------------------------------------------------------


class TestModuleImportability:
    """Each high-dependency module can be imported without ImportError."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "omnibase_core.enums.enum_core_error_code",
            "omnibase_core.enums.enum_node_type",
            "omnibase_core.enums.enum_workflow_status",
            "omnibase_core.enums.enum_workflow_execution",
            "omnibase_core.errors",
            "omnibase_core.errors.exception_groups",
            "omnibase_core.errors.error_codes",
            "omnibase_core.models.errors.model_onex_error",
            "omnibase_core.models.container.model_onex_container",
            "omnibase_core.models.container.model_service",
            "omnibase_core.models.primitives.model_semver",
            "omnibase_core.models.validation.model_contract_validation_result",
            "omnibase_core.models.common.model_onex_warning",
            "omnibase_core.models.common.model_registry_error",
            "omnibase_core.enums.ticket.enum_receipt_status",
        ],
    )
    def test_module_importable(self, module_path: str) -> None:
        mod = importlib.import_module(module_path)
        assert mod is not None
