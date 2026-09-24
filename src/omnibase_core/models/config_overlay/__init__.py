# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed config-store overlay documents (OMN-19391, plan task B2).

Frozen, ``extra="forbid"`` schemas for the three overlay keys core owns
(``llm.catalog``, ``llm.pricing``, ``embedding.endpoint``), the document
envelope every source returns, and the scope a document is read for. None of
them defaults to a model, an endpoint or a price.
"""

from omnibase_core.models.config_overlay.model_config_overlay_document import (
    ModelConfigOverlayDocument,
)
from omnibase_core.models.config_overlay.model_config_overlay_scope import (
    ModelConfigOverlayScope,
)
from omnibase_core.models.config_overlay.model_embedding_endpoint_overlay import (
    ModelEmbeddingEndpointOverlay,
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

__all__ = [
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
]
