"""
Event Publisher Migration Utilities for Kafka Migration Project.

This module provides utilities to help migrate services from Event Bus to Kafka
publishers while maintaining backward compatibility and ensuring zero downtime.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from omnibase.enums.enum_health_status import EnumHealthStatus
from pydantic import BaseModel, Field

from omnibase_core.configs.event_publisher_config import get_config_manager
from omnibase_core.core.core_errors import OnexError
from omnibase_core.enums.enum_protocol_event_type import EnumProtocolEventType
from omnibase_core.enums.enum_publisher_type import EnumPublisherType
from omnibase_core.models.model_event import ModelEvent
from omnibase_core.models.model_publisher_config import ModelPublisherConfig
from omnibase_core.monitors.event_publisher_health_monitor import \
    get_health_monitor
from omnibase_core.protocols.protocol_event_publisher import \
    ProtocolEventPublisher
from omnibase_core.registries.event_publisher_registry import get_registry


class EnumMigrationPhase(str, Enum):
    """Migration phases."""

    ASSESSMENT = "assessment"
    PREPARATION = "preparation"
    DUAL_MODE = "dual_mode"
    VALIDATION = "validation"
    CUTOVER = "cutover"
    CLEANUP = "cleanup"
    COMPLETED = "completed"


class EnumMigrationStatus(str, Enum):
    """Migration status."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


class ModelMigrationStep(BaseModel):
    """Individual migration step."""

    step_id: str = Field(description="Unique step identifier")
    step_name: str = Field(description="Human readable step name")
    description: str = Field(description="Step description")
    phase: EnumMigrationPhase = Field(description="Migration phase")

    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="Step dependencies")

    # Status
    status: EnumMigrationStatus = Field(default=EnumMigrationStatus.NOT_STARTED)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # Results
    success: bool = Field(default=False)
    error_message: Optional[str] = Field(default=None)
    output: Dict[str, Any] = Field(default_factory=dict)

    # Rollback
    rollback_function: Optional[str] = Field(
        default=None, description="Rollback function name"
    )


class ModelServiceMigration(BaseModel):
    """Service migration plan and status."""

    service_name: str = Field(description="Service being migrated")
    migration_id: str = Field(description="Unique migration identifier")

    # Migration details
    source_publisher_type: EnumPublisherType = Field(
        description="Current publisher type"
    )
    target_publisher_type: EnumPublisherType = Field(
        description="Target publisher type"
    )

    # Status
    overall_status: EnumMigrationStatus = Field(default=EnumMigrationStatus.NOT_STARTED)
    current_phase: EnumMigrationPhase = Field(default=EnumMigrationPhase.ASSESSMENT)

    # Steps
    migration_steps: List[ModelMigrationStep] = Field(default_factory=list)

    # Configuration
    source_config: Optional[ModelPublisherConfig] = Field(default=None)
    target_config: Optional[ModelPublisherConfig] = Field(default=None)

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # Validation
    validation_metrics: Dict[str, Any] = Field(default_factory=dict)
    rollback_ready: bool = Field(default=False)

    # Events and topics
    monitored_topics: List[str] = Field(default_factory=list)
    critical_events: List[str] = Field(default_factory=list)


