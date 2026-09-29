# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed config-store overlay documents (OMN-19391, plan task B2).

Frozen, ``extra="forbid"`` schemas for the overlay keys core owns,
including model configuration and deployment-declared state, the document
envelope every source returns, and the scope a document is read for. None of
them defaults to a model, an endpoint or a price.

``runtime.lane`` (OMN-19746): the typed declaration of a deployment's runtime
lane and its roles, and the startup refusals a runtime applies to it. It names
no lane.

``broker.principal_grants``, ``host.settings`` and ``lane.services``
(OMN-19933) declare broker access, host settings and lane services. Observations
record the state read from a deployment surface and any read failure.
"""

from omnibase_core.models.config_overlay.model_broker_extra_grant import (
    ModelBrokerExtraGrant,
)
from omnibase_core.models.config_overlay.model_broker_principal_declaration import (
    ModelBrokerPrincipalDeclaration,
)
from omnibase_core.models.config_overlay.model_broker_principal_grants_overlay import (
    ModelBrokerPrincipalGrantsOverlay,
)
from omnibase_core.models.config_overlay.model_config_overlay_document import (
    ModelConfigOverlayDocument,
)
from omnibase_core.models.config_overlay.model_config_overlay_scope import (
    ModelConfigOverlayScope,
)
from omnibase_core.models.config_overlay.model_declared_state_observation import (
    ModelDeclaredStateObservation,
)
from omnibase_core.models.config_overlay.model_embedding_endpoint_overlay import (
    ModelEmbeddingEndpointOverlay,
)
from omnibase_core.models.config_overlay.model_host_declaration import (
    ModelHostDeclaration,
)
from omnibase_core.models.config_overlay.model_host_network_interface_setting import (
    ModelHostNetworkInterfaceSetting,
)
from omnibase_core.models.config_overlay.model_host_settings_overlay import (
    ModelHostSettingsOverlay,
)
from omnibase_core.models.config_overlay.model_host_systemd_drop_in import (
    ModelHostSystemdDropIn,
)
from omnibase_core.models.config_overlay.model_host_systemd_unit import (
    ModelHostSystemdUnit,
)
from omnibase_core.models.config_overlay.model_lane_one_shot_job import (
    ModelLaneOneShotJob,
)
from omnibase_core.models.config_overlay.model_lane_service_declaration import (
    ModelLaneServiceDeclaration,
)
from omnibase_core.models.config_overlay.model_lane_services_overlay import (
    ModelLaneServicesOverlay,
)
from omnibase_core.models.config_overlay.model_llm_catalog_entry import (
    ModelLlmCatalogEntry,
)
from omnibase_core.models.config_overlay.model_llm_catalog_overlay import (
    ModelLlmCatalogOverlay,
)
from omnibase_core.models.config_overlay.model_llm_compute_cost_entry import (
    ModelLlmComputeCostEntry,
)
from omnibase_core.models.config_overlay.model_llm_pricing_entry import (
    ModelLlmPricingEntry,
)
from omnibase_core.models.config_overlay.model_llm_pricing_evidence import (
    ModelLlmPricingEvidence,
)
from omnibase_core.models.config_overlay.model_llm_pricing_overlay import (
    ModelLlmPricingOverlay,
)
from omnibase_core.models.config_overlay.model_llm_runner_cost_policy import (
    ModelLlmRunnerCostPolicy,
)
from omnibase_core.models.config_overlay.model_runtime_lane_declaration import (
    RUNTIME_LANE_ENV_VAR,
    RUNTIME_LANE_SCHEMA_VERSION,
    ModelRuntimeLaneDeclaration,
)

__all__ = [
    "RUNTIME_LANE_ENV_VAR",
    "RUNTIME_LANE_SCHEMA_VERSION",
    "ModelBrokerExtraGrant",
    "ModelBrokerPrincipalDeclaration",
    "ModelBrokerPrincipalGrantsOverlay",
    "ModelDeclaredStateObservation",
    "ModelHostDeclaration",
    "ModelHostNetworkInterfaceSetting",
    "ModelHostSettingsOverlay",
    "ModelHostSystemdDropIn",
    "ModelHostSystemdUnit",
    "ModelLaneOneShotJob",
    "ModelLaneServiceDeclaration",
    "ModelLaneServicesOverlay",
    "ModelConfigOverlayDocument",
    "ModelConfigOverlayScope",
    "ModelEmbeddingEndpointOverlay",
    "ModelLlmCatalogEntry",
    "ModelLlmCatalogOverlay",
    "ModelLlmComputeCostEntry",
    "ModelLlmPricingEntry",
    "ModelLlmPricingEvidence",
    "ModelLlmPricingOverlay",
    "ModelLlmRunnerCostPolicy",
    "ModelRuntimeLaneDeclaration",
]
