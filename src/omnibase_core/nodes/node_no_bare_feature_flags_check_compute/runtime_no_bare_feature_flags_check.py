# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the no-bare-feature-flags hook (OMN-20074, OMN-21518).

Reads the named files through the source-file gather EFFECT, loads the rule rows of
``no_bare_feature_flags.validation.yaml``, hands both to ``HandlerNoBareFeatureFlags``
and prints one line per violation and the closing summary. A named path that cannot be
read is skipped without a message, as in the source. Usage::

    python -m omnibase_core.nodes.node_no_bare_feature_flags_check_compute.runtime_no_bare_feature_flags_check [files...]

Exit code 0 = clean. Exit code 1 = violations found.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.bare_feature_flag_check.model_bare_feature_flag_check_input import (
    ModelBareFeatureFlagCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_no_bare_feature_flags_check_compute.handler_no_bare_feature_flags import (
    HandlerNoBareFeatureFlags,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.checker_no_bare_feature_flags import (
    RULE_SUMMARY,
    load_rules,
)
from omnibase_core.validation.checker_rule_parameters import rule_string
from omnibase_core.validation.validator_no_bare_feature_flags import (
    ValidatorNoBareFeatureFlags,
)

__all__ = ["main", "summary"]


_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN = cast(
    "type[NodeSourceFileGatherEffect]", NodeSourceFileGatherEffect
)
_HANDLER_NO_BARE_FEATURE_FLAGS_TOKEN = cast(
    "type[HandlerNoBareFeatureFlags]", HandlerNoBareFeatureFlags
)


def summary(
    contract: ModelValidatorSubcontract, violations: int, exemptions: Sequence[str]
) -> str:
    """The closing lines after the violations: their count and the listed exemptions."""
    row = next(rule for rule in contract.rules if rule.rule_id == RULE_SUMMARY)
    listed = ""
    if exemptions:
        listed = rule_string(row, "exemptions_template").format(
            count=len(exemptions),
            listing=rule_string(row, "listing_separator").join(exemptions),
        )
    return rule_string(row, "summary_template").format(
        count=violations, exemptions=listed
    )


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN, NodeSourceFileGatherEffect),
        (_HANDLER_NO_BARE_FEATURE_FLAGS_TOKEN, HandlerNoBareFeatureFlags),
    ):
        run_coro_sync(
            registry.register_service(
                token,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def main(
    argv: Sequence[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Run the CLI with container-resolved services."""
    owned = container is None
    if container is None:
        container = build_container()
    try:
        return _run(argv, container)
    finally:
        if owned:
            container.close()


def _run(argv: Sequence[str] | None, container: ModelONEXContainer) -> int:
    """Run the exported hook on the given files, or command-line arguments."""
    paths = list(sys.argv[1:] if argv is None else argv)
    if not paths:
        return 0
    contract = ValidatorNoBareFeatureFlags().contract
    gathered = container.get_service(_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN).handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=paths,
            include_patterns=["**/*"],
            decode_errors="replace",
        )
    )
    # The source skips a path it cannot read without a message, so
    # gathered.skipped is deliberately not reported.
    report = container.get_service(_HANDLER_NO_BARE_FEATURE_FLAGS_TOKEN).handle(
        ModelBareFeatureFlagCheckInput(
            rules=load_rules(contract),
            files=[
                ModelSourceFile(path=f.path, source=f.source) for f in gathered.files
            ],
        )
    )
    violations = [f.message for f in report.findings if f.severity == "FAIL"]
    exemptions = [f.message for f in report.findings if f.severity == "SKIP"]
    if violations:
        for violation in violations:
            sys.stdout.write(f"{violation}\n")
        sys.stdout.write(summary(contract, len(violations), exemptions))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
