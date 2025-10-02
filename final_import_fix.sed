# Final import fixes for domain reorganization
# Errors
s|from omnibase_core\.core\.errors\.core_errors|from omnibase_core.errors.core_errors|g
s|from omnibase_core\.core\.errors\.onex_error|from omnibase_core.errors.onex_error|g

# Container → infrastructure
s|from omnibase_core\.core\.onex_container import ModelONEXContainer|from omnibase_core.infrastructure.model_onex_container import ModelONEXContainer|g
s|from omnibase_core\.core\.onex_container|from omnibase_core.infrastructure.onex_container|g

# Contracts
s|from omnibase_core\.core\.contracts\.|from omnibase_core.models.contracts.|g

# Monadic
s|from omnibase_core\.core\.monadic\.|from omnibase_core.models.monadic.|g

# Node bases
s|from omnibase_core\.core\.node_core_base|from omnibase_core.infrastructure.node_core_base|g
s|from omnibase_core\.core\.node_base|from omnibase_core.infrastructure.node_base|g
s|from omnibase_core\.core\.node_effect|from omnibase_core.infrastructure.node_effect|g
s|from omnibase_core\.core\.node_compute|from omnibase_core.infrastructure.node_compute|g
s|from omnibase_core\.core\.node_reducer|from omnibase_core.infrastructure.node_reducer|g
s|from omnibase_core\.core\.node_orchestrator|from omnibase_core.infrastructure.node_orchestrator|g
s|from omnibase_core\.core\.node_compute_service|from omnibase_core.infrastructure.node_compute_service|g
s|from omnibase_core\.core\.node_reducer_service|from omnibase_core.infrastructure.node_reducer_service|g
s|from omnibase_core\.core\.node_orchestrator_service|from omnibase_core.infrastructure.node_orchestrator_service|g

# Common types (already has correct path)
s|from omnibase_core\.core\.common_types|from omnibase_core.models.types.model_onex_common_types|g

# UUID service → just use uuid module directly (comment out for manual review)
# s|from omnibase_core\.core\.core_uuid_service|# DELETE: use uuid.uuid4() directly|g

# Delete manifest runner imports (already deleted the file)
s|from omnibase_core\.core\.tool_manifest_discovery|# DELETED: manifest_service_runner pattern deprecated|g

# Delete registry imports
s|from omnibase_core\.core\..*registry.*|# DELETED: using containers now|g

# Delete event bus factory
s|from omnibase_core\.core\.hybrid_event_bus_factory|# DELETED: not needed|g
s|from omnibase_core\.core\.spi_service_registry|# DELETED: using containers now|g

# Core models
s|from omnibase_core\.core\.models|from omnibase_core.models.core|g
