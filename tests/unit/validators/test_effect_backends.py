# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The effect-backends validator lists every effect node without an in-memory default (OMN-22911).

The list is the input of the piece 4 reading (plan section 3.6, the two-backend rule): an effect
node has an in-memory default and a real backend chosen by an overlay key, both declared in its
contract under ``backends``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.validation.model_effect_backends_load_request import (
    ModelEffectBackendsLoadRequest,
)
from omnibase_core.models.validation.model_effect_backends_request import (
    ModelEffectBackendsRequest,
)
from omnibase_core.models.validation.model_effect_contract_document import (
    ModelEffectContractDocument,
)
from omnibase_core.nodes.node_effect_backends_check_compute.handler_effect_backends import (
    HandlerEffectBackends,
)
from omnibase_core.nodes.node_effect_backends_check_compute.handler_effect_backends_loader import (
    HandlerEffectBackendsLoader,
)

pytestmark = pytest.mark.unit

BOTH = {
    "default": "in_memory",
    "in_memory": {"factory": "pkg.mem.make_store"},
    "real": {"factory": "pkg.real.make_store", "overlay_key": "store_backend"},
}


def doc(
    name: str, node_type: str = "effect", backends: object = None
) -> ModelEffectContractDocument:
    body: dict[str, object] = {"node_name": name, "node_type": node_type}
    if backends is not None:
        body["backends"] = backends
    return ModelEffectContractDocument(path=f"{name}/contract.yaml", document=body)


def report(*docs: ModelEffectContractDocument):
    return HandlerEffectBackends().handle(
        ModelEffectBackendsRequest(contracts=tuple(docs))
    )


def test_effect_without_backends_is_listed() -> None:
    result = report(doc("node_a_effect"))
    assert result.without_in_memory_default == ("node_a_effect",)
    assert result.not_on_both == ("node_a_effect",)
    assert result.effects_total == 1


def test_effect_with_both_backends_is_not_listed() -> None:
    result = report(doc("node_b_effect", backends=BOTH))
    assert result.without_in_memory_default == ()
    assert result.not_on_both == ()
    assert result.on_both == ("node_b_effect",)


def test_in_memory_only_has_a_default_but_is_not_on_both() -> None:
    only_memory = {k: v for k, v in BOTH.items() if k != "real"}
    result = report(doc("node_c_effect", backends=only_memory))
    assert result.without_in_memory_default == ()
    assert result.not_on_both == ("node_c_effect",)


def test_real_backend_without_overlay_key_is_not_on_both() -> None:
    no_overlay = {**BOTH, "real": {"factory": "pkg.real.make_store"}}
    result = report(doc("node_d_effect", backends=no_overlay))
    assert result.not_on_both == ("node_d_effect",)
    assert result.without_in_memory_default == ()


def test_default_other_than_in_memory_is_listed() -> None:
    result = report(doc("node_e_effect", backends={**BOTH, "default": "real"}))
    assert result.without_in_memory_default == ("node_e_effect",)


def test_in_memory_default_with_no_factory_is_listed() -> None:
    result = report(
        doc("node_f_effect", backends={**BOTH, "in_memory": {"factory": " "}})
    )
    assert result.without_in_memory_default == ("node_f_effect",)


def test_compute_node_is_not_an_effect() -> None:
    result = report(doc("node_g_compute", node_type="compute"))
    assert result.effects_total == 0
    assert result.without_in_memory_default == ()


def test_list_is_sorted_and_counts_agree() -> None:
    result = report(
        doc("node_z_effect"),
        doc("node_b_effect", backends=BOTH),
        doc("node_m_effect"),
    )
    assert result.without_in_memory_default == ("node_m_effect", "node_z_effect")
    assert result.not_on_both_count == 2
    assert result.effects_total == 3


def test_loader_reads_contract_files_and_reports_unreadable(tmp_path: Path) -> None:
    good = tmp_path / "node_h_effect"
    good.mkdir()
    (good / "contract.yaml").write_text(
        yaml.safe_dump({"node_name": "node_h_effect", "node_type": "effect"})
    )
    bad = tmp_path / "node_i_effect"
    bad.mkdir()
    (bad / "contract.yaml").write_text("node_type: [unclosed")
    loaded = HandlerEffectBackendsLoader().handle(
        ModelEffectBackendsLoadRequest(root=str(tmp_path))
    )
    result = HandlerEffectBackends().handle(
        ModelEffectBackendsRequest(
            contracts=loaded.documents, unreadable=loaded.unreadable
        )
    )
    assert result.without_in_memory_default == ("node_h_effect",)
    assert [Path(p).parent.name for p in result.unreadable] == ["node_i_effect"]
