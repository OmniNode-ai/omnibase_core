# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-23758: the schema 1.1.0 standard form, its ModelTicketDraft source, and
the timestamp-stable contract fingerprint."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, get_args, get_origin

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_proof_class import EnumProofClass
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

FIELD_MISSING = "TICKET_STANDARD_FORM_FIELD_MISSING"
TICKET_ID_PATTERN = "TICKET_STANDARD_FORM_TICKET_ID_PATTERN"
DOD_MISSING = "TICKET_STANDARD_FORM_DOD_EVIDENCE_MISSING"
FALSIFIER_MISSING = "TICKET_STANDARD_FORM_CRITERION_FALSIFIER_MISSING"
INTEGRATION_RULE = "DOD_EVIDENCE_INTEGRATION_ITEM_MISSING"
TITLE_EMPTY = "TICKET_STANDARD_FORM_TITLE_EMPTY"

_STANDARD_FORM: dict = {
    "schema_version": "1.1.0",
    "ticket_id": "OMN-90001",
    "title": "A standard ticket",
    "summary": "s",
    "proof_class": "deployed",
    "business_brief": {
        "what_this_is": "a",
        "why_it_matters": "b",
        "done_looks_like": "c",
        "risk": "d",
        "depends_on": "e",
    },
    "parent_ticket_id": "OMN-90000",
    "parent_ac_label": "AC1",
    "repository": "omnibase_core",
    "requirements": [
        {
            "id": "REQ-1",
            "statement": "r",
            "acceptance": [
                {
                    "id": "AC1",
                    "statement": "unit",
                    "falsifier": "uv run pytest tests/x.py",
                    "integrated": False,
                },
                {
                    "id": "AC2",
                    "statement": "running",
                    "falsifier": "onex validate on the dev lane",
                    "integrated": True,
                },
            ],
        }
    ],
    "dod_evidence": [
        {
            "id": "dod-001",
            "description": "unit",
            "binds_ac": ["AC1"],
            "checks": [{"check_type": "test_passes", "check_value": "tests/x.py"}],
        },
        {
            "id": "dod-002",
            "description": "running",
            "binds_ac": ["AC2"],
            "checks": [{"check_type": "endpoint", "check_value": "http://host/health"}],
        },
    ],
}

FIELDS_1_0_0 = (
    "schema_version",
    "summary",
    "is_seam_ticket",
    "interface_change",
    "interfaces_touched",
    "evidence_requirements",
    "emergency_bypass",
    "golden_path",
    "dod_evidence",
    "contract_completeness",
    "proof_class",
    "ticket_id",
    "title",
    "description",
    "phase",
    "context",
    "questions",
    "requirements",
    "verification_steps",
    "gates",
    "interfaces_provided",
    "interfaces_consumed",
    "contract_fingerprint",
    "created_at",
    "updated_at",
)


def _without_none(annotation: object) -> object:
    """The annotation with ``| None`` and ``Annotated`` metadata set aside."""
    if get_origin(annotation) is Annotated:
        return _without_none(get_args(annotation)[0])
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if (
        get_origin(annotation) is not None
        and len(args) == 1
        and (get_origin(annotation) is not list)
    ):
        return _without_none(args[0])
    return annotation


def standard_form_data() -> dict:
    """A fresh deep copy of the 1.1.0 standard form."""
    return copy.deepcopy(_STANDARD_FORM)


def draft_kwargs() -> dict:
    """The standard form content without schema_version and ticket_id."""
    data = standard_form_data()
    del data["schema_version"]
    del data["ticket_id"]
    return data


def _all_unit_criteria(data: dict) -> None:
    for ac in data["requirements"][0]["acceptance"]:
        ac["integrated"] = False


@pytest.mark.unit
def test_brief_required_positive_control_validates() -> None:
    contract = ModelTicketContract.model_validate(standard_form_data())
    assert contract.schema_version == "1.1.0"
    assert contract.title == "A standard ticket"
    assert contract.proof_class == EnumProofClass.DEPLOYED


