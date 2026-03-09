# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelHandlerLifecycleContract and ModelRetryPolicyContract.

Tests cover:
- Model instantiation with minimal and full field sets
- Default value correctness
- Field validation (bounds, literals, required fields)
- Serialization round-trip (model -> dict -> model)
- Frozen model immutability
- Import from public API surface

OMN-4221: Extract ModelHandlerLifecycleContract Pydantic model into omnibase_core
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_handler_lifecycle_contract import (
    ModelHandlerLifecycleContract,
)
from omnibase_core.models.contracts.model_retry_policy_contract import (
    ModelRetryPolicyContract,
)


@pytest.mark.unit
class TestModelRetryPolicyContract:
    """Tests for ModelRetryPolicyContract."""

    @pytest.mark.unit
    def test_default_instantiation(self) -> None:
        """ModelRetryPolicyContract should instantiate with all defaults."""
        policy = ModelRetryPolicyContract()
        assert policy.max_retries == 3
        assert policy.base_delay_seconds == 1.0
        assert policy.backoff_strategy == "exponential"
        assert policy.max_delay_seconds == 30.0

    @pytest.mark.unit
    def test_full_instantiation(self) -> None:
        """ModelRetryPolicyContract should accept all valid field values."""
        policy = ModelRetryPolicyContract(
            max_retries=5,
            base_delay_seconds=2.0,
            backoff_strategy="linear",
            max_delay_seconds=60.0,
        )
        assert policy.max_retries == 5
        assert policy.base_delay_seconds == 2.0
        assert policy.backoff_strategy == "linear"
        assert policy.max_delay_seconds == 60.0

    @pytest.mark.unit
    def test_fixed_backoff_strategy(self) -> None:
        """'fixed' is a valid backoff_strategy literal."""
        policy = ModelRetryPolicyContract(backoff_strategy="fixed")
        assert policy.backoff_strategy == "fixed"

    @pytest.mark.unit
    def test_zero_retries_allowed(self) -> None:
        """max_retries=0 is valid (disables retries)."""
        policy = ModelRetryPolicyContract(max_retries=0)
        assert policy.max_retries == 0

    @pytest.mark.unit
    def test_invalid_backoff_strategy_raises(self) -> None:
        """An unrecognised backoff_strategy should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelRetryPolicyContract.model_validate({"backoff_strategy": "random"})

    @pytest.mark.unit
    def test_max_retries_exceeds_upper_bound_raises(self) -> None:
        """max_retries > 10 should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelRetryPolicyContract(max_retries=11)

    @pytest.mark.unit
    def test_negative_max_retries_raises(self) -> None:
        """max_retries < 0 should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelRetryPolicyContract(max_retries=-1)

    @pytest.mark.unit
    def test_base_delay_too_small_raises(self) -> None:
        """base_delay_seconds below minimum should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelRetryPolicyContract(base_delay_seconds=0.05)

    @pytest.mark.unit
    def test_frozen_model_immutable(self) -> None:
        """ModelRetryPolicyContract is frozen; model_config confirms frozen=True."""
        policy = ModelRetryPolicyContract()
        assert policy.model_config.get("frozen") is True
        # model_copy(update=...) produces a NEW instance; original is unchanged
        new_policy = policy.model_copy(update={"max_retries": 99})
        assert policy.max_retries == 3
        assert new_policy.max_retries == 99

    @pytest.mark.unit
    def test_serialization_round_trip(self) -> None:
        """model_dump() -> model_validate() round-trip must be lossless."""
        policy = ModelRetryPolicyContract(
            max_retries=2,
            base_delay_seconds=0.5,
            backoff_strategy="fixed",
            max_delay_seconds=10.0,
        )
        as_dict = policy.model_dump()
        restored = ModelRetryPolicyContract.model_validate(as_dict)
        assert restored == policy

    @pytest.mark.unit
    def test_no_extra_fields_accepted(self) -> None:
        """extra='forbid' — unknown fields must raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelRetryPolicyContract(  # type: ignore[call-arg]  # NOTE(OMN-4221): intentional unknown kwarg to validate extra='forbid'
                unknown_field="value"
            )


@pytest.mark.unit
class TestModelHandlerLifecycleContract:
    """Tests for ModelHandlerLifecycleContract."""

    @pytest.mark.unit
    def test_minimal_instantiation(self) -> None:
        """ModelHandlerLifecycleContract requires only handler_id and handler_type."""
        contract = ModelHandlerLifecycleContract(
            handler_id="handler.http.outbound",
            handler_type="http",
        )
        assert contract.handler_id == "handler.http.outbound"
        assert contract.handler_type == "http"
        assert contract.supports_warm_start is False
        assert contract.startup_timeout_seconds == 30.0
        assert contract.teardown_timeout_seconds == 10.0
        assert contract.health_check_interval_seconds is None
        assert contract.retry_policy is None

    @pytest.mark.unit
    def test_full_instantiation(self) -> None:
        """ModelHandlerLifecycleContract should accept all valid field values."""
        retry = ModelRetryPolicyContract(max_retries=2, backoff_strategy="linear")
        contract = ModelHandlerLifecycleContract(
            handler_id="handler.kafka.consumer",
            handler_type="kafka",
            supports_warm_start=True,
            startup_timeout_seconds=15.0,
            teardown_timeout_seconds=5.0,
            health_check_interval_seconds=30.0,
            retry_policy=retry,
        )
        assert contract.handler_id == "handler.kafka.consumer"
        assert contract.handler_type == "kafka"
        assert contract.supports_warm_start is True
        assert contract.startup_timeout_seconds == 15.0
        assert contract.teardown_timeout_seconds == 5.0
        assert contract.health_check_interval_seconds == 30.0
        assert contract.retry_policy is not None
        assert contract.retry_policy.max_retries == 2

    @pytest.mark.unit
    def test_custom_handler_type(self) -> None:
        """handler_type accepts custom labels beyond 'http' and 'kafka'."""
        contract = ModelHandlerLifecycleContract(
            handler_id="handler.grpc.client",
            handler_type="grpc",
        )
        assert contract.handler_type == "grpc"

    @pytest.mark.unit
    def test_handler_id_required(self) -> None:
        """Omitting handler_id must raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerLifecycleContract(  # type: ignore[call-arg]  # NOTE(OMN-4221): intentional missing required field
                handler_type="http"
            )

    @pytest.mark.unit
    def test_handler_type_required(self) -> None:
        """Omitting handler_type must raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerLifecycleContract(  # type: ignore[call-arg]  # NOTE(OMN-4221): intentional missing required field
                handler_id="handler.x"
            )

    @pytest.mark.unit
    def test_empty_handler_id_raises(self) -> None:
        """Empty handler_id should raise ValidationError (min_length=1)."""
        with pytest.raises(ValidationError):
            ModelHandlerLifecycleContract(handler_id="", handler_type="http")

    @pytest.mark.unit
    def test_startup_timeout_below_minimum_raises(self) -> None:
        """startup_timeout_seconds < 0.1 should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerLifecycleContract(
                handler_id="handler.x",
                handler_type="http",
                startup_timeout_seconds=0.0,
            )

    @pytest.mark.unit
    def test_teardown_timeout_below_minimum_raises(self) -> None:
        """teardown_timeout_seconds < 0.1 should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerLifecycleContract(
                handler_id="handler.x",
                handler_type="http",
                teardown_timeout_seconds=0.0,
            )

    @pytest.mark.unit
    def test_health_check_interval_below_minimum_raises(self) -> None:
        """health_check_interval_seconds < 1.0 should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerLifecycleContract(
                handler_id="handler.x",
                handler_type="http",
                health_check_interval_seconds=0.5,
            )

    @pytest.mark.unit
    def test_health_check_interval_none_is_valid(self) -> None:
        """health_check_interval_seconds=None disables probing (valid)."""
        contract = ModelHandlerLifecycleContract(
            handler_id="handler.x",
            handler_type="http",
            health_check_interval_seconds=None,
        )
        assert contract.health_check_interval_seconds is None

    @pytest.mark.unit
    def test_frozen_model_immutable(self) -> None:
        """ModelHandlerLifecycleContract is frozen; model_config confirms frozen=True."""
        contract = ModelHandlerLifecycleContract(
            handler_id="handler.x",
            handler_type="http",
        )
        assert contract.model_config.get("frozen") is True
        # model_copy(update=...) produces a NEW instance; original is unchanged
        updated = contract.model_copy(update={"supports_warm_start": True})
        assert contract.supports_warm_start is False
        assert updated.supports_warm_start is True

    @pytest.mark.unit
    def test_no_extra_fields_accepted(self) -> None:
        """extra='forbid' — unknown fields must raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerLifecycleContract(  # type: ignore[call-arg]  # NOTE(OMN-4221): intentional unknown kwarg to validate extra='forbid'
                handler_id="handler.x",
                handler_type="http",
                unknown_field="value",
            )

    @pytest.mark.unit
    def test_serialization_round_trip_without_retry(self) -> None:
        """Serialization round-trip must be lossless (no retry policy)."""
        contract = ModelHandlerLifecycleContract(
            handler_id="handler.http.outbound",
            handler_type="http",
            supports_warm_start=False,
            startup_timeout_seconds=20.0,
            teardown_timeout_seconds=8.0,
        )
        as_dict = contract.model_dump()
        restored = ModelHandlerLifecycleContract.model_validate(as_dict)
        assert restored == contract

    @pytest.mark.unit
    def test_serialization_round_trip_with_retry(self) -> None:
        """Serialization round-trip must be lossless (with retry policy)."""
        retry = ModelRetryPolicyContract(
            max_retries=3,
            base_delay_seconds=2.0,
            backoff_strategy="exponential",
            max_delay_seconds=60.0,
        )
        contract = ModelHandlerLifecycleContract(
            handler_id="handler.kafka.producer",
            handler_type="kafka",
            supports_warm_start=True,
            startup_timeout_seconds=45.0,
            teardown_timeout_seconds=15.0,
            health_check_interval_seconds=60.0,
            retry_policy=retry,
        )
        as_dict = contract.model_dump()
        restored = ModelHandlerLifecycleContract.model_validate(as_dict)
        assert restored == contract

    @pytest.mark.unit
    def test_json_schema_generation(self) -> None:
        """model_json_schema() must succeed and include required fields."""
        schema = ModelHandlerLifecycleContract.model_json_schema()
        assert "handler_id" in schema.get("properties", {})
        assert "handler_type" in schema.get("properties", {})

    @pytest.mark.unit
    def test_whitespace_stripped_from_handler_id(self) -> None:
        """str_strip_whitespace=True strips leading/trailing whitespace."""
        contract = ModelHandlerLifecycleContract(
            handler_id="  handler.http.outbound  ",
            handler_type="  http  ",
        )
        assert contract.handler_id == "handler.http.outbound"
        assert contract.handler_type == "http"


@pytest.mark.unit
class TestModelHandlerLifecycleContractPublicApi:
    """Tests verifying the public API surface (import from contracts package)."""

    @pytest.mark.unit
    def test_import_from_contracts_package(self) -> None:
        """ModelHandlerLifecycleContract and ModelRetryPolicyContract importable from contracts."""
        from omnibase_core.models.contracts import (
            ModelHandlerLifecycleContract,
            ModelRetryPolicyContract,
        )

        contract = ModelHandlerLifecycleContract(
            handler_id="handler.test.api", handler_type="http"
        )
        assert contract.handler_id == "handler.test.api"

        policy = ModelRetryPolicyContract(max_retries=1)
        assert policy.max_retries == 1

    @pytest.mark.unit
    def test_no_infra_imports(self) -> None:
        """The module must not import from omnibase_infra or concrete handlers."""
        import sys

        module_name = "omnibase_core.models.contracts.model_handler_lifecycle_contract"
        # Ensure the module is loaded
        import omnibase_core.models.contracts.model_handler_lifecycle_contract  # noqa: F401

        module = sys.modules[module_name]

        # Check the module's actual imported dependencies (not docstring text)
        # by inspecting __dict__ for any omnibase_infra modules
        infra_imports = [
            key
            for key in module.__dict__
            if hasattr(module.__dict__[key], "__module__")
            and isinstance(module.__dict__[key], type)
            and (module.__dict__[key].__module__ or "").startswith("omnibase_infra")
        ]
        assert infra_imports == [], (
            f"Module must not import from omnibase_infra; found: {infra_imports}"
        )

        # Verify pydantic is the only non-stdlib import
        import types

        for name, obj in module.__dict__.items():
            if isinstance(obj, types.ModuleType):
                assert not obj.__name__.startswith("omnibase_infra"), (
                    f"Found omnibase_infra module import: {obj.__name__}"
                )
