# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract hot-loading records: frozen, extra-forbidden, required fields per category (OMN-21226).

Every model refuses an unknown field and a missing field of its category's required
set. The required set of each model is spelled out here, so making a required field
optional in a model fails both the missing-field case and the set comparison.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_contract_hotload_operation import (
    EnumContractHotloadOperation,
)
from omnibase_core.enums.enum_contract_hotload_reason import EnumContractHotloadReason
from omnibase_core.enums.enum_contract_hotload_status import EnumContractHotloadStatus
from omnibase_core.enums.enum_contract_load_outcome import EnumContractLoadOutcome
from omnibase_core.models.events.contract_hotload.model_contract_hotload_accepted import (
    ModelContractHotloadAccepted,
)
from omnibase_core.models.events.contract_hotload.model_contract_hotload_applied import (
    ModelContractHotloadApplied,
)
from omnibase_core.models.events.contract_hotload.model_contract_hotload_removed import (
    ModelContractHotloadRemoved,
)
from omnibase_core.models.events.contract_hotload.model_contract_load_reply import (
    ModelContractLoadReply,
)
from omnibase_core.models.events.contract_hotload.model_contract_load_request import (
    ModelContractLoadRequest,
)
from omnibase_core.models.events.contract_hotload.model_contract_revision import (
    ModelContractRevision,
)
from omnibase_core.models.events.contract_hotload.model_hotload_name_state import (
    ModelHotloadNameState,
)
from omnibase_core.models.events.contract_hotload.model_hotload_observed_entry import (
    ModelHotloadObservedEntry,
)
from omnibase_core.models.events.contract_hotload.model_prune_completion import (
    ModelPruneCompletion,
)
from omnibase_core.models.events.contract_hotload.model_prune_request import (
    ModelPruneRequest,
)
from omnibase_core.models.events.contract_hotload.model_registry_watermark import (
    REGISTRY_WATERMARK_ENTITY_ID,
    ModelRegistryWatermark,
)
from omnibase_core.models.events.contract_hotload.model_runtime_hotload_state import (
    ModelRuntimeHotloadState,
)

HASH = "a" * 64
YAML = "name: node_example\n"
RT_ID = "3b4c5d6e-7f80-4a91-b2c3-d4e5f6a7b8c9"
REQ_ID = "6f1c1a0e-7d57-4b0e-9a55-0c1d2e3f4a51"
INC_ID = "8a2b3c4d-1e2f-4a5b-8c6d-7e8f9a0b1c2d"
RETIRED_ID = "0d9c8b7a-6e5f-4d3c-8b2a-1f0e9d8c7b6a"
NOW = datetime(2026, 11, 3, 6, 0, tzinfo=UTC)

# category -> (model, valid control fields)
CASES: dict[str, tuple[type[BaseModel], dict[str, Any]]] = {
    "request": (
        ModelContractLoadRequest,
        {
            "operation": "register",
            "contract_name": "node_example",
            "content_hash": HASH,
            "registration_request_id": REQ_ID,
            "expected_version": 0,
            "owner": "principal-a",
        },
    ),
    "registry_state_accepted": (
        ModelContractHotloadAccepted,
        {
            "entity_id": "node_example",
            "registry_version": 1,
            "content_hash": HASH,
            "operation": "register",
            "owner": "principal-a",
            "registration_request_id": REQ_ID,
            "contract_yaml": YAML,
        },
    ),
    "registry_state_removed": (
        ModelContractHotloadRemoved,
        {
            "entity_id": "node_example",
            "registry_version": 3,
            "content_hash": HASH,
            "operation": "remove",
            "owner": "principal-a",
            "registration_request_id": REQ_ID,
        },
    ),
    "reply": (
        ModelContractLoadReply,
        {
            "entity_id": f"principal-a:{REQ_ID}",
            "outcome": "accepted",
            "reason": None,
            "registry_version": 1,
        },
    ),
    "prune_request": (
        ModelPruneRequest,
        {
            "entity_id": "prune-1",
            "candidates": [
                {
                    "topic": "onex.evt.platform.example.v1",
                    "end_offsets": [{"partition": 0, "end_offset": 12}],
                    "consumer_groups": ["group-a"],
                }
            ],
            "inventory_digest": "digest-1",
        },
    ),
    "prune_completion": (
        ModelPruneCompletion,
        {
            "entity_id": "prune-1",
            "results": [
                {
                    "topic": "onex.evt.platform.example.v1",
                    "status": "retired",
                    "retired_topic_id": RETIRED_ID,
                }
            ],
        },
    ),
    "registry_record_revision": (
        ModelContractRevision,
        {
            "entity_id": f"node_example@{HASH}",
            "contract_yaml": YAML,
            "registry_version": 1,
        },
    ),
    "registry_record_watermark": (
        ModelRegistryWatermark,
        {
            "entity_id": REGISTRY_WATERMARK_ENTITY_ID,
            "committed_sequence": 7,
            "published_sequence": 6,
            "observed_at": NOW,
        },
    ),
    "runtime_event": (
        ModelContractHotloadApplied,
        {
            "entity_id": "node_example",
            "registry_version": 1,
            "content_hash": HASH,
            "operation": "register",
            "status": "materialized",
            "reason": None,
            "runtime_instance_id": RT_ID,
            "incarnation_id": INC_ID,
            "profile": "effects",
            "lane": "dev",
            "image_digest": "sha256:" + HASH,
        },
    ),
    "runtime_state": (
        ModelRuntimeHotloadState,
        {
            "entity_id": RT_ID,
            "incarnation_id": INC_ID,
            "profile": "effects",
            "lane": "dev",
            "image_digest": "sha256:" + HASH,
            "bootstrap_ready": True,
            "serving_ready": True,
            "names": {
                "node_example": {
                    "observed": {
                        "registry_version": 1,
                        "status": "materialized",
                        "reason": None,
                    },
                    "served": {"registry_version": 1, "content_hash": HASH},
                }
            },
        },
    ),
}