@pytest.mark.unit
def test_brief_required_refuses_missing_business_brief() -> None:
    data = standard_form_data()
    del data["business_brief"]
    with pytest.raises(ValidationError, match=FIELD_MISSING) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "business_brief" in str(excinfo.value)


@pytest.mark.unit
@pytest.mark.parametrize(
    "heading",
    ["what_this_is", "why_it_matters", "done_looks_like", "risk", "depends_on"],
)
def test_brief_required_refuses_missing_brief_heading(heading: str) -> None:
    data = standard_form_data()
    del data["business_brief"][heading]
    with pytest.raises(ValidationError) as excinfo:
        ModelTicketContract.model_validate(data)
    assert heading in str(excinfo.value)


@pytest.mark.unit
def test_integration_item_required_refuses_unit_bound_integrated() -> None:
    data = standard_form_data()
    data["dod_evidence"][1]["checks"] = [
        {"check_type": "test_passes", "check_value": "tests/x.py"}
    ]
    with pytest.raises(ValidationError, match=INTEGRATION_RULE) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "AC2" in str(excinfo.value)


@pytest.mark.unit
def test_integration_item_required_refuses_all_unit_criteria() -> None:
    data = standard_form_data()
    _all_unit_criteria(data)
    with pytest.raises(ValidationError, match=INTEGRATION_RULE) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "AC1" in str(excinfo.value)
    assert "AC2" in str(excinfo.value)


@pytest.mark.unit
def test_integration_item_required_refuses_unbound_integrated() -> None:
    data = standard_form_data()
    data["dod_evidence"] = [data["dod_evidence"][0]]
    with pytest.raises(ValidationError, match=INTEGRATION_RULE) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "AC2" in str(excinfo.value)


@pytest.mark.unit
def test_integration_item_required_refuses_no_integration() -> None:
    data = standard_form_data()
    data["proof_class"] = None
    _all_unit_criteria(data)
    with pytest.raises(ValidationError, match=INTEGRATION_RULE) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "AC2" in str(excinfo.value)


@pytest.mark.unit
def test_integration_item_required_accepts_code_only_with_unit_checks() -> None:
    data = standard_form_data()
    data["proof_class"] = "code-only"
    _all_unit_criteria(data)
    data["dod_evidence"][1]["checks"] = [
        {"check_type": "test_passes", "check_value": "tests/x.py"}
    ]
    contract = ModelTicketContract.model_validate(data)
    assert contract.proof_class == EnumProofClass.CODE_ONLY


@pytest.mark.unit
def test_integration_item_required_accepts_valid_fixture() -> None:
    contract = ModelTicketContract.model_validate(standard_form_data())
    assert contract.dod_evidence[1].checks[0].check_type == "endpoint"


@pytest.mark.unit
def test_integration_item_required_accepts_behavior_proven_integration() -> None:
    data = standard_form_data()
    data["dod_evidence"][1]["checks"] = [
        {"check_type": "behavior_proven", "check_value": "true"}
    ]
    contract = ModelTicketContract.model_validate(data)
    assert contract.dod_evidence[1].checks[0].check_type == "behavior_proven"


@pytest.mark.unit
def test_from_draft_builds_contract_from_draft() -> None:
    from omnibase_core.models.ticket.model_ticket_draft import ModelTicketDraft

    draft = ModelTicketDraft.model_validate(draft_kwargs())
    contract = ModelTicketContract.from_draft(draft, "OMN-90002")
    assert isinstance(contract, ModelTicketContract)
    assert contract.ticket_id == "OMN-90002"
    assert contract.schema_version == "1.1.0"
    for name in ModelTicketDraft.model_fields:
        assert getattr(draft, name) == getattr(contract, name), name
    assert contract.contract_fingerprint == contract.compute_fingerprint()
    assert len(contract.contract_fingerprint) == 16
    assert all(ch in "0123456789abcdef" for ch in contract.contract_fingerprint)


