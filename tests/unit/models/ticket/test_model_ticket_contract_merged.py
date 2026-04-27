# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for merged ModelTicketContract schema (OMN-10064).

These tests verify the merged core ModelTicketContract after absorbing all
OCC-local fields (OMN-9582, Task 2). Xfail markers removed — implementation
is present and all tests should pass green.

Test inventory:
    T1 — New merged fields are accepted by the model
    T2 — schema_version rejects non-SemVer values
    T3 — interfaces_touched with interface_change=False raises ValidationError
    T4 — Existing fields are unaffected by the merge
    T5 — YAML round-trip preserves new merged fields
    T6 — On-disk YAML sample (OMN-6238.yaml fields) loads without error
"""

from __future__ import annotations

import textwrap

import pytest
from pydantic import ValidationError

from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

# ============================================================================
# T1 — New merged fields are accepted by the model
# ============================================================================


@pytest.mark.unit
def test_merged_fields_accepted() -> None:
    """ModelTicketContract accepts all new OCC-origin fields as typed model fields.

    Fields under test:
      schema_version, summary, is_seam_ticket, interface_change,
      interfaces_touched, evidence_requirements, emergency_bypass,
      golden_path, dod_evidence, contract_completeness.

    The post-merge model must store these as declared schema fields (present in
    ModelTicketContract.model_fields), not as raw extras in model_extra. In
    particular, emergency_bypass must be a ModelEmergencyBypass instance (not a
    dict), and contract_completeness must be an EnumContractCompleteness instance.
    """
    from omnibase_core.enums.enum_contract_completeness import (
        EnumContractCompleteness,
    )
    from omnibase_core.models.ticket.model_emergency_bypass import (
        ModelEmergencyBypass,
    )

    contract = ModelTicketContract(
        ticket_id="OMN-10062",
        title="Merged schema smoke test",
        schema_version="1.0.0",
        summary="Verify merged fields are accepted",
        is_seam_ticket=False,
        interface_change=False,
        interfaces_touched=[],
        evidence_requirements=[
            {
                "kind": "tests",
                "description": "Unit test coverage",
                "command": "uv run pytest tests/ -v",
            }
        ],
        emergency_bypass={
            "enabled": False,
            "justification": "",
            "follow_up_ticket_id": "",
        },
        golden_path=None,
        dod_evidence=[],
        contract_completeness="STUB",
    )

    # Fields must be declared schema fields, NOT raw extras
    declared_fields = ModelTicketContract.model_fields
    assert "schema_version" in declared_fields, (
        "schema_version must be a declared field, not stored in model_extra"
    )
    assert "summary" in declared_fields, (
        "summary must be a declared field, not stored in model_extra"
    )
    assert "is_seam_ticket" in declared_fields, (
        "is_seam_ticket must be a declared field, not stored in model_extra"
    )
    assert "interface_change" in declared_fields, (
        "interface_change must be a declared field, not stored in model_extra"
    )
    assert "interfaces_touched" in declared_fields, (
        "interfaces_touched must be a declared field, not stored in model_extra"
    )
    assert "evidence_requirements" in declared_fields, (
        "evidence_requirements must be a declared field, not stored in model_extra"
    )
    assert "emergency_bypass" in declared_fields, (
        "emergency_bypass must be a declared field, not stored in model_extra"
    )
    assert "dod_evidence" in declared_fields, (
        "dod_evidence must be a declared field, not stored in model_extra"
    )
    assert "contract_completeness" in declared_fields, (
        "contract_completeness must be a declared field, not stored in model_extra"
    )

    # emergency_bypass must be coerced to the typed model (not remain a raw dict)
    assert isinstance(contract.emergency_bypass, ModelEmergencyBypass), (
        f"emergency_bypass must be ModelEmergencyBypass, got {type(contract.emergency_bypass)}"
    )

    # contract_completeness must be an EnumContractCompleteness instance
    assert isinstance(contract.contract_completeness, EnumContractCompleteness), (
        f"contract_completeness must be EnumContractCompleteness, got {type(contract.contract_completeness)}"
    )
    assert contract.contract_completeness == EnumContractCompleteness.STUB

    # Basic value checks
    assert contract.schema_version == "1.0.0"
    assert contract.summary == "Verify merged fields are accepted"
    assert contract.is_seam_ticket is False
    assert contract.interface_change is False
    assert contract.interfaces_touched == []
    assert len(contract.evidence_requirements) == 1
    assert contract.golden_path is None
    assert contract.dod_evidence == []


# ============================================================================
# T2 — schema_version rejects non-SemVer values
# ============================================================================


@pytest.mark.unit
def test_schema_version_rejects_non_semver() -> None:
    """schema_version field must reject non-SemVer strings.

    Valid SemVer: major.minor.patch with no leading zeros (e.g. "1.0.0", "2.3.14").
    Rejected: "abc", "01.0.0", "1.0", "1.0.0-alpha", "".
    """
    invalid_versions = [
        "abc",
        "01.0.0",  # Leading zero in major
        "1.0",  # Missing patch segment
        "1.0.0-alpha",  # Pre-release suffix not supported
        "1.0.0+build",  # Build metadata not supported
        "",  # Empty string
    ]

    for bad_version in invalid_versions:
        with pytest.raises(ValidationError, match="schema_version"):
            ModelTicketContract(
                ticket_id="OMN-TEST",
                title="SemVer rejection test",
                schema_version=bad_version,
                summary="",
                is_seam_ticket=False,
                interface_change=False,
                emergency_bypass={
                    "enabled": False,
                    "justification": "",
                    "follow_up_ticket_id": "",
                },
            )


# ============================================================================
# T3 — interfaces_touched with interface_change=False raises ValidationError
# ============================================================================


@pytest.mark.unit
def test_interfaces_touched_requires_interface_change_true() -> None:
    """interfaces_touched must be empty when interface_change=False.

    Cross-field validator from OCC ported to core: if interface_change is False
    and interfaces_touched is non-empty, raise ValidationError.
    """
    with pytest.raises(ValidationError):
        ModelTicketContract(
            ticket_id="OMN-TEST",
            title="Interface constraint test",
            schema_version="1.0.0",
            summary="",
            is_seam_ticket=False,
            interface_change=False,
            interfaces_touched=["events"],  # Non-empty with interface_change=False
            emergency_bypass={
                "enabled": False,
                "justification": "",
                "follow_up_ticket_id": "",
            },
        )


# ============================================================================
# T4 — Existing fields are unaffected by the merge
# ============================================================================


@pytest.mark.unit
def test_existing_fields_unaffected() -> None:
    """All existing core ModelTicketContract fields continue to work after merge.

    Checks: ticket_id, title, description, phase, context, questions,
    requirements, verification_steps, gates, interfaces_provided,
    interfaces_consumed, contract_fingerprint, created_at, updated_at.

    Also checks that extra='forbid' is now in effect (post-merge schema change).
    """
    contract = ModelTicketContract(
        ticket_id="OMN-EXISTING",
        title="Existing fields check",
        description="A description",
        phase="intake",  # type: ignore[arg-type]
        context={"key": "value"},
        questions=[],
        requirements=[],
        verification_steps=[],
        gates=[],
        interfaces_provided=[],
        interfaces_consumed=[],
    )

    assert contract.ticket_id == "OMN-EXISTING"
    assert contract.title == "Existing fields check"
    assert contract.description == "A description"
    assert contract.context == {"key": "value"}
    assert contract.questions == []
    assert contract.requirements == []
    assert contract.verification_steps == []
    assert contract.gates == []
    assert contract.interfaces_provided == []
    assert contract.interfaces_consumed == []

    # Post-merge: extra="forbid" must be in effect
    with pytest.raises(ValidationError):
        ModelTicketContract.model_validate(
            {
                "ticket_id": "OMN-EXTRA",
                "title": "Extra field test",
                "schema_version": "1.0.0",
                "summary": "",
                "is_seam_ticket": False,
                "interface_change": False,
                "emergency_bypass": {
                    "enabled": False,
                    "justification": "",
                    "follow_up_ticket_id": "",
                },
                "unknown_extra_field": "should_be_rejected",
            }
        )


# ============================================================================
# T5 — YAML round-trip preserves new merged fields
# ============================================================================


@pytest.mark.unit
def test_yaml_round_trip_preserves_merged_fields() -> None:
    """Merged fields survive a to_yaml() → from_yaml() round-trip.

    Constructs a ModelTicketContract with the new fields set to non-default
    values, serializes to YAML, deserializes back, and asserts all new fields
    are preserved with their original values.
    """
    original = ModelTicketContract(
        ticket_id="OMN-ROUNDTRIP",
        title="Round-trip test",
        schema_version="1.0.0",
        summary="Testing YAML round-trip of merged fields",
        is_seam_ticket=True,
        interface_change=True,
        interfaces_touched=["events", "topics"],
        evidence_requirements=[
            {
                "kind": "tests",
                "description": "Round-trip evidence",
                "command": "uv run pytest",
            }
        ],
        emergency_bypass={
            "enabled": False,
            "justification": "",
            "follow_up_ticket_id": "",
        },
        golden_path=None,
        dod_evidence=[
            {
                "id": "dod-001",
                "description": "Test exists",
                "source": "generated",
                "checks": [
                    {
                        "check_type": "test_passes",
                        "check_value": "tests/unit/models/ticket/",
                    }
                ],
                "status": "pending",
            }
        ],
        contract_completeness="ENRICHED",
    )

    yaml_str = original.to_yaml()
    restored = ModelTicketContract.from_yaml(yaml_str)

    # All new fields must survive round-trip
    assert restored.schema_version == "1.0.0"
    assert restored.summary == "Testing YAML round-trip of merged fields"
    assert restored.is_seam_ticket is True
    assert restored.interface_change is True
    assert len(restored.interfaces_touched) == 2
    assert len(restored.evidence_requirements) == 1
    assert restored.emergency_bypass is not None
    assert restored.emergency_bypass.enabled is False
    assert len(restored.dod_evidence) == 1
    assert restored.dod_evidence[0].id == "dod-001"
    assert restored.contract_completeness.value == "ENRICHED"

    # Existing fields also survive
    assert restored.ticket_id == "OMN-ROUNDTRIP"
    assert restored.title == "Round-trip test"


# ============================================================================
# T6 — On-disk YAML sample (OMN-6238.yaml fields) loads without error
# ============================================================================


@pytest.mark.unit
def test_on_disk_yaml_sample_loads() -> None:
    """Representative OMN-6238.yaml on-disk contract loads against core model.

    Uses a verbatim copy of the OMN-6238.yaml fields from
    onex_change_control/contracts/OMN-6238.yaml (observed 2026-04-27).
    After the merge, core ModelTicketContract must accept this exact structure.
    """
    omn_6238_yaml = textwrap.dedent(
        """\
        schema_version: "1.0.0"
        ticket_id: OMN-6238
        summary: "Build Contract-Driven Multi-Repo Verification Agents"
        is_seam_ticket: true
        interface_change: false
        interfaces_touched: []
        evidence_requirements:
          - kind: "ci"
            description: "CI passes on merge PR"
            command: "gh pr checks"
        emergency_bypass:
          enabled: false
          justification: ""
          follow_up_ticket_id: ""
        dod_evidence:
          - id: "dod-001"
            description: "PR opened against main branch"
            source: "generated"
            checks:
              - check_type: "command"
                check_value: "gh pr view --json state -q .state"
          - id: "dod-002"
            description: "PR merged to main"
            source: "generated"
            checks:
              - check_type: "command"
                check_value: "gh pr view --json mergedAt -q .mergedAt"
          - id: "dod-003"
            description: "Tests pass in CI"
            source: "generated"
            checks:
              - check_type: "command"
                check_value: "gh pr checks --watch"
          - id: "dod-004"
            description: "Pre-commit hooks clean"
            source: "generated"
            checks:
              - check_type: "command"
                check_value: "pre-commit run --all-files"
          - id: "dod-005"
            description: "Contract/schema artifact file exists"
            source: "generated"
            checks:
              - check_type: "command"
                check_value: "contracts/OMN-6238.yaml"
        title: "Build Contract-Driven Multi-Repo Verification Agents"
        """
    )

    # The core model must accept this YAML without raising after the merge
    contract = ModelTicketContract.from_yaml(omn_6238_yaml)

    # Verify key fields round-tripped correctly
    assert contract.ticket_id == "OMN-6238"
    assert contract.schema_version == "1.0.0"
    assert contract.summary == "Build Contract-Driven Multi-Repo Verification Agents"
    assert contract.is_seam_ticket is True
    assert contract.interface_change is False
    assert contract.interfaces_touched == []
    assert len(contract.evidence_requirements) == 1
    assert contract.emergency_bypass is not None
    assert contract.emergency_bypass.enabled is False
    assert len(contract.dod_evidence) == 5
    assert contract.dod_evidence[0].id == "dod-001"