# The required set of each category, spelled out from the ticket and plan 3.2 (OMN-21226).
REQUIRED: dict[str, frozenset[str]] = {
    "request": frozenset(
        {
            "operation",
            "contract_name",
            "content_hash",
            "registration_request_id",
            "expected_version",
            "owner",
        }
    ),
    "registry_state_accepted": frozenset(
        {
            "entity_id",
            "registry_version",
            "content_hash",
            "operation",
            "owner",
            "registration_request_id",
            "contract_yaml",
        }
    ),
    "registry_state_removed": frozenset(
        {
            "entity_id",
            "registry_version",
            "content_hash",
            "operation",
            "owner",
            "registration_request_id",
        }
    ),
    "reply": frozenset({"entity_id", "outcome", "reason", "registry_version"}),
    "prune_request": frozenset({"entity_id", "candidates", "inventory_digest"}),
    "prune_completion": frozenset({"entity_id", "results"}),
    "registry_record_revision": frozenset(
        {"entity_id", "contract_yaml", "registry_version"}
    ),
    "registry_record_watermark": frozenset(
        {"entity_id", "committed_sequence", "published_sequence", "observed_at"}
    ),
    "runtime_event": frozenset(
        {
            "entity_id",
            "registry_version",
            "content_hash",
            "operation",
            "status",
            "reason",
            "runtime_instance_id",
            "incarnation_id",
            "profile",
            "lane",
            "image_digest",
        }
    ),
    "runtime_state": frozenset(
        {
            "entity_id",
            "incarnation_id",
            "profile",
            "lane",
            "image_digest",
            "bootstrap_ready",
            "serving_ready",
            "names",
        }
    ),
}

MISSING_FIELD_CASES = [
    pytest.param(category, field, id=f"{category}-{field}")
    for category in sorted(CASES)
    for field in sorted(REQUIRED[category])
]


@pytest.mark.unit
def test_every_category_has_a_case_and_a_required_set() -> None:
    assert set(CASES) == set(REQUIRED)


@pytest.mark.unit
@pytest.mark.parametrize("category", sorted(CASES))
def test_the_control_record_is_valid_and_round_trips(category: str) -> None:
    model, fields = CASES[category]
    record = model.model_validate(fields)
    assert model.model_validate_json(record.model_dump_json()) == record


@pytest.mark.unit
@pytest.mark.parametrize("category", sorted(CASES))
def test_the_required_set_is_exactly_the_categorys(category: str) -> None:
    model, _ = CASES[category]
    required = frozenset(
        name for name, info in model.model_fields.items() if info.is_required()
    )
    assert required == REQUIRED[category]


@pytest.mark.unit
@pytest.mark.parametrize("category", sorted(CASES))
def test_an_unknown_field_is_refused(category: str) -> None:
    model, fields = CASES[category]
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model.model_validate({**fields, "undeclared_field": "x"})


@pytest.mark.unit
@pytest.mark.parametrize(("category", "field"), MISSING_FIELD_CASES)
def test_a_missing_required_field_is_refused(category: str, field: str) -> None:
    model, fields = CASES[category]
    without = {k: v for k, v in fields.items() if k != field}
    with pytest.raises(ValidationError, match="Field required"):
        model.model_validate(without)


@pytest.mark.unit
@pytest.mark.parametrize("category", sorted(CASES))
def test_a_record_is_frozen(category: str) -> None:
    model, fields = CASES[category]
    record = model.model_validate(fields)
    with pytest.raises(ValidationError):
        setattr(record, "entity_id", "other")


@pytest.mark.unit
@pytest.mark.parametrize(
    "category",
    [
        "request",
        "registry_state_accepted",
        "registry_state_removed",
        "runtime_event",
    ],
)
@pytest.mark.parametrize(
    "bad_hash", ["", "A" * 64, "a" * 63, "a" * 65, "sha256:" + "a" * 64, "g" * 64]
)
def test_a_content_hash_off_the_canonical_form_is_refused(
    category: str, bad_hash: str
) -> None:
    model, fields = CASES[category]
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "content_hash": bad_hash})


