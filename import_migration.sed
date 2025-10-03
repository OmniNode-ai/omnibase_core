#!/usr/bin/env sed -f
# Import migration script for domain reorganization
# Order matters: most specific patterns first!

# Container imports (most specific first)
s/from omnibase_core\.core\.model_onex_container/from omnibase_core.models.container.model_onex_container/g
s/from omnibase_core\.core\.container_service_resolver/from omnibase_core.container.service_resolver/g
s/from omnibase_core\.core\.enhanced_container/from omnibase_core.container.enhanced_container/g
s/import omnibase_core\.core\.model_onex_container/import omnibase_core.models.container.model_onex_container/g
s/import omnibase_core\.core\.container_service_resolver/import omnibase_core.container.service_resolver/g
s/import omnibase_core\.core\.enhanced_container/import omnibase_core.container.enhanced_container/g

# Infrastructure imports (most specific first)
s/from omnibase_core\.core\.infrastructure_service_bases/from omnibase_core.infrastructure.service_bases/g
s/from omnibase_core\.core\.core_bootstrap/from omnibase_core.infrastructure.bootstrap/g
s/from omnibase_core\.core\.node_effect/from omnibase_core.infrastructure.node_effect/g
s/from omnibase_core\.core\.node_compute/from omnibase_core.infrastructure.node_compute/g
s/from omnibase_core\.core\.node_base/from omnibase_core.infrastructure.node_base/g
s/import omnibase_core\.core\.infrastructure_service_bases/import omnibase_core.infrastructure.service_bases/g
s/import omnibase_core\.core\.core_bootstrap/import omnibase_core.infrastructure.bootstrap/g
s/import omnibase_core\.core\.node_effect/import omnibase_core.infrastructure.node_effect/g
s/import omnibase_core\.core\.node_compute/import omnibase_core.infrastructure.node_compute/g
s/import omnibase_core\.core\.node_base/import omnibase_core.infrastructure.node_base/g

# Logging imports (most specific first)
s/from omnibase_core\.core\.core_structured_logging/from omnibase_core.logging.structured/g
s/from omnibase_core\.core\.core_emit_log_event/from omnibase_core.logging.emit/g
s/from omnibase_core\.core\.bootstrap_logger/from omnibase_core.logging.bootstrap_logger/g
s/import omnibase_core\.core\.core_structured_logging/import omnibase_core.logging.structured/g
s/import omnibase_core\.core\.core_emit_log_event/import omnibase_core.logging.emit/g
s/import omnibase_core\.core\.bootstrap_logger/import omnibase_core.logging.bootstrap_logger/g

# Core cleanup imports (most specific first)
s/from omnibase_core\.core\.model_base_collection/from omnibase_core.models.base.model_collection/g
s/from omnibase_core\.core\.type_constraints/from omnibase_core.types.constraints/g
s/from omnibase_core\.core\.decorators/from omnibase_core.utils.decorators/g
s/import omnibase_core\.core\.model_base_collection/import omnibase_core.models.base.model_collection/g
s/import omnibase_core\.core\.type_constraints/import omnibase_core.types.constraints/g
s/import omnibase_core\.core\.decorators/import omnibase_core.utils.decorators/g