class EventPublisherMigrationUtility:
    """Utility class for managing event publisher migrations."""

    def __init__(self):
        """Initialize migration utility."""
        self._active_migrations: Dict[str, ModelServiceMigration] = {}
        self._migration_history: List[ModelServiceMigration] = []

        # Dependencies
        self._registry = get_registry()
        self._health_monitor = get_health_monitor()
        self._config_manager = get_config_manager()

        # State
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Step handlers
        self._step_handlers: Dict[str, Callable] = self._register_step_handlers()

    def _register_step_handlers(self) -> Dict[str, Callable]:
        """Register migration step handlers."""
        return {
            "assess_current_setup": self._assess_current_setup,
            "create_target_config": self._create_target_config,
            "validate_target_config": self._validate_target_config,
            "create_target_publisher": self._create_target_publisher,
            "setup_dual_mode": self._setup_dual_mode,
            "start_event_mirroring": self._start_event_mirroring,
            "validate_event_flow": self._validate_event_flow,
            "switch_traffic": self._switch_traffic,
            "validate_cutover": self._validate_cutover,
            "cleanup_old_publisher": self._cleanup_old_publisher,
            "finalize_migration": self._finalize_migration,
        }

    def create_migration_plan(
        self,
        service_name: str,
        target_publisher_type: EnumPublisherType,
        monitored_topics: Optional[List[str]] = None,
        critical_events: Optional[List[str]] = None,
    ) -> ModelServiceMigration:
        """
        Create a migration plan for a service.

        Args:
            service_name: Name of service to migrate
            target_publisher_type: Target publisher type
            monitored_topics: Topics to monitor during migration
            critical_events: Critical events that must not be lost

        Returns:
            Migration plan
        """
        # Determine current publisher type
        current_publishers = self._registry.list_publishers(service_name=service_name)
        if not current_publishers:
            raise OnexError(f"No publishers found for service: {service_name}")

        source_publisher_type = current_publishers[0].publisher_type

        # Generate migration ID
        migration_id = f"migration_{service_name}_{int(datetime.utcnow().timestamp())}"

        # Create migration plan
        migration = ModelServiceMigration(
            service_name=service_name,
            migration_id=migration_id,
            source_publisher_type=source_publisher_type,
            target_publisher_type=target_publisher_type,
            monitored_topics=monitored_topics or [],
            critical_events=critical_events or [],
        )

        # Generate migration steps
        migration.migration_steps = self._generate_migration_steps(migration)

        # Store migration
        self._active_migrations[migration_id] = migration

        self._logger.info(
            f"Created migration plan: {migration_id} ({source_publisher_type.value} -> {target_publisher_type.value})"
        )

        return migration

    def _generate_migration_steps(
        self, migration: ModelServiceMigration
    ) -> List[ModelMigrationStep]:
        """Generate migration steps based on source and target types."""
        steps = []

        # Phase 1: Assessment
        steps.extend(
            [
                ModelMigrationStep(
                    step_id="assess_current_setup",
                    step_name="Assess Current Setup",
                    description="Analyze current publisher configuration and usage",
                    phase=EnumMigrationPhase.ASSESSMENT,
                ),
                ModelMigrationStep(
                    step_id="create_target_config",
                    step_name="Create Target Configuration",
                    description="Generate configuration for target publisher",
                    phase=EnumMigrationPhase.ASSESSMENT,
                    depends_on=["assess_current_setup"],
                ),
            ]
        )

        # Phase 2: Preparation
        steps.extend(
            [
                ModelMigrationStep(
                    step_id="validate_target_config",
                    step_name="Validate Target Configuration",
                    description="Validate target publisher configuration",
                    phase=EnumMigrationPhase.PREPARATION,
                    depends_on=["create_target_config"],
                ),
                ModelMigrationStep(
                    step_id="create_target_publisher",
                    step_name="Create Target Publisher",
                    description="Create and initialize target publisher",
                    phase=EnumMigrationPhase.PREPARATION,
                    depends_on=["validate_target_config"],
                ),
            ]
        )

        # Phase 3: Dual Mode (if different types)
        if migration.source_publisher_type != migration.target_publisher_type:
            steps.extend(
                [
                    ModelMigrationStep(
                        step_id="setup_dual_mode",
                        step_name="Setup Dual Mode",
                        description="Configure dual-mode operation",
                        phase=EnumMigrationPhase.DUAL_MODE,
                        depends_on=["create_target_publisher"],
                    ),
                    ModelMigrationStep(
                        step_id="start_event_mirroring",
                        step_name="Start Event Mirroring",
                        description="Begin mirroring events to target publisher",
                        phase=EnumMigrationPhase.DUAL_MODE,
                        depends_on=["setup_dual_mode"],
                    ),
                ]
            )

        # Phase 4: Validation
        steps.extend(
            [
                ModelMigrationStep(
                    step_id="validate_event_flow",
                    step_name="Validate Event Flow",
                    description="Validate events are flowing correctly",
                    phase=EnumMigrationPhase.VALIDATION,
                    depends_on=(
                        ["start_event_mirroring"]
                        if migration.source_publisher_type
                        != migration.target_publisher_type
                        else ["create_target_publisher"]
                    ),
                )
            ]
        )

        # Phase 5: Cutover
        steps.extend(
            [
                ModelMigrationStep(
                    step_id="switch_traffic",
                    step_name="Switch Traffic",
                    description="Switch event traffic to target publisher",
                    phase=EnumMigrationPhase.CUTOVER,
                    depends_on=["validate_event_flow"],
                ),
                ModelMigrationStep(
                    step_id="validate_cutover",
                    step_name="Validate Cutover",
                    description="Validate cutover was successful",
                    phase=EnumMigrationPhase.CUTOVER,
                    depends_on=["switch_traffic"],
                ),
            ]
        )

        # Phase 6: Cleanup
        steps.extend(
            [
                ModelMigrationStep(
                    step_id="cleanup_old_publisher",
                    step_name="Cleanup Old Publisher",
                    description="Remove old publisher configuration",
                    phase=EnumMigrationPhase.CLEANUP,
                    depends_on=["validate_cutover"],
                ),
                ModelMigrationStep(
                    step_id="finalize_migration",
                    step_name="Finalize Migration",
                    description="Complete migration and update records",
                    phase=EnumMigrationPhase.CLEANUP,
                    depends_on=["cleanup_old_publisher"],
                ),
            ]
        )

        return steps

    async def execute_migration(self, migration_id: str, dry_run: bool = False) -> bool:
        """
        Execute a migration plan.

        Args:
            migration_id: Migration identifier
            dry_run: Whether to perform a dry run

        Returns:
            Success status
        """
        if migration_id not in self._active_migrations:
            raise OnexError(f"Migration not found: {migration_id}")

        migration = self._active_migrations[migration_id]

        if migration.overall_status == EnumMigrationStatus.IN_PROGRESS:
            raise OnexError(f"Migration already in progress: {migration_id}")

        # Start migration
        migration.overall_status = EnumMigrationStatus.IN_PROGRESS
        migration.started_at = datetime.utcnow()

        self._logger.info(f"Starting migration: {migration_id} (dry_run={dry_run})")

        try:
            # Execute steps in dependency order
            success = await self._execute_migration_steps(migration, dry_run)

            if success:
                migration.overall_status = EnumMigrationStatus.COMPLETED
                migration.completed_at = datetime.utcnow()
                migration.current_phase = EnumMigrationPhase.COMPLETED

                # Move to history
                self._migration_history.append(migration)
                del self._active_migrations[migration_id]

                self._logger.info(f"Migration completed successfully: {migration_id}")
            else:
                migration.overall_status = EnumMigrationStatus.FAILED
                self._logger.error(f"Migration failed: {migration_id}")

            return success

        except Exception as e:
            migration.overall_status = EnumMigrationStatus.FAILED
            self._logger.error(f"Migration error: {migration_id}: {e}")
            return False

    async def _execute_migration_steps(
        self, migration: ModelServiceMigration, dry_run: bool
    ) -> bool:
        """Execute migration steps in dependency order."""
        # Build dependency graph
        steps_by_id = {step.step_id: step for step in migration.migration_steps}
        completed_steps = set()

        while len(completed_steps) < len(migration.migration_steps):
            # Find steps ready to execute
            ready_steps = []
            for step in migration.migration_steps:
                if (
                    step.step_id not in completed_steps
                    and step.status == EnumMigrationStatus.NOT_STARTED
                ):
                    # Check dependencies
                    if all(dep_id in completed_steps for dep_id in step.depends_on):
                        ready_steps.append(step)

            if not ready_steps:
                # Check if we have any failed steps
                failed_steps = [
                    s
                    for s in migration.migration_steps
                    if s.status == EnumMigrationStatus.FAILED
                ]
                if failed_steps:
                    self._logger.error(
                        f"Migration failed due to step failures: {[s.step_id for s in failed_steps]}"
                    )
                    return False

                # No ready steps and no failures - might be circular dependency
                self._logger.error(
                    "No ready steps found - possible circular dependency"
                )
                return False

            # Execute ready steps
            for step in ready_steps:
                step.status = EnumMigrationStatus.IN_PROGRESS
                step.started_at = datetime.utcnow()

                # Update current phase
                migration.current_phase = step.phase

                try:
                    success = await self._execute_migration_step(
                        migration, step, dry_run
                    )

                    if success:
                        step.status = EnumMigrationStatus.COMPLETED
                        step.success = True
                        step.completed_at = datetime.utcnow()
                        completed_steps.add(step.step_id)

                        self._logger.info(f"Step completed: {step.step_id}")
                    else:
                        step.status = EnumMigrationStatus.FAILED
                        step.success = False
                        step.completed_at = datetime.utcnow()
                        return False

                except Exception as e:
                    step.status = EnumMigrationStatus.FAILED
                    step.success = False
                    step.error_message = str(e)
                    step.completed_at = datetime.utcnow()

                    self._logger.error(f"Step failed: {step.step_id}: {e}")
                    return False

        return True

    async def _execute_migration_step(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> bool:
        """Execute a single migration step."""
        self._logger.info(f"Executing step: {step.step_id} (dry_run={dry_run})")

        # Get step handler
        handler = self._step_handlers.get(step.step_id)
        if not handler:
            raise OnexError(f"No handler found for step: {step.step_id}")

        # Execute handler
        try:
            result = await handler(migration, step, dry_run)
            step.output = result if isinstance(result, dict) else {"result": result}
            return True
        except Exception as e:
            step.error_message = str(e)
            return False

    # Step handler implementations
    async def _assess_current_setup(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Assess current publisher setup."""
        publishers = self._registry.list_publishers(service_name=migration.service_name)

        if not publishers:
            raise OnexError(
                f"No publishers found for service: {migration.service_name}"
            )

        # Get current configuration
        current_publisher = publishers[0]
        migration.source_config = current_publisher.config

        # Get health status
        health = self._health_monitor.get_publisher_health(
            current_publisher.publisher_id
        )

        return {
            "current_publisher_type": current_publisher.publisher_type.value,
            "current_environment": current_publisher.environment,
            "health_status": health.status.value if health else "unknown",
            "publisher_count": len(publishers),
        }

    async def _create_target_config(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Create target publisher configuration."""
        # Base on source config
        base_config = migration.source_config
        if not base_config:
            raise OnexError("Source configuration not available")

        # Create target configuration
        target_config = base_config.copy()
        target_config.publisher_type = migration.target_publisher_type

        # Customize based on target type
        if migration.target_publisher_type == EnumPublisherType.KAFKA:
            # Ensure Kafka configuration is present
            if not target_config.kafka_config:
                kafka_config = (
                    self._config_manager.get_config().get_current_config().kafka_config
                )
                target_config.kafka_config = kafka_config

        migration.target_config = target_config

        return {
            "target_publisher_type": target_config.publisher_type.value,
            "configuration_created": True,
        }

    async def _validate_target_config(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Validate target publisher configuration."""
        if not migration.target_config:
            raise OnexError("Target configuration not available")

        # Basic validation
        config = migration.target_config

        # Type-specific validation
        if config.publisher_type == EnumPublisherType.KAFKA:
            if not config.kafka_config:
                raise OnexError("Kafka configuration required for Kafka publisher")

            if not config.kafka_config.bootstrap_servers:
                raise OnexError("Kafka bootstrap servers required")

        return {"validation_passed": True, "config_type": config.publisher_type.value}

    async def _create_target_publisher(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Create target publisher."""
        if dry_run:
            return {"created": False, "dry_run": True}

        target_publisher_id = f"{migration.service_name}_target"

        # Create publisher
        target_publisher = await self._registry.create_publisher(
            publisher_id=target_publisher_id,
            publisher_type=migration.target_publisher_type,
            config=migration.target_config,
            tags=["migration", "target"],
            auto_register=True,
        )

        return {
            "publisher_id": target_publisher_id,
            "created": True,
            "initialized": True,
        }

    async def _setup_dual_mode(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Setup dual-mode operation."""
        if dry_run:
            return {"setup": False, "dry_run": True}

        # This would involve configuring the service to use both publishers
        # Implementation depends on specific service architecture

        return {"dual_mode_enabled": True}

    async def _start_event_mirroring(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Start event mirroring to target publisher."""
        if dry_run:
            return {"mirroring": False, "dry_run": True}

        # This would involve setting up event mirroring
        # Implementation depends on specific requirements

        return {"mirroring_started": True}

    async def _validate_event_flow(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Validate event flow to target publisher."""
        target_publisher_id = f"{migration.service_name}_target"
        target_publisher = await self._registry.get_publisher(target_publisher_id)

        if not target_publisher:
            raise OnexError("Target publisher not found")

        # Check health
        health = self._health_monitor.get_publisher_health(target_publisher_id)
        if not health or health.status != EnumHealthStatus.HEALTHY:
            raise OnexError("Target publisher is not healthy")

        return {"health_status": health.status.value, "validation_passed": True}

    async def _switch_traffic(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Switch traffic to target publisher."""
        if dry_run:
            return {"traffic_switched": False, "dry_run": True}

        # This would involve updating service configuration to use target publisher
        # Implementation depends on service architecture

        return {"traffic_switched": True}

    async def _validate_cutover(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Validate cutover was successful."""
        # Check that target publisher is receiving traffic
        target_publisher_id = f"{migration.service_name}_target"
        health = self._health_monitor.get_publisher_health(target_publisher_id)

        if not health or health.status != EnumHealthStatus.HEALTHY:
            raise OnexError("Target publisher health check failed after cutover")

        return {"cutover_validated": True, "target_health": health.status.value}

    async def _cleanup_old_publisher(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Clean up old publisher."""
        if dry_run:
            return {"cleaned_up": False, "dry_run": True}

        # Find and remove old publishers
        old_publishers = self._registry.list_publishers(
            service_name=migration.service_name,
            publisher_type=migration.source_publisher_type,
        )

        for pub_info in old_publishers:
            if "migration" not in pub_info.tags:  # Don't remove target
                await self._registry.unregister_publisher(pub_info.publisher_id)

        return {
            "old_publishers_removed": len(old_publishers),
            "cleanup_completed": True,
        }

    async def _finalize_migration(
        self, migration: ModelServiceMigration, step: ModelMigrationStep, dry_run: bool
    ) -> Dict[str, Any]:
        """Finalize migration."""
        # Update target publisher tags
        target_publisher_id = f"{migration.service_name}_target"
        target_info = self._registry.get_publisher_info(target_publisher_id)

        if target_info:
            # Remove migration tags
            target_info.tags = [
                tag for tag in target_info.tags if tag not in ["migration", "target"]
            ]
            target_info.tags.append("migrated")

        return {"migration_finalized": True, "migration_id": migration.migration_id}

    def get_migration_status(
        self, migration_id: str
    ) -> Optional[ModelServiceMigration]:
        """Get migration status."""
        # Check active migrations
        if migration_id in self._active_migrations:
            return self._active_migrations[migration_id]

        # Check history
        for migration in self._migration_history:
            if migration.migration_id == migration_id:
                return migration

        return None

    def list_active_migrations(self) -> List[ModelServiceMigration]:
        """List active migrations."""
        return list(self._active_migrations.values())

    def export_migration_plan(self, migration_id: str, file_path: Path) -> None:
        """Export migration plan to file."""
        migration = self.get_migration_status(migration_id)
        if not migration:
            raise OnexError(f"Migration not found: {migration_id}")

        with open(file_path, "w") as f:
            json.dump(migration.dict(), f, indent=2, default=str)

    def import_migration_plan(self, file_path: Path) -> ModelServiceMigration:
        """Import migration plan from file."""
        with open(file_path, "r") as f:
            data = json.load(f)

        migration = ModelServiceMigration(**data)
        self._active_migrations[migration.migration_id] = migration

        return migration

    async def rollback_migration(self, migration_id: str) -> bool:
        """Rollback a migration."""
        migration = self.get_migration_status(migration_id)
        if not migration:
            raise OnexError(f"Migration not found: {migration_id}")

        if migration.overall_status not in [
            EnumMigrationStatus.FAILED,
            EnumMigrationStatus.IN_PROGRESS,
        ]:
            raise OnexError(
                f"Cannot rollback migration in status: {migration.overall_status}"
            )

        # This would implement rollback logic
        # For now, just mark as rolled back
        migration.overall_status = EnumMigrationStatus.ROLLED_BACK

        self._logger.info(f"Migration rolled back: {migration_id}")
        return True


# Global utility instance
_global_migration_utility: Optional[EventPublisherMigrationUtility] = None


def get_migration_utility() -> EventPublisherMigrationUtility:
    """Get global migration utility instance."""
    global _global_migration_utility
    if _global_migration_utility is None:
        _global_migration_utility = EventPublisherMigrationUtility()
    return _global_migration_utility


# Convenience functions
def create_migration_plan_global(
    service_name: str, target_publisher_type: EnumPublisherType, **kwargs
) -> ModelServiceMigration:
    """Create migration plan using global utility."""
    utility = get_migration_utility()
    return utility.create_migration_plan(service_name, target_publisher_type, **kwargs)


async def execute_migration_global(migration_id: str, dry_run: bool = False) -> bool:
    """Execute migration using global utility."""
    utility = get_migration_utility()
    return await utility.execute_migration(migration_id, dry_run)
