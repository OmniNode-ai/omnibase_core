# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Auditable owner/disposition mapping for every current raw-env reader path.

This is not an exception mechanism: ``no_new_os_environ`` still reports every
raw access as a violation. The inventory makes the approved migration backlog
explicit and fails its audit if a new reader path has no named disposition or
if a migrated path remains listed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final

from omnibase_core.models.validation.model_environment_reader_inventory_assignment import (
    ModelEnvironmentReaderInventoryAssignment,
)

__all__ = [
    "READER_INVENTORY_BY_PATH",
    "ModelEnvironmentReaderInventoryAssignment",
    "inventory_key",
    "stale_inventory_paths",
    "unassigned_reader_paths",
]


_TYPED_BOOTSTRAP_INJECTION: Final = ModelEnvironmentReaderInventoryAssignment(
    owner="OMN-17744",
    disposition="migrate-to-typed-bootstrap-injection",
)
_READER_PATHS: Final[frozenset[str]] = frozenset(
    {
        "examples/demo/handlers/support_assistant/handler_anthropic.py",
        "examples/demo/handlers/support_assistant/handler_local.py",
        "examples/demo/handlers/support_assistant/handler_openai.py",
        "examples/demo/handlers/support_assistant/model_config.py",
        "scripts/check_hook_bits_drift.py",
        "scripts/ci/canonical_handler_shape.py",
        "scripts/ci/check_occ_companion_merged.py",
        "scripts/ci/detect_test_paths.py",
        "scripts/ci/parity_replay.py",
        "scripts/ci/rsd_provenance_stamp.py",
        "scripts/ci/test_selection_shadow.py",
        "scripts/ci/verify_flip_bundle.py",
        "scripts/generate_llm_refs.py",
        "scripts/hooks/prepush_override_grant.py",
        "scripts/hooks/pytest_full_suite_host_guard.py",
        "scripts/run_cross_repo_validation.py",
        "scripts/validate_deterministic_skill_routing.py",
        "scripts/zone_diff_filter.py",
        "src/omnibase_core/artifacts/artifact_store.py",
        "src/omnibase_core/cli/cli_commands.py",
        "src/omnibase_core/cli/cli_hooks.py",
        "src/omnibase_core/cli/cli_run_node.py",
        "src/omnibase_core/cli/cli_runtime_host.py",
        "src/omnibase_core/constants/constants_effect.py",
        "src/omnibase_core/constants/constants_workflow.py",
        "src/omnibase_core/contracts/runtime_contracts.py",
        "src/omnibase_core/doctor/checks/check_env_vars.py",
        "src/omnibase_core/doctor/checks/check_kafka.py",
        "src/omnibase_core/doctor/checks/check_linear.py",
        "src/omnibase_core/doctor/checks/check_repos_synced.py",
        "src/omnibase_core/doctor/checks/check_stale_worktrees.py",
        "src/omnibase_core/enums/enum_hook_bit.py",
        "src/omnibase_core/event_bus/util_consumer_group.py",
        "src/omnibase_core/feature_flags/registry.py",
        "src/omnibase_core/infrastructure/node_config_provider.py",
        "src/omnibase_core/logging/logging_emit.py",
        "src/omnibase_core/mixins/mixin_effect_execution.py",
        "src/omnibase_core/mixins/mixin_introspection.py",
        "src/omnibase_core/mixins/mixin_node_id_from_contract.py",
        "src/omnibase_core/models/configuration/model_database_connection_config.py",
        "src/omnibase_core/models/configuration/model_database_secure_config.py",
        "src/omnibase_core/models/configuration/model_event_bus_config.py",
        "src/omnibase_core/models/configuration/model_rest_api_connection_config.py",
        "src/omnibase_core/models/container/model_onex_container.py",
        "src/omnibase_core/models/contracts/subcontracts/model_tool_execution_subcontract.py",
        "src/omnibase_core/models/dispatch/model_lifecycle_chain.py",
        "src/omnibase_core/models/event_bus/model_event_bus_input_state.py",
        "src/omnibase_core/models/infrastructure/model_environment_variables.py",
        "src/omnibase_core/models/plan/model_plan_contract.py",
        "src/omnibase_core/models/runtime/model_runtime_aliveness_probe.py",
        "src/omnibase_core/models/security/model_secret_backend.py",
        "src/omnibase_core/models/security/model_secure_credentials.py",
        "src/omnibase_core/models/services/model_node_service_config.py",
        "src/omnibase_core/models/ticket/model_ticket_contract.py",
        "src/omnibase_core/models/validation/model_envelope_validation_config.py",
        "src/omnibase_core/models/workflow/execution/model_workflow_state_snapshot.py",
        "src/omnibase_core/overlays/contract_env_ref.py",
        "src/omnibase_core/runtime/golden_chain/record_guard.py",
        "src/omnibase_core/runtime/runtime_local_adapter.py",
        "src/omnibase_core/utils/util_omni_home_paths.py",
        "src/omnibase_core/utils/util_ticket_workflow_persistence.py",
        "src/omnibase_core/validation/pin_hygiene/runtime_pin_hygiene.py",
        "src/omnibase_core/validation/validator_skill_backing_node.py",
        "src/omnibase_core/validators/no_unguarded_git_subprocess.py",
        "tests/analysis/test_consumer_graph.py",
        "tests/ci/test_workflow_uses_refs_resolve.py",
        "tests/conftest.py",
        "tests/fixtures/validation/exports/star_import.py",
        "tests/fixtures/validation/exports/syntax_error.py",
        "tests/gates/test_consumer_group_name_authorization.py",
        "tests/integration/ci/test_workflow_uses_refs_resolve_live.py",
        "tests/integration/examples/demo/handlers/support_assistant/conftest.py",
        "tests/integration/examples/demo/handlers/support_assistant/test_handler_integration.py",
        "tests/integration/models/agents/test_agent_yaml_validation.py",
        "tests/integration/test_validation_integration.py",
        "tests/performance/conftest.py",
        "tests/scripts/test_check_release_identity.py",
        "tests/scripts/test_deterministic_skills_hook_omni_home_preflight.py",
        "tests/scripts/test_prepush_actor_fallback.py",
        "tests/scripts/test_prepush_hook_host_identity_guard.py",
        "tests/scripts/test_prepush_hook_recursion_and_env_guard.py",
        "tests/scripts/test_prepush_host_table.py",
        "tests/scripts/test_prepush_remote_leg_policy.py",
        "tests/scripts/test_propagate_config.py",
        "tests/scripts/test_pytest_full_suite_host_guard.py",
        "tests/scripts/test_semantic_diff_cli.py",
        "tests/scripts/test_zone_diff_filter.py",
        "tests/unit/artifacts/test_artifact_store.py",
        "tests/unit/cli/substrate_gates/fixtures/env_clean.py",
        "tests/unit/cli/substrate_gates/fixtures/env_violation.py",
        "tests/unit/cli/test_cli_hooks.py",
        "tests/unit/cli/test_runtime_host_cli.py",
        "tests/unit/concurrency/conftest.py",
        "tests/unit/contracts/test_get_runtime_contracts_dir.py",
        "tests/unit/gate/test_diff_hash.py",
        "tests/unit/mixins/test_mixin_effect_execution.py",
        "tests/unit/mixins/test_mixin_node_service_shutdown.py",
        "tests/unit/models/configuration/test_model_database_secure_config.py",
        "tests/unit/models/configuration/test_model_event_bus_config.py",
        "tests/unit/models/event_bus/test_model_event_bus_input_state.py",
        "tests/unit/models/security/test_model_secure_credentials.py",
        "tests/unit/normalization/test_e2e_contract_validation.py",
        "tests/unit/scripts/ci/test_detect_test_paths_cli.py",
        "tests/unit/scripts/ci/test_omn16321_enums_proportionality.py",
        "tests/unit/scripts/ci/test_parity_replay.py",
        "tests/unit/scripts/ci/test_verify_flip_bundle.py",
        "tests/unit/scripts/test_gen_hook_bits_precommit.py",
        "tests/unit/services/replay/test_service_config_override_injector.py",
        "tests/unit/test_git_env_isolation.py",
        "tests/unit/validation/pin_hygiene/test_handler_pin_hygiene_compute.py",
        "tests/unit/validation/test_release_workflow_shape.py",
        "tests/unit/validation/test_validator_dispatch_report_anchors.py",
        "tests/unit/validators/test_pydantic_extra_forbid.py",
        "tests/validation/test_onex_state_disposable_gitignore.py",
    }
)
READER_INVENTORY_BY_PATH: Final[
    Mapping[str, ModelEnvironmentReaderInventoryAssignment]
] = MappingProxyType(dict.fromkeys(_READER_PATHS, _TYPED_BOOTSTRAP_INJECTION))


def inventory_key(path: Path) -> str:
    """Return a repository-relative, portable path key for an audited reader."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def unassigned_reader_paths(paths: Iterable[Path]) -> tuple[str, ...]:
    """Return reader paths with no owner/disposition assignment."""
    return tuple(
        sorted(
            {inventory_key(path) for path in paths} - READER_INVENTORY_BY_PATH.keys()
        )
    )


def stale_inventory_paths(paths: Iterable[Path]) -> tuple[str, ...]:
    """Return inventory entries no longer backed by a scanned raw reader."""
    return tuple(
        sorted(
            READER_INVENTORY_BY_PATH.keys() - {inventory_key(path) for path in paths}
        )
    )