@pytest.mark.unit
def test_from_draft_field_annotations_cannot_drift() -> None:
    from omnibase_core.models.ticket.model_ticket_draft import ModelTicketDraft

    for name in ModelTicketDraft.model_fields:
        assert name in ModelTicketContract.model_fields, name
        contract_field = ModelTicketContract.model_fields[name]
        draft_field = ModelTicketDraft.model_fields[name]
        # The contract keeps the six 1.1.0 fields optional so 1.0.0 files load;
        # the draft requires them. Same type once None is set aside.
        assert _without_none(contract_field.annotation) == _without_none(
            draft_field.annotation
        ), name


@pytest.mark.unit
def test_from_draft_refuses_draft_without_business_brief() -> None:
    from omnibase_core.models.ticket.model_ticket_draft import ModelTicketDraft

    kwargs = draft_kwargs()
    del kwargs["business_brief"]
    with pytest.raises(ValidationError) as excinfo:
        ModelTicketDraft.model_validate(kwargs)
    assert "business_brief" in str(excinfo.value)


@pytest.mark.unit
def test_from_draft_refuses_non_matching_ticket_id() -> None:
    from omnibase_core.models.ticket.model_ticket_draft import ModelTicketDraft

    draft = ModelTicketDraft.model_validate(draft_kwargs())
    with pytest.raises(ValidationError, match=TICKET_ID_PATTERN):
        ModelTicketContract.from_draft(draft, "ABC-1")


@pytest.mark.unit
def test_from_draft_refuses_deployed_draft_without_integrated_criterion() -> None:
    from omnibase_core.models.ticket.model_ticket_draft import ModelTicketDraft

    kwargs = draft_kwargs()
    _all_unit_criteria(kwargs)
    draft = ModelTicketDraft.model_validate(kwargs)
    with pytest.raises(ValidationError, match=INTEGRATION_RULE):
        ModelTicketContract.from_draft(draft, "OMN-90003")


@pytest.mark.unit
@pytest.mark.parametrize(
    "field", ["business_brief", "parent_ticket_id", "parent_ac_label", "repository"]
)
def test_section_1a_kept_refuses_missing_required_field(field: str) -> None:
    data = standard_form_data()
    del data[field]
    with pytest.raises(ValidationError, match=FIELD_MISSING) as excinfo:
        ModelTicketContract.model_validate(data)
    assert field in str(excinfo.value)


@pytest.mark.unit
def test_section_1a_kept_refuses_empty_repository() -> None:
    data = standard_form_data()
    data["repository"] = ""
    with pytest.raises(ValidationError, match=FIELD_MISSING) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "repository" in str(excinfo.value)


@pytest.mark.unit
def test_section_1a_kept_refuses_criterion_without_falsifier() -> None:
    data = standard_form_data()
    del data["requirements"][0]["acceptance"][0]["falsifier"]
    with pytest.raises(ValidationError, match=FALSIFIER_MISSING) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "falsifier" in str(excinfo.value)


@pytest.mark.unit
def test_section_1a_kept_refuses_criterion_without_integrated() -> None:
    data = standard_form_data()
    del data["requirements"][0]["acceptance"][0]["integrated"]
    with pytest.raises(ValidationError, match=FIELD_MISSING) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "integrated" in str(excinfo.value)


@pytest.mark.unit
def test_section_1a_kept_refuses_empty_dod_evidence() -> None:
    data = standard_form_data()
    data["dod_evidence"] = []
    with pytest.raises(ValidationError, match=DOD_MISSING) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "dod_evidence" in str(excinfo.value)


