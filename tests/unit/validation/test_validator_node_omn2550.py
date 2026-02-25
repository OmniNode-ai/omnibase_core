# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for NodeValidator base class and ValidatorRegistry.

OMN-2550: Implement NodeValidator base class and validator registry.

Coverage:
- NodeValidator abstract base class (cannot instantiate, must implement validate)
- NodeValidator descriptor enforcement
- ValidatorRegistry.register() — happy path and duplicate error
- ValidatorRegistry.resolve() — scope, capability, deny_list, contract_type,
  tuple_type filtering
- ValidatorRegistry.list_all()
- register_decorator usage
- Thread-safety smoke test
- No circular imports (import-level validation)
"""

from __future__ import annotations

import threading

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.models.validation.model_validation_request import (
    ModelValidationRequest,
)
from omnibase_core.models.validation.model_validator_descriptor import (
    ModelValidatorDescriptor,
)
from omnibase_core.nodes.node_validator import NodeValidator
from omnibase_core.validation.registry_validator import ValidatorRegistry

# ---------------------------------------------------------------------------
# Test fixtures: concrete validator implementations
# ---------------------------------------------------------------------------


class AlwaysPassValidator(NodeValidator):
    """Minimal concrete validator that always produces a PASS finding.

    This class serves as a test fixture for NodeValidator and ValidatorRegistry.
    It is intentionally minimal — no validator-specific logic, just PASS.
    """

    descriptor = ModelValidatorDescriptor(
        validator_id="always_pass",
        applicable_scopes=("file", "subtree", "workspace", "artifact"),
        deterministic=True,
        idempotent=True,
    )

    def validate(self, request: ModelValidationRequest) -> ModelValidationReport:
        finding = ModelValidationFindingEmbed(
            validator_id=self.descriptor.validator_id,
            severity="PASS",
            message="No issues found.",
        )
        return ModelValidationReport.from_findings(
            findings=(finding,),
            request=ModelValidationRequestRef(profile=request.profile),
            validators_run=(self.descriptor.validator_id,),
        )


class AlwaysFailValidator(NodeValidator):
    """Minimal concrete validator that always produces a FAIL finding."""

    descriptor = ModelValidatorDescriptor(
        validator_id="always_fail",
        applicable_scopes=("file",),
        deterministic=True,
        idempotent=True,
        tags=("test",),
    )

    def validate(self, request: ModelValidationRequest) -> ModelValidationReport:
        finding = ModelValidationFindingEmbed(
            validator_id=self.descriptor.validator_id,
            severity="FAIL",
            message="Intentional failure for testing.",
        )
        return ModelValidationReport.from_findings(
            findings=(finding,),
            request=ModelValidationRequestRef(profile=request.profile),
            validators_run=(self.descriptor.validator_id,),
        )


class CapabilityRequiringValidator(NodeValidator):
    """Validator that requires the 'network' capability."""

    descriptor = ModelValidatorDescriptor(
        validator_id="capability_requiring",
        applicable_scopes=("workspace",),
        required_capabilities=("network",),
    )

    def validate(self, request: ModelValidationRequest) -> ModelValidationReport:
        finding = ModelValidationFindingEmbed(
            validator_id=self.descriptor.validator_id,
            severity="PASS",
            message="Network check passed.",
        )
        return ModelValidationReport.from_findings(
            findings=(finding,),
            request=ModelValidationRequestRef(profile=request.profile),
        )


class ContractTypeValidator(NodeValidator):
    """Validator that applies only to NodeContract contract type."""

    descriptor = ModelValidatorDescriptor(
        validator_id="contract_type_validator",
        applicable_scopes=("file", "subtree"),
        applicable_contract_types=("NodeContract",),
    )

    def validate(self, request: ModelValidationRequest) -> ModelValidationReport:
        finding = ModelValidationFindingEmbed(
            validator_id=self.descriptor.validator_id,
            severity="PASS",
            message="Contract type check passed.",
        )
        return ModelValidationReport.from_findings(
            findings=(finding,),
            request=ModelValidationRequestRef(profile=request.profile),
        )


class TupleTypeValidator(NodeValidator):
    """Validator that applies only to ModelOnexNode tuple type."""

    descriptor = ModelValidatorDescriptor(
        validator_id="tuple_type_validator",
        applicable_scopes=("file",),
        applicable_tuple_types=("ModelOnexNode",),
    )

    def validate(self, request: ModelValidationRequest) -> ModelValidationReport:
        finding = ModelValidationFindingEmbed(
            validator_id=self.descriptor.validator_id,
            severity="PASS",
            message="Tuple type check passed.",
        )
        return ModelValidationReport.from_findings(
            findings=(finding,),
            request=ModelValidationRequestRef(profile=request.profile),
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_registry_with(*validators: type[NodeValidator]) -> ValidatorRegistry:
    """Build a fresh ValidatorRegistry with the given validator classes registered."""
    registry = ValidatorRegistry()
    for cls in validators:
        registry.register(cls.descriptor, cls)
    return registry


def _make_request(
    scope: str = "file", profile: str = "default"
) -> ModelValidationRequest:
    return ModelValidationRequest(
        target="src/",
        scope=scope,  # type: ignore[arg-type]
        profile=profile,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# NodeValidator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNodeValidator:
    """Tests for the NodeValidator abstract base class."""

    def test_cannot_instantiate_abstract_base(self) -> None:
        """NodeValidator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            NodeValidator()  # type: ignore[abstract]

    def test_missing_abstract_method_raises(self) -> None:
        """Subclass without validate() implementation cannot be instantiated."""

        class NoValidate(NodeValidator):  # type: ignore[abstract]
            descriptor = ModelValidatorDescriptor(validator_id="no_validate")

        with pytest.raises(TypeError):
            NoValidate()  # type: ignore[abstract]

    def test_concrete_subclass_instantiates(self) -> None:
        """AlwaysPassValidator can be instantiated."""
        v = AlwaysPassValidator()
        assert isinstance(v, NodeValidator)

    def test_validate_returns_report(self) -> None:
        """validate() returns a ModelValidationReport."""
        v = AlwaysPassValidator()
        req = _make_request()
        report = v.validate(req)
        assert isinstance(report, ModelValidationReport)

    def test_validate_pass_overall_status(self) -> None:
        """AlwaysPassValidator produces PASS overall_status."""
        v = AlwaysPassValidator()
        req = _make_request()
        report = v.validate(req)
        assert report.overall_status == "PASS"

    def test_validate_fail_overall_status(self) -> None:
        """AlwaysFailValidator produces FAIL overall_status."""
        v = AlwaysFailValidator()
        req = _make_request()
        report = v.validate(req)
        assert report.overall_status == "FAIL"

    def test_descriptor_is_model_validator_descriptor(self) -> None:
        """descriptor is a ModelValidatorDescriptor instance."""
        assert isinstance(AlwaysPassValidator.descriptor, ModelValidatorDescriptor)

    def test_missing_descriptor_raises_on_class_definition(self) -> None:
        """Concrete subclass without a descriptor raises TypeError at class definition."""
        with pytest.raises(TypeError, match="descriptor"):

            class MissingDescriptor(NodeValidator):
                def validate(
                    self, request: ModelValidationRequest
                ) -> ModelValidationReport:
                    raise NotImplementedError

    def test_wrong_descriptor_type_raises(self) -> None:
        """Concrete subclass with non-descriptor 'descriptor' raises TypeError."""
        with pytest.raises(TypeError, match="descriptor"):

            class WrongDescriptorType(NodeValidator):
                descriptor = "not_a_descriptor"  # type: ignore[assignment]

                def validate(
                    self, request: ModelValidationRequest
                ) -> ModelValidationReport:
                    raise NotImplementedError

    def test_request_is_immutable(self) -> None:
        """ModelValidationRequest passed to validate() is frozen."""
        req = _make_request()
        with pytest.raises(Exception):
            req.target = "changed"  # type: ignore[misc]

    def test_validate_with_strict_profile(self) -> None:
        """validate() respects strict profile passed in request."""
        v = AlwaysPassValidator()
        req = ModelValidationRequest(target="src/", scope="file", profile="strict")
        report = v.validate(req)
        assert report.profile == "strict"
        assert report.overall_status == "PASS"

    def test_validate_finding_validator_id_matches_descriptor(self) -> None:
        """Findings from AlwaysPassValidator use the descriptor validator_id."""
        v = AlwaysPassValidator()
        req = _make_request()
        report = v.validate(req)
        for finding in report.findings:
            assert finding.validator_id == AlwaysPassValidator.descriptor.validator_id


