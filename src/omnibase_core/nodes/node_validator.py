# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeValidator — abstract base class for generic ONEX validators.

Part of the Generic Validator Node Architecture (OMN-2362).
Blocked by: OMN-2543 (models must exist first).

Each concrete validator extends NodeValidator and implements exactly one
abstract method: validate(). This is the sole entry point for running a
validator — no side-channel execution paths are permitted.

Design constraints:
- validate() accepts only immutable input (ModelValidationRequest is frozen).
- validate() returns only a new ModelValidationReport; it must not mutate
  external state or return mutable state that can affect callers.
- NodeValidator does not import from any concrete validator module.
- No validator-specific logic lives in this base class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.validation.model_validation_request import (
    ModelValidationRequest,
)
from omnibase_core.models.validation.model_validator_descriptor import (
    ModelValidatorDescriptor,
)


class NodeValidator(ABC):
    """Abstract base class for all ONEX validators in the Generic Validator Architecture.

    Each concrete validator must:
    1. Implement the `validate()` abstract method.
    2. Provide a class-level `descriptor` class variable of type `ModelValidatorDescriptor`.

    The `descriptor` is the registry contract: it declares the validator's ID,
    applicable scopes, contract types, tuple types, required capabilities, and
    execution constraints. The `ValidatorRegistry` uses it to match validators
    to `ModelValidationRequest` instances without instantiating validators eagerly.

    Thread safety:
    Concrete validator instances are NOT required to be thread-safe.
    Callers that require concurrent execution must either:
    - create separate instances per thread/task, or
    - protect shared instances with external synchronisation.

    Example:
        >>> from omnibase_core.models.validation.model_validator_descriptor import (
        ...     ModelValidatorDescriptor,
        ... )
        >>> class AlwaysPassValidator(NodeValidator):
        ...     descriptor = ModelValidatorDescriptor(
        ...         validator_id="always_pass",
        ...         applicable_scopes=("file",),
        ...     )
        ...     def validate(
        ...         self, request: ModelValidationRequest
        ...     ) -> ModelValidationReport:
        ...         from omnibase_core.models.validation.model_validation_report import (
        ...             ModelValidationFindingEmbed,
        ...             ModelValidationRequestRef,
        ...         )
        ...         return ModelValidationReport.from_findings(
        ...             findings=(
        ...                 ModelValidationFindingEmbed(
        ...                     validator_id=self.descriptor.validator_id,
        ...                     severity="PASS",
        ...                     message="No issues found.",
        ...                 ),
        ...             ),
        ...             request=ModelValidationRequestRef(profile=request.profile),
        ...         )
    """

    #: Registry contract for this validator. Must be set by every concrete subclass.
    #: The ValidatorRegistry reads this to match the validator to requests.
    descriptor: ModelValidatorDescriptor

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Verify that concrete subclasses declare a descriptor.

        Abstract subclasses (those with remaining abstract methods) are exempt.
        This runs at class-definition time, not at instantiation time.
        """
        super().__init_subclass__(**kwargs)
        # Only enforce on concrete (non-abstract) subclasses.
        if not getattr(cls, "__abstractmethods__", None):
            if not hasattr(cls, "descriptor") or not isinstance(
                cls.descriptor, ModelValidatorDescriptor
            ):
                raise TypeError(
                    f"Concrete NodeValidator subclass '{cls.__name__}' must define "
                    f"a class-level 'descriptor' of type ModelValidatorDescriptor. "
                    f"Example: descriptor = ModelValidatorDescriptor(validator_id='my_validator')"
                )

    @abstractmethod
    def validate(self, request: ModelValidationRequest) -> ModelValidationReport:
        """Run this validator against the given request and return a report.

        This is the sole entry point for executing this validator.
        Implementations must NOT:
        - Accept mutable state as input (ModelValidationRequest is frozen).
        - Return anything that mutates external state.
        - Access side channels (network, database, filesystem) unless declared
          in descriptor.required_capabilities.
        - Import from any concrete validator module.

        Args:
            request: Frozen ModelValidationRequest describing the target and
                scope of the validation run. Callers must not assume the request
                is mutated or stored by the validator.

        Returns:
            A new ModelValidationReport containing all findings for this run.
            The validator_id on all findings must match self.descriptor.validator_id.
        """


__all__ = ["NodeValidator"]
