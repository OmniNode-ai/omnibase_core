# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CI/pre-commit adapter for the shared-token COMPUTE node over the local bus."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.container.container_auto_config import local_event_bus
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.event_bus.util_consumer_group import derive_service_group_id
from omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract import (
    ModelEventBusSubcontract,
)
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.runtime.model_operational_timeouts import packaged_timeouts
from omnibase_core.models.validation.model_shared_token_allowlist import (
    ModelSharedTokenAllowlist,
)
from omnibase_core.models.validation.model_shared_token_policy_request import (
    ModelSharedTokenPolicyRequest,
)
from omnibase_core.models.validation.model_shared_token_policy_result import (
    ModelSharedTokenPolicyResult,
)
from omnibase_core.nodes.node_backend_secret_discipline_compute.handler_shared_token_policy import (
    HandlerSharedTokenPolicyCompute,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates


def _read(paths: list[Path]) -> dict[str, str]:
    """Read every named YAML file through the existing gather EFFECT."""
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=[str(path) for path in paths],
            include_patterns=["**/*.yml", "**/*.yaml"],
        )
    )
    if output.skipped or len(output.files) != len(paths):
        raise ModelOnexError(
            message="one or more policy inputs could not be read",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return {file.path: file.source for file in output.files}


async def run_policy(
    request: ModelSharedTokenPolicyRequest, *, bus: EventBusInmemory | None = None
) -> ModelSharedTokenPolicyResult:
    """Dispatch a typed request and consume its result on contract-declared topics."""
    contract_path = (
        Path(__file__).parents[1]
        / "node_backend_secret_discipline_compute"
        / "contract.yaml"
    )
    raw = load_yaml_mapping_no_duplicates(
        _read([contract_path])[str(contract_path)], source="secret-discipline contract"
    )
    contract = ModelEventBusSubcontract.model_validate(raw["event_bus"])
    (command_topic,) = contract.subscribe_topics
    (result_topic,) = contract.publish_topics
    transport = bus if bus is not None else local_event_bus()
    results: asyncio.Queue[ModelSharedTokenPolicyResult] = asyncio.Queue(maxsize=1)

    async def on_command(message: ModelEventMessage) -> None:
        payload = ModelSharedTokenPolicyRequest.model_validate_json(message.value)
        result = HandlerSharedTokenPolicyCompute().handle(payload)
        await transport.publish(result_topic, None, result.model_dump_json().encode())

    async def on_result(message: ModelEventMessage) -> None:
        await results.put(
            ModelSharedTokenPolicyResult.model_validate_json(message.value)
        )

    await transport.start()
    try:
        await transport.subscribe(
            command_topic,
            on_message=on_command,
            group_id=derive_service_group_id(
                "shared_token_policy_compute", service="omnibase_core"
            ),
        )
        await transport.subscribe(
            result_topic,
            on_message=on_result,
            group_id=derive_service_group_id(
                "shared_token_policy_result", service="omnibase_core"
            ),
        )
        await transport.publish(command_topic, None, request.model_dump_json().encode())
        return await asyncio.wait_for(
            results.get(),
            timeout=packaged_timeouts().shared_token_policy_response_seconds,
        )
    finally:
        await transport.shutdown()


def main(argv: list[str] | None = None) -> int:
    """Scan all workflows even when pre-commit was triggered by one changed file."""
    parser = argparse.ArgumentParser(
        description="Refuse unreviewed shared GitHub token use"
    )
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root)
    paths = sorted(
        path
        for path in (root / ".github/workflows").glob("*")
        if path.suffix in {".yml", ".yaml"}
    )
    if not paths:
        sys.stderr.write("shared-token-policy: no workflows found\n")
        return 1
    policy_path = (
        root
        / "src/omnibase_core/nodes/node_backend_secret_discipline_compute/contract.yaml"
    )
    try:
        sources = _read(paths)
        if policy_path.exists():
            policy_contract = load_yaml_mapping_no_duplicates(
                _read([policy_path])[str(policy_path)],
                source="secret-discipline policy",
            )
            allowlist = ModelSharedTokenAllowlist.model_validate(
                policy_contract["shared_token_policy"]
            ).model_dump_json()
        else:
            allowlist = "entries: []\n"
        request = ModelSharedTokenPolicyRequest(
            workflows={
                str(Path(path).relative_to(root)): source
                for path, source in sources.items()
            },
            allowlist=allowlist,
        )
        result = asyncio.run(run_policy(request))
    except (
        OSError,
        ValueError,
        KeyError,
        ValidationError,
        yaml.YAMLError,
        TimeoutError,
        ModelOnexError,
    ):
        # Do not echo source text or parser exceptions into CI logs.
        sys.stderr.write(
            "shared-token-policy: unreadable input or missing bus result\n"
        )
        return 1
    for error in result.errors:
        sys.stderr.write(f"shared-token-policy: {error}\n")
    for use in result.violations:
        sys.stderr.write(
            f"{use.workflow}:{use.location}: {use.reference} requires a reviewed exception\n"
        )
    if result.passed:
        sys.stdout.write(
            f"shared-token-policy: PASS ({len(paths)} workflows, {len(result.uses)} reviewed uses)\n"
        )
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
