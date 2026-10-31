# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the two contract hashes of the merge engine (OMN-21506, T-C4).

``compute_resolver_config_hash`` and ``compute_effective_contract_hash`` are the
one definition of the resolver-configuration hash and the effective-contract
hash. The merge engine calls them, carries them in its started and completed
events and returns them with the merge result.
"""

from __future__ import annotations

import ast
import builtins
import os
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.contracts import contract_merge_hashes
from omnibase_core.contracts.contract_merge_hashes import (
    compute_effective_contract_hash,
    compute_resolver_config_hash,
)
from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
from omnibase_core.factories.factory_contract_profile import ContractProfileFactory
from omnibase_core.merge.contract_merge_engine import ContractMergeEngine
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.events.contract_validation import (
    ModelContractMergeCompletedEvent,
    ModelContractMergeStartedEvent,
)
from omnibase_core.models.merge.model_contract_merge_result import (
    ModelContractMergeResult,
)
from omnibase_core.models.merge.model_overlay_ref import ModelOverlayRef
from omnibase_core.models.merge.model_overlay_stack_entry import ModelOverlayStackEntry
from omnibase_core.models.primitives.model_semver import ModelSemVer


class RecordingEmitter:
    """Emitter that records the merge lifecycle events the engine emits."""

    def __init__(self) -> None:
        self.started: list[ModelContractMergeStartedEvent] = []
        self.completed: list[ModelContractMergeCompletedEvent] = []

    def emit_merge_started(self, event: ModelContractMergeStartedEvent) -> None:
        self.started.append(event)

    def emit_merge_completed(self, event: ModelContractMergeCompletedEvent) -> None:
        self.completed.append(event)

    def emit_validation_started(self, event: Any) -> None:
        pass

    def emit_validation_passed(self, event: Any) -> None:
        pass

    def emit_validation_failed(self, event: Any) -> None:
        pass


def _patch(description: str = "Hash test handler") -> ModelContractPatch:
    return ModelContractPatch(
        extends=ModelProfileReference(profile="compute_pure", version="1.0.0"),
        name="hash_test_handler",
        node_version=ModelSemVer(major=1, minor=0, patch=0),
        description=description,
    )


def _overlay(version: str = "1.0.0") -> ModelOverlayStackEntry:
    return ModelOverlayStackEntry(
        overlay_id="org-defaults",
        overlay_patch=_patch(),
        scope=EnumOverlayScope.ORG,
        version=version,
    )


def _engine(emitter: RecordingEmitter | None = None) -> ContractMergeEngine:
    return ContractMergeEngine(ContractProfileFactory(), event_emitter=emitter)


def _ref(version: str = "1.0.0") -> ModelOverlayRef:
    return ModelOverlayRef(
        overlay_id="org-defaults",
        version=version,
        scope=EnumOverlayScope.ORG,
        order_index=0,
    )


@pytest.mark.unit
class TestHashEquivalence:
    """AC1: equal for equivalent inputs; each hash moves only with its own input."""

    def test_equivalent_resolver_configs_hash_equal(self) -> None:
        first = compute_resolver_config_hash(
            profile="compute_pure",
            profile_version="1.0.0",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            overlay_refs=[_ref()],
        )
        second = compute_resolver_config_hash(
            profile="compute_pure",
            profile_version="1.0.0",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            overlay_refs=(_ref(),),
        )
        assert first == second
        assert first.startswith("sha256:")
        assert len(first) == len("sha256:") + 64

    def test_equivalent_effective_contracts_hash_equal(self) -> None:
        first = _engine().resolve(_patch())
        second = _engine().resolve(_patch())
        reloaded = type(first.contract).model_validate(
            first.contract.model_dump(mode="json")
        )
        assert first.contract is not second.contract
        assert first.effective_contract_hash == second.effective_contract_hash
        assert compute_effective_contract_hash(reloaded) == (
            first.effective_contract_hash
        )
        assert first.effective_contract_hash.startswith("sha256:")

    def test_changed_resolver_config_changes_only_resolver_config_hash(self) -> None:
        engine = _engine()
        before = engine.resolve(_patch(), overlays=[_overlay("1.0.0")])
        after = engine.resolve(_patch(), overlays=[_overlay("2.0.0")])
        assert before.contract == after.contract
        assert before.effective_contract_hash == after.effective_contract_hash
        assert before.resolver_config_hash != after.resolver_config_hash

    def test_changed_effective_contract_changes_effective_contract_hash(self) -> None:
        engine = _engine()
        before = engine.resolve(_patch("first description"))
        after = engine.resolve(_patch("second description"))
        assert before.resolver_config_hash == after.resolver_config_hash
        assert before.effective_contract_hash != after.effective_contract_hash


@pytest.mark.unit
class TestEngineCarriesHashes:
    """AC2: the events and the merge result carry both hashes."""

    def test_events_and_result_carry_both_hashes(self) -> None:
        emitter = RecordingEmitter()
        engine = _engine(emitter)
        result = engine.resolve(_patch(), overlays=[_overlay()])

        assert isinstance(result, ModelContractMergeResult)
        assert len(emitter.started) == 1
        assert len(emitter.completed) == 1
        assert result.resolver_config_hash is not None
        assert result.effective_contract_hash is not None
        assert emitter.started[0].resolver_config_hash == result.resolver_config_hash
        assert (
            emitter.completed[0].effective_contract_hash
            == result.effective_contract_hash
        )

    def test_merge_and_merge_with_overlays_events_carry_both_hashes(self) -> None:
        emitter = RecordingEmitter()
        engine = _engine(emitter)
        engine.merge(_patch())
        engine.merge_with_overlays(_patch(), [_overlay()])

        assert len(emitter.started) == 2
        assert len(emitter.completed) == 2
        assert all(e.resolver_config_hash is not None for e in emitter.started)
        assert all(e.effective_contract_hash is not None for e in emitter.completed)

    def test_result_hashes_match_the_contract_and_overlays_it_returns(self) -> None:
        result = _engine().resolve(_patch(), overlays=[_overlay()])
        assert result.overlay_refs == [_ref()]
        assert result.effective_contract_hash == compute_effective_contract_hash(
            result.contract
        )


@pytest.mark.unit
class TestNoDeploymentValue:
    """AC3: a core library carries no deployment value."""

    def test_hash_module_imports_no_environment_or_file_reader(self) -> None:
        tree = ast.parse(Path(contract_merge_hashes.__file__).read_text())
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not imported & {"os", "pathlib", "yaml", "dotenv", "subprocess"}
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        assert not names & {"open", "getenv", "environ"}

    def test_hashing_reads_no_overlay_file_and_no_environment_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        result = _engine().resolve(_patch(), overlays=[_overlay()])

        def refuse(*args: object, **kwargs: object) -> None:
            raise AssertionError("hashing touched a file or the environment")

        class RefusingEnviron(dict[str, str]):
            def __getitem__(self, key: str) -> str:
                refuse()
                return ""

            def get(self, key: str, default: Any = None) -> Any:
                refuse()

        monkeypatch.setattr(builtins, "open", refuse)
        monkeypatch.setattr(os, "environ", RefusingEnviron())
        monkeypatch.setattr(os, "getenv", refuse)

        assert (
            compute_resolver_config_hash(
                profile="compute_pure",
                profile_version="1.0.0",
                node_type=EnumNodeType.COMPUTE_GENERIC,
                overlay_refs=result.overlay_refs,
            )
            == result.resolver_config_hash
        )
        assert (
            compute_effective_contract_hash(result.contract)
            == result.effective_contract_hash
        )


@pytest.mark.unit
class TestInProcessParity:
    """AC4: the same inputs hash the same in a direct call and through the engine.

    The parity harness (T-B2) is not built; the engine's in-process ``resolve``
    entry stands in for the local in-process entry until it is.
    """

    def test_direct_call_and_engine_entry_agree_byte_for_byte(self) -> None:
        result = _engine().resolve(_patch(), overlays=[_overlay("3.1.4")])

        direct_resolver = compute_resolver_config_hash(
            profile="compute_pure",
            profile_version="1.0.0",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            overlay_refs=[_ref("3.1.4")],
        )
        direct_effective = compute_effective_contract_hash(result.contract)

        assert result.resolver_config_hash.encode() == direct_resolver.encode()
        assert result.effective_contract_hash.encode() == direct_effective.encode()