@pytest.mark.unit
@pytest.mark.parametrize("ticket_id", ["ABC-1", "OMN-", "omn-12", "OMN-12x"])
def test_section_1a_kept_refuses_malformed_ticket_ids(ticket_id: str) -> None:
    data = standard_form_data()
    data["ticket_id"] = ticket_id
    with pytest.raises(ValidationError, match=TICKET_ID_PATTERN) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "ticket_id" in str(excinfo.value)


@pytest.mark.unit
@pytest.mark.parametrize("title", ["", "   "])
def test_section_1a_kept_refuses_empty_or_whitespace_title(title: str) -> None:
    data = standard_form_data()
    data["title"] = title
    with pytest.raises(ValidationError, match=TITLE_EMPTY) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "title" in str(excinfo.value)


@pytest.mark.unit
def test_section_1a_kept_refuses_non_matching_parent_ticket_id() -> None:
    data = standard_form_data()
    data["parent_ticket_id"] = "nope"
    with pytest.raises(ValidationError, match=TICKET_ID_PATTERN) as excinfo:
        ModelTicketContract.model_validate(data)
    assert "parent_ticket_id" in str(excinfo.value)


@pytest.mark.unit
def test_section_1a_kept_keeps_optional_start_probe_and_diagnosis() -> None:
    contract = ModelTicketContract.model_validate(standard_form_data())
    assert contract.start_probe is None
    assert contract.diagnosis is None
    data = standard_form_data()
    data["start_probe"] = "probe text"
    data["diagnosis"] = "diagnosis text"
    contract = ModelTicketContract.model_validate(data)
    assert contract.start_probe == "probe text"
    assert contract.diagnosis == "diagnosis text"


@pytest.mark.unit
def test_section_1a_kept_keeps_every_1_0_0_field_name() -> None:
    for name in FIELDS_1_0_0:
        assert name in ModelTicketContract.model_fields, name


@pytest.mark.unit
@pytest.mark.parametrize(
    "data",
    [
        {"ticket_id": "OMN-90001", "title": "A minimal 1.0.0 contract"},
        {
            "schema_version": "1.0.0",
            "ticket_id": "OMN-90001",
            "title": "A minimal 1.0.0 contract",
        },
    ],
)
def test_section_1a_kept_accepts_minimal_1_0_0_contracts(data: dict) -> None:
    contract = ModelTicketContract.model_validate(data)
    assert contract.schema_version == "1.0.0"


@pytest.mark.unit
def test_section_1a_kept_accepts_real_contract_file() -> None:
    path = Path(__file__).resolve().parents[4] / "contracts" / "OMN-10278.yaml"
    raw = path.read_text(encoding="utf-8")
    assert isinstance(yaml.safe_load(raw), dict)
    contract = ModelTicketContract.from_yaml(raw)
    assert contract.ticket_id == "OMN-10278"
    assert contract.schema_version == "1.0.0"


@pytest.mark.unit
def test_fingerprint_recomputes_matches_stored_value() -> None:
    contract = ModelTicketContract.model_validate(standard_form_data())
    contract.update_fingerprint()
    assert contract.compute_fingerprint() == contract.contract_fingerprint


@pytest.mark.unit
def test_fingerprint_recomputes_survives_yaml_round_trip() -> None:
    contract = ModelTicketContract.model_validate(standard_form_data())
    contract.update_fingerprint()
    round_trip = ModelTicketContract.from_yaml(contract.to_yaml())
    assert round_trip.compute_fingerprint() == round_trip.contract_fingerprint


@pytest.mark.unit
def test_fingerprint_recomputes_survives_later_updated_at() -> None:
    contract = ModelTicketContract.model_validate(standard_form_data())
    contract.update_fingerprint()
    contract.updated_at = datetime(2099, 1, 1, tzinfo=UTC)
    assert contract.compute_fingerprint() == contract.contract_fingerprint


