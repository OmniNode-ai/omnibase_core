# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalFileShapeRules -- rule parameters of the canonical-file-shape validator (OMN-21515).

Every field is a ``parameters`` entry of a rule row in
``validation/contracts/canonical_file_shape.validation.yaml``; the checker holds
no pattern, name list, path or remediation text of its own. ``extra="forbid"``
and the absence of defaults make a contract with an unknown or missing key fail
to load instead of passing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelCanonicalFileShapeRules(BaseModel):
    """The merged ``parameters`` of every rule row of the contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # noncanonical-file
    code_extensions: tuple[str, ...]
    canonical_src_dirs: tuple[str, ...]
    canonical_prefixed_dirs: tuple[str, ...]
    test_dirs: tuple[str, ...]
    docs_root: str
    always_canonical_names: tuple[str, ...]
    src_root: str
    shebang_prefix: str
    canonical_src_min_parts: int
    noncanonical_text: str
    shell_text: str
    baseline_path: str
    node_home_baseline_path: str
    baseline_header: str
    # baseline-stale, baseline-growth, baselined-file-growth
    baseline_stale_text: str
    baseline_growth_text: str
    comment_prefixes: tuple[str, ...]
    baselined_growth_text: str
    # burn-down baseline: burndown-baseline, burndown-ticket-missing, burndown-baseline-removed
    burndown_baseline_path: str
    burndown_baseline_header: str
    burndown_ticket_pattern: str
    burndown_ticket_missing_text: str
    burndown_stale_text: str
    burndown_growth_text: str
    burndown_removed_text: str
    # skill-imperative
    skill_file_name: str
    imperative_patterns: tuple[str, ...]
    skill_imperative_text: str
    # suppression-growth
    suppression_patterns: tuple[str, ...]
    config_extensions: tuple[str, ...]
    suppression_growth_text: str
    # new-exception-file, exception-entry-growth
    exception_name_pattern: str
    prose_extensions: tuple[str, ...]
    new_exception_text: str
    exception_growth_text: str
    # declared-gate-lists
    pre_commit_config_path: str
    hooks_manifest_path: str
    workflows_dir: str
    gate_hook_ids: tuple[str, ...]
    node_boundary_hook_name: str
    node_boundary_baseline: str
    model_config_hook_name: str
    model_config_baseline: str
    gate_repo_url_pattern: str
    guard_workflow_uses_pattern: str
    guard_allowlist_input: str
    # repository-lifecycle and its four finding rules
    lifecycle_path: str
    lifecycle_state_key: str
    lifecycle_states: tuple[str, ...]
    no_code_state: str
    fix_only_state: str
    retired_state: str
    release_trailer_key: str
    no_code_text: str
    fix_only_new_file_text: str
    fix_only_growth_text: str
    retired_text: str
    # handler_outside_node
    handler_file_prefix: str
    handler_class_pattern: str
    contract_file_name: str
    binding_handler_key: str
    binding_module_key: str
    binding_default_key: str
    handler_outside_node_text: str
    # cli_entry_outside_node
    argparse_pattern: str
    main_pattern: str
    node_runtime_prefix: str
    scripts_key_path: str
    cli_entry_outside_node_text: str
    # git-reader
    cat_file_timeout_s: float
    # node-home: new nodes belong in omnimarket unless the contract declares a category
    node_home_ignored_components: tuple[str, ...]
    node_home_hidden_prefix: str
    node_home_source_suffix: str
    node_home_handler_prefix: str
    node_home_node_file: str
    node_home_handlers_dir: str
    node_home_nodes_dir: str
    node_home_node_dir_prefix: str
    node_home_node_class_pattern: str
    node_home_admitted_field: str
    node_home_admitted_categories: tuple[str, ...]
    node_home_entry_point_path: tuple[str, ...]
    node_home_outside_market_text: str
    node_home_baseline_stale_text: str
    node_home_baseline_growth_text: str
    node_home_baseline_removed_text: str
    node_home_entry_point_text: str
