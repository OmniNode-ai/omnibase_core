# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Extended Handler Contract Model for infra-specific YAML fields.

This module defines ModelHandlerContractExtended, a subclass of
ModelHandlerContract that accepts additional fields used by
omnibase_infra's handler_contract.yaml files (handler_routing,
operation_bindings, activation, dict-form input_model/output_model).

The base ``ModelHandlerContract`` stays strict (``extra="forbid"``) so
all other consumers aren't forced to know about infra-specific fields.

See Also:
    - OMN-6483: Create ModelHandlerContractExtended
    - ModelHandlerContract: Base handler contract model

.. versionadded:: 0.32.0
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from omnibase_core.models.contracts.model_handler_contract import (
    ModelHandlerContract,
)


class ModelHandlerContractExtended(ModelHandlerContract):
    """Extension of ModelHandlerContract with infra-specific fields.

    Used by omnibase_infra's handler_contract.yaml files that include
    handler_routing, operation_bindings, activation, and dict-form
    input_model/output_model fields not declared on the base contract.

    Attributes:
        handler_routing: Infra-specific handler routing configuration.
        operation_bindings: Infra-specific operation binding declarations.
        activation: Infra-specific activation configuration.
        input_model: Input model reference (string or dict for infra-extended form).
        output_model: Output model reference (string or dict for infra-extended form).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    handler_routing: (
        dict[str, object] | None
    ) = (  # ONEX_EXCLUDE: dict_str_any - infra routing config has variable schema
        Field(
            default=None,
            description="Infra-specific handler routing configuration",
        )
    )

    operation_bindings: (
        list[dict[str, object]] | None
    ) = (  # ONEX_EXCLUDE: dict_str_any - operation bindings have variable schema
        Field(
            default=None,
            description="Infra-specific operation binding declarations",
        )
    )

    activation: (
        dict[str, object] | None
    ) = (  # ONEX_EXCLUDE: dict_str_any - activation config has variable schema
        Field(
            default=None,
            description="Infra-specific activation configuration",
        )
    )

    # Override input_model/output_model to also accept dict form used by infra
    input_model: (
        dict[  # type: ignore[assignment]
            str, object
        ]
        | str
    ) = (  # ONEX_EXCLUDE: dict_str_any - infra uses dict-form model refs
        Field(
            ...,
            description="Input model reference (string or dict for infra-extended form)",
        )
    )

    output_model: (
        dict[  # type: ignore[assignment]
            str, object
        ]
        | str
    ) = (  # ONEX_EXCLUDE: dict_str_any - infra uses dict-form model refs
        Field(
            ...,
            description="Output model reference (string or dict for infra-extended form)",
        )
    )


def _rebuild_extended() -> None:
    """Rebuild ModelHandlerContractExtended to resolve forward references."""
    from omnibase_core.models.contracts.subcontracts.model_context_integrity_subcontract import (
        ModelContextIntegritySubcontract,
    )
    from omnibase_core.models.routing.model_trust_domain_config import (
        ModelTrustDomainConfig,
    )

    ModelHandlerContractExtended.model_rebuild(
        _types_namespace={
            "ModelContextIntegritySubcontract": ModelContextIntegritySubcontract,
            "ModelTrustDomainConfig": ModelTrustDomainConfig,
        }
    )


_rebuild_extended()

__all__ = [
    "ModelHandlerContractExtended",
]