@pytest.mark.unit
def test_fingerprint_is_contract_hash_ignores_timestamps() -> None:
    a = ModelTicketContract.model_validate(standard_form_data())
    a.created_at = datetime(2020, 1, 1, tzinfo=UTC)
    a.updated_at = datetime(2021, 1, 1, tzinfo=UTC)
    b = ModelTicketContract.model_validate(standard_form_data())
    b.created_at = datetime(2030, 1, 1, tzinfo=UTC)
    b.updated_at = datetime(2031, 1, 1, tzinfo=UTC)
    assert a.compute_fingerprint() == b.compute_fingerprint()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        ("title", "A different title"),
        ("summary", "a different summary"),
        ("business_brief.risk", "a different risk"),
        ("criterion.falsifier", "a different falsifier"),
        ("repository", "another_repository"),
        ("proof_class", EnumProofClass.LIVE_READBACK),
    ],
)
def test_fingerprint_is_contract_hash_changes_with_content(
    field_path,
    value,
) -> None:
    altered = standard_form_data()
    if field_path in ("title", "summary", "repository", "proof_class"):
        altered[field_path] = value
    elif field_path == "business_brief.risk":
        altered["business_brief"]["risk"] = value
    elif field_path == "criterion.falsifier":
        altered["requirements"][0]["acceptance"][0]["falsifier"] = value
    a = ModelTicketContract.model_validate(standard_form_data())
    b = ModelTicketContract.model_validate(altered)
    assert a.compute_fingerprint() != b.compute_fingerprint()


@pytest.mark.unit
def test_fingerprint_is_contract_hash_ignores_stored_fingerprint() -> None:
    contract = ModelTicketContract.model_validate(standard_form_data())
    expected = contract.compute_fingerprint()
    contract.contract_fingerprint = "0" * 16
    assert contract.compute_fingerprint() == expected


@pytest.mark.unit
def test_fingerprint_is_contract_hash_is_sha256_of_canonical_dump() -> None:
    contract = ModelTicketContract.model_validate(standard_form_data())
    expected = hashlib.sha256(
        json.dumps(
            contract.model_dump(
                mode="json",
                exclude={"contract_fingerprint", "created_at", "updated_at"},
            ),
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()[:16]
    assert contract.compute_fingerprint() == expected


@pytest.mark.unit
def test_fingerprint_recomputes_on_a_1_0_0_contract() -> None:
    """The base's reason: update_fingerprint() moved updated_at after the hash."""
    contract = ModelTicketContract(ticket_id="OMN-90001", title="A 1.0.0 contract")
    contract.update_fingerprint()
    assert contract.compute_fingerprint() == contract.contract_fingerprint


@pytest.mark.unit
def test_fingerprint_is_contract_hash_on_a_1_0_0_contract_ignores_timestamps() -> None:
    """The base's reason: created_at and updated_at were inside the hash."""
    a = ModelTicketContract(ticket_id="OMN-90001", title="A 1.0.0 contract")
    b = a.model_copy(
        update={
            "created_at": datetime(2030, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2031, 1, 1, tzinfo=UTC),
        }
    )
    assert a.compute_fingerprint() == b.compute_fingerprint()


@pytest.mark.unit
def test_section_1a_kept_accepts_the_1_1_0_fixture_file() -> None:
    """The fixture the dev-lane reading validates: written by from_draft, read back."""
    path = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "ticket_standard_form"
        / "ticket_contract_1_1_0.yaml"
    )
    contract = ModelTicketContract.from_yaml(path.read_text(encoding="utf-8"))
    assert contract.schema_version == "1.1.0"
    assert contract.contract_fingerprint == contract.compute_fingerprint()


def test_dev_lane_fixture_validates_through_yaml_entry_point() -> None:
    """OMN-23758 AC8: a 1.1.0 fixture validates through the YAML entry point."""
    contract = ModelTicketContract.from_yaml(
        yaml.safe_dump(standard_form_data(), sort_keys=False)
    )
    assert str(contract.schema_version) == "1.1.0"
    assert contract.business_brief is not None