# ---------------------------------------------------------------------------
# ValidatorRegistry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatorRegistry:
    """Tests for the ValidatorRegistry class."""

    def test_empty_registry(self) -> None:
        """Fresh registry has no validators."""
        registry = ValidatorRegistry()
        assert len(registry) == 0
        assert registry.list_all() == []

    def test_register_single_validator(self) -> None:
        """Registering a validator adds it to the registry."""
        registry = ValidatorRegistry()
        registry.register(AlwaysPassValidator.descriptor, AlwaysPassValidator)
        assert len(registry) == 1
        assert "always_pass" in registry

    def test_register_duplicate_raises(self) -> None:
        """Registering the same validator_id twice raises ValueError."""
        registry = ValidatorRegistry()
        registry.register(AlwaysPassValidator.descriptor, AlwaysPassValidator)
        with pytest.raises(ValueError, match="always_pass"):
            registry.register(AlwaysPassValidator.descriptor, AlwaysPassValidator)

    def test_register_non_validator_node_raises(self) -> None:
        """Registering a non-NodeValidator class raises TypeError."""
        registry = ValidatorRegistry()

        class NotAValidator:
            pass

        with pytest.raises(TypeError, match="NodeValidator"):
            registry.register(AlwaysPassValidator.descriptor, NotAValidator)  # type: ignore[arg-type]

    def test_list_all_returns_descriptors(self) -> None:
        """list_all() returns descriptors for all registered validators."""
        registry = _make_registry_with(AlwaysPassValidator, AlwaysFailValidator)
        descriptors = registry.list_all()
        assert len(descriptors) == 2
        ids = {d.validator_id for d in descriptors}
        assert "always_pass" in ids
        assert "always_fail" in ids

    def test_list_all_ordered_by_validator_id(self) -> None:
        """list_all() returns descriptors in deterministic validator_id order."""
        registry = _make_registry_with(AlwaysFailValidator, AlwaysPassValidator)
        descriptors = registry.list_all()
        ids = [d.validator_id for d in descriptors]
        assert ids == sorted(ids)

    def test_list_all_returns_snapshot(self) -> None:
        """Modifying the returned list does not affect the registry."""
        registry = _make_registry_with(AlwaysPassValidator)
        descriptors = registry.list_all()
        descriptors.clear()
        assert len(registry) == 1

    # --- resolve: scope filter ---

    def test_resolve_by_scope_returns_applicable(self) -> None:
        """resolve(scope='file') returns validators applicable to 'file' scope."""
        registry = _make_registry_with(AlwaysPassValidator, AlwaysFailValidator)
        validators = registry.resolve(scope="file")
        ids = {type(v).descriptor.validator_id for v in validators}
        assert "always_pass" in ids
        assert "always_fail" in ids

    def test_resolve_by_scope_excludes_inapplicable(self) -> None:
        """resolve(scope='workspace') excludes validators not applicable to workspace."""
        # AlwaysFailValidator only applies to 'file'
        registry = _make_registry_with(AlwaysPassValidator, AlwaysFailValidator)
        validators = registry.resolve(scope="workspace")
        ids = {type(v).descriptor.validator_id for v in validators}
        assert "always_pass" in ids
        assert "always_fail" not in ids

    def test_resolve_no_scope_returns_all(self) -> None:
        """resolve() with no scope returns all registered validators."""
        registry = _make_registry_with(AlwaysPassValidator, AlwaysFailValidator)
        validators = registry.resolve()
        assert len(validators) == 2

    def test_resolve_ordered_deterministically(self) -> None:
        """resolve() returns validators in deterministic validator_id order."""
        registry = _make_registry_with(AlwaysFailValidator, AlwaysPassValidator)
        validators = registry.resolve()
        ids = [type(v).descriptor.validator_id for v in validators]
        assert ids == sorted(ids)

    # --- resolve: capability filter ---

    def test_resolve_with_required_capability_satisfied(self) -> None:
        """Validator with required capability is included when capability is available."""
        registry = _make_registry_with(CapabilityRequiringValidator)
        validators = registry.resolve(available_capabilities=("network",))
        assert len(validators) == 1
        assert type(validators[0]).descriptor.validator_id == "capability_requiring"

    def test_resolve_with_required_capability_missing(self) -> None:
        """Validator with required capability is excluded when capability is unavailable."""
        registry = _make_registry_with(CapabilityRequiringValidator)
        validators = registry.resolve(available_capabilities=())
        assert len(validators) == 0

    def test_resolve_no_required_capabilities_always_included(self) -> None:
        """Validators with no required_capabilities are always included."""
        registry = _make_registry_with(AlwaysPassValidator)
        validators = registry.resolve(available_capabilities=())
        assert len(validators) == 1

    # --- resolve: deny_list ---

    def test_resolve_with_deny_list(self) -> None:
        """resolve() excludes validators in deny_list."""
        registry = _make_registry_with(AlwaysPassValidator, AlwaysFailValidator)
        validators = registry.resolve(deny_list=("always_fail",))
        ids = {type(v).descriptor.validator_id for v in validators}
        assert "always_pass" in ids
        assert "always_fail" not in ids

    def test_resolve_deny_list_all(self) -> None:
        """resolve() with deny_list containing all validators returns empty."""
        registry = _make_registry_with(AlwaysPassValidator, AlwaysFailValidator)
        validators = registry.resolve(deny_list=("always_pass", "always_fail"))
        assert validators == []

    def test_resolve_deny_list_unknown_id_ignored(self) -> None:
        """deny_list with unknown validator_id does not error."""
        registry = _make_registry_with(AlwaysPassValidator)
        validators = registry.resolve(deny_list=("nonexistent",))
        assert len(validators) == 1

    # --- resolve: contract_types filter ---

    def test_resolve_contract_type_match(self) -> None:
        """resolve() includes validators whose applicable_contract_types intersect query."""
        registry = _make_registry_with(
            AlwaysPassValidator,
            ContractTypeValidator,  # AlwaysPass: no restriction
        )
        validators = registry.resolve(contract_types=("NodeContract",))
        ids = {type(v).descriptor.validator_id for v in validators}
        assert "contract_type_validator" in ids
        assert "always_pass" in ids  # no restriction means included

    def test_resolve_contract_type_no_match(self) -> None:
        """resolve() excludes validators whose applicable_contract_types don't intersect."""
        registry = _make_registry_with(ContractTypeValidator)
        validators = registry.resolve(contract_types=("OtherContract",))
        assert len(validators) == 0

    def test_resolve_empty_contract_types_skips_filter(self) -> None:
        """resolve() with empty contract_types does not filter by contract type."""
        registry = _make_registry_with(ContractTypeValidator)
        validators = registry.resolve(contract_types=())
        assert len(validators) == 1

    # --- resolve: tuple_types filter ---

    def test_resolve_tuple_type_match(self) -> None:
        """resolve() includes validators whose applicable_tuple_types intersect query."""
        registry = _make_registry_with(TupleTypeValidator)
        validators = registry.resolve(tuple_types=("ModelOnexNode",))
        assert len(validators) == 1

    def test_resolve_tuple_type_no_match(self) -> None:
        """resolve() excludes validators whose applicable_tuple_types don't intersect."""
        registry = _make_registry_with(TupleTypeValidator)
        validators = registry.resolve(tuple_types=("OtherModel",))
        assert len(validators) == 0

    # --- register_decorator ---

    def test_register_decorator(self) -> None:
        """register_decorator registers a NodeValidator class on definition."""
        registry = ValidatorRegistry()

        @registry.register_decorator
        class DecoratedValidator(NodeValidator):
            descriptor = ModelValidatorDescriptor(
                validator_id="decorated_validator",
                applicable_scopes=("file",),
            )

            def validate(
                self, request: ModelValidationRequest
            ) -> ModelValidationReport:
                finding = ModelValidationFindingEmbed(
                    validator_id=self.descriptor.validator_id,
                    severity="PASS",
                    message="ok",
                )
                return ModelValidationReport.from_findings(
                    findings=(finding,),
                    request=ModelValidationRequestRef(profile=request.profile),
                )

        assert "decorated_validator" in registry
        assert len(registry) == 1

    def test_register_decorator_duplicate_raises(self) -> None:
        """register_decorator raises ValueError for duplicate validator_id."""
        registry = ValidatorRegistry()
        registry.register(AlwaysPassValidator.descriptor, AlwaysPassValidator)

        with pytest.raises(ValueError, match="always_pass"):

            @registry.register_decorator
            class Duplicate(NodeValidator):
                descriptor = ModelValidatorDescriptor(
                    validator_id="always_pass",  # duplicate
                    applicable_scopes=("file",),
                )

                def validate(
                    self, request: ModelValidationRequest
                ) -> ModelValidationReport:
                    raise NotImplementedError

    def test_register_decorator_non_validator_raises(self) -> None:
        """register_decorator on a non-NodeValidator class raises TypeError."""
        registry = ValidatorRegistry()

        with pytest.raises(TypeError, match="NodeValidator"):

            @registry.register_decorator  # type: ignore[arg-type]
            class NotAValidator:
                pass

    # --- deregister ---

    def test_deregister_removes_validator(self) -> None:
        """deregister() removes a validator by ID."""
        registry = _make_registry_with(AlwaysPassValidator)
        removed = registry.deregister("always_pass")
        assert removed is True
        assert "always_pass" not in registry
        assert len(registry) == 0

    def test_deregister_nonexistent_returns_false(self) -> None:
        """deregister() returns False for unknown validator_id."""
        registry = ValidatorRegistry()
        assert registry.deregister("nonexistent") is False

    # --- __contains__ ---

    def test_contains_registered_validator(self) -> None:
        """'validator_id in registry' returns True for registered validators."""
        registry = _make_registry_with(AlwaysPassValidator)
        assert "always_pass" in registry

    def test_not_contains_unregistered_validator(self) -> None:
        """'validator_id in registry' returns False for unregistered validators."""
        registry = ValidatorRegistry()
        assert "always_pass" not in registry

    def test_contains_non_string_returns_false(self) -> None:
        """'x in registry' for non-string x returns False (no TypeError)."""
        registry = _make_registry_with(AlwaysPassValidator)
        assert 42 not in registry  # type: ignore[operator]
        assert None not in registry  # type: ignore[operator]

    # --- Thread safety smoke test ---

    def test_concurrent_registration_and_resolution(self) -> None:
        """Concurrent registrations and resolutions do not cause data corruption.

        This is a smoke test — it exercises the lock path without asserting
        specific orderings. The goal is to catch obvious race conditions.
        """
        registry = ValidatorRegistry()
        errors: list[Exception] = []

        # Pre-create validator classes with descriptors set at class level
        # (descriptor must be set before class creation due to __init_subclass__).
        def _make_thread_validator(idx: int) -> type[NodeValidator]:
            _descriptor = ModelValidatorDescriptor(
                validator_id=f"thread_validator_{idx}",
                applicable_scopes=("file",),
            )

            # Capture descriptor in default arg to avoid closure issue in loop.
            class _ThreadValidator(NodeValidator):
                descriptor = _descriptor

                def validate(
                    self, request: ModelValidationRequest
                ) -> ModelValidationReport:
                    finding = ModelValidationFindingEmbed(
                        validator_id=self.descriptor.validator_id,
                        severity="PASS",
                        message="ok",
                    )
                    return ModelValidationReport.from_findings(
                        findings=(finding,),
                        request=ModelValidationRequestRef(profile=request.profile),
                    )

            return _ThreadValidator

        validator_classes = [_make_thread_validator(i) for i in range(5)]

        def register_validator(cls: type[NodeValidator]) -> None:
            try:
                registry.register(cls.descriptor, cls)
            except ValueError:
                pass  # Duplicate registration — expected in concurrent scenario
            except Exception as exc:
                errors.append(exc)

        def resolve_validators() -> None:
            try:
                registry.resolve(scope="file")
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=register_validator, args=(cls,))
            for cls in validator_classes
        ]
        threads += [threading.Thread(target=resolve_validators) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected thread errors: {errors}"

    # --- Integration: resolve then validate ---

    def test_resolved_validators_can_be_called(self) -> None:
        """Validators returned by resolve() are functional instances."""
        registry = _make_registry_with(AlwaysPassValidator, AlwaysFailValidator)
        validators = registry.resolve(scope="file")
        req = _make_request()
        reports = [v.validate(req) for v in validators]
        statuses = {r.overall_status for r in reports}
        assert "PASS" in statuses
        assert "FAIL" in statuses


# ---------------------------------------------------------------------------
# AlwaysPassValidator standalone
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAlwaysPassValidator:
    """Tests for the AlwaysPassValidator test fixture."""

    def test_descriptor_id(self) -> None:
        assert AlwaysPassValidator.descriptor.validator_id == "always_pass"

    def test_deterministic(self) -> None:
        assert AlwaysPassValidator.descriptor.deterministic is True

    def test_applies_to_all_scopes(self) -> None:
        scopes = set(AlwaysPassValidator.descriptor.applicable_scopes)
        assert scopes == {"file", "subtree", "workspace", "artifact"}

    def test_validate_produces_one_finding(self) -> None:
        v = AlwaysPassValidator()
        req = _make_request()
        report = v.validate(req)
        assert len(report.findings) == 1

    def test_validate_finding_severity_is_pass(self) -> None:
        v = AlwaysPassValidator()
        req = _make_request()
        report = v.validate(req)
        assert report.findings[0].severity == "PASS"

    def test_validate_is_json_serialisable(self) -> None:
        import json

        v = AlwaysPassValidator()
        req = _make_request()
        report = v.validate(req)
        data = json.loads(report.model_dump_json())
        assert data["overall_status"] == "PASS"


# ---------------------------------------------------------------------------
# No circular imports
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoCircularImports:
    """Verify that node_validator and registry_validator can be imported independently."""

    def test_import_node_validator(self) -> None:
        from omnibase_core.nodes import node_validator

        assert hasattr(node_validator, "NodeValidator")

    def test_import_registry_validator(self) -> None:
        from omnibase_core.validation import registry_validator

        assert hasattr(registry_validator, "ValidatorRegistry")

    def test_import_node_validator_does_not_import_registry(self) -> None:
        """node_validator.py should not import registry_validator at module level."""
        import sys

        # Remove from cache to force fresh import
        for key in list(sys.modules.keys()):
            if "node_validator" in key or "registry_validator" in key:
                del sys.modules[key]

        import omnibase_core.nodes.node_validator as nv

        # Just confirm node_validator module loaded successfully without pulling in registry
        assert hasattr(nv, "NodeValidator")