@pytest.mark.unit
def test_the_operations_are_register_replace_remove() -> None:
    assert {o.value for o in EnumContractHotloadOperation} == {
        "register",
        "replace",
        "remove",
    }


@pytest.mark.unit
def test_the_reply_outcomes_are_accepted_rejected_unchanged_replayed() -> None:
    assert {o.value for o in EnumContractLoadOutcome} == {
        "accepted",
        "rejected",
        "unchanged",
        "replayed",
    }


@pytest.mark.unit
def test_the_statuses_are_those_of_plan_3_2() -> None:
    assert {s.value for s in EnumContractHotloadStatus} == {
        "materialized",
        "adopted",
        "replaced",
        "removed",
        "refused",
        "not_ready",
        "failed",
    }


@pytest.mark.unit
def test_an_outcome_outside_the_set_is_refused() -> None:
    model, fields = CASES["reply"]
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "outcome": "maybe"})


@pytest.mark.unit
def test_a_negative_registry_version_is_refused() -> None:
    model, fields = CASES["reply"]
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "registry_version": -1})


@pytest.mark.unit
def test_a_reply_reason_is_a_typed_token_or_none() -> None:
    model, fields = CASES["reply"]
    rejected = model.model_validate(
        {**fields, "outcome": "rejected", "reason": "VERSION_CONFLICT"}
    )
    assert isinstance(rejected, ModelContractLoadReply)
    assert rejected.reason is EnumContractHotloadReason.VERSION_CONFLICT
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "reason": "because"})


@pytest.mark.unit
def test_an_accepted_record_never_removes_and_a_removed_record_always_does() -> None:
    accepted, accepted_fields = CASES["registry_state_accepted"]
    removed, removed_fields = CASES["registry_state_removed"]
    for op in ("register", "replace"):
        accepted.model_validate({**accepted_fields, "operation": op})
    with pytest.raises(ValidationError):
        accepted.model_validate({**accepted_fields, "operation": "remove"})
    for op in ("register", "replace"):
        with pytest.raises(ValidationError):
            removed.model_validate({**removed_fields, "operation": op})


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_key", ["node_example", f"@{HASH}", "node_example@" + "a" * 63, "n@" + "A" * 64]
)
def test_a_revision_key_must_be_name_at_hash(bad_key: str) -> None:
    model, fields = CASES["registry_record_revision"]
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "entity_id": bad_key})


@pytest.mark.unit
def test_the_watermark_key_is_fixed_and_the_time_is_aware() -> None:
    model, fields = CASES["registry_record_watermark"]
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "entity_id": "another-key"})
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "observed_at": datetime(2026, 11, 3, 6, 0)})


@pytest.mark.unit
def test_the_runtime_state_carries_no_request_id() -> None:
    assert "registration_request_id" not in ModelRuntimeHotloadState.model_fields


@pytest.mark.unit
def test_a_refused_event_must_carry_a_reason() -> None:
    model, fields = CASES["runtime_event"]
    refused = model.model_validate(
        {**fields, "status": "refused", "reason": "PACKAGE_HASH_MISMATCH"}
    )
    assert isinstance(refused, ModelContractHotloadApplied)
    assert refused.status is EnumContractHotloadStatus.REFUSED
    assert refused.reason is EnumContractHotloadReason.PACKAGE_HASH_MISMATCH
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "status": "refused", "reason": None})
    with pytest.raises(ValidationError):
        model.model_validate({**fields, "reason": "because"})


@pytest.mark.unit
def test_a_state_after_a_removal_observes_removed_and_serves_nothing() -> None:
    state = ModelRuntimeHotloadState.model_validate(
        {
            **CASES["runtime_state"][1],
            "names": {
                "node_example": {
                    "observed": {
                        "registry_version": 3,
                        "status": "removed",
                        "reason": None,
                    },
                    "served": None,
                }
            },
        }
    )
    entry = state.names["node_example"]
    assert isinstance(entry, ModelHotloadNameState)
    assert entry.observed.status is EnumContractHotloadStatus.REMOVED
    assert entry.served is None


@pytest.mark.unit
def test_a_state_after_a_refused_replacement_observes_v2_and_serves_v1() -> None:
    state = ModelRuntimeHotloadState.model_validate(
        {
            **CASES["runtime_state"][1],
            "names": {
                "node_example": {
                    "observed": {
                        "registry_version": 2,
                        "status": "refused",
                        "reason": "PACKAGE_HASH_MISMATCH",
                    },
                    "served": {"registry_version": 1, "content_hash": HASH},
                }
            },
        }
    )
    entry = state.names["node_example"]
    assert isinstance(entry.observed, ModelHotloadObservedEntry)
    assert entry.observed.registry_version == 2
    assert entry.served is not None
    assert entry.served.registry_version == 1


@pytest.mark.unit
def test_a_nested_state_entry_refuses_an_unknown_field() -> None:
    fields = CASES["runtime_state"][1]
    bad = {
        **fields,
        "names": {
            "node_example": {
                **fields["names"]["node_example"],
                "undeclared_field": "x",
            }
        },
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ModelRuntimeHotloadState.model_validate(bad)
