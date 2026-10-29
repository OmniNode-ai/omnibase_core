# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""End-to-end tests for the event-registry drift check CLI (OMN-21416).

Each test writes real contract, registry and baseline files, runs the CLI the
way pre-commit and CI do, and reads the canonical report it writes. The cases
follow the failure modes written before the code: a registration present on
one side only, a topic/fan-out, partition key or required-fields mismatch, a
duplicate declaration, empty discovery, and a malformed or missing source
(which must be ERROR, never PASS).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.validator_event_registry_drift import (
    ValidatorEventDeclarationDrift,
)

pytestmark = pytest.mark.unit

_USAGE_TOPIC = "onex.evt.omnimarket.delegation-usage-call.v1"
_RUN_STEP_TOPIC = "onex.evt.omnimarket.delegation-run-step.v1"

_USAGE_CONTRACT = f"""\
topic: "{_USAGE_TOPIC}"
schema_version: "1.0.0"
producer:
  repo: omnimarket
  event_type: delegation.usage_call
required_fields:
  - name: call_id
    type: string
  - name: model_name
    type: string
  - name: tenant_id
    type: string
  - name: timestamp
    type: datetime
event_registration:
  partition_key_field: tenant_id
  fan_out:
    - topic: "{_USAGE_TOPIC}"
  required_fields: [call_id, model_name, tenant_id, timestamp]
"""

_RUN_STEP_CONTRACT = f"""\
topic: "{_RUN_STEP_TOPIC}"
schema_version: "1.0.0"
producer:
  repo: omnimarket
  event_type: delegation.run_step
required_fields:
  - name: tenant_id
    type: string
  - name: correlation_id
    type: uuid
  - name: step_sequence
    type: integer
event_registration:
  partition_key_field: correlation_id
  fan_out:
    - topic: "{_RUN_STEP_TOPIC}"
  required_fields: [tenant_id, correlation_id, step_sequence]
"""

_REGISTRY = f"""\
events:
  delegation.usage_call:
    partition_key_field: tenant_id
    required_fields: [call_id, model_name, tenant_id, timestamp]
    fan_out:
      - topic: {_USAGE_TOPIC}
  delegation.run_step:
    partition_key_field: correlation_id
    required_fields: [tenant_id, correlation_id, step_sequence]
    fan_out:
      - topic: {_RUN_STEP_TOPIC}
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _layout(
    tmp_path: Path,
    *,
    contracts: dict[str, str] | None = None,
    registry: str = _REGISTRY,
) -> tuple[Path, Path]:
    contract_dir = tmp_path / "wire"
    contract_dir.mkdir()
    for name, text in (
        contracts
        if contracts is not None
        else {"usage.yaml": _USAGE_CONTRACT, "run_step.yaml": _RUN_STEP_CONTRACT}
    ).items():
        _write(contract_dir / name, text)
    return contract_dir, _write(tmp_path / "topics.yaml", registry)


def _run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], *args: str
) -> tuple[int, dict[str, object]]:
    capsys.readouterr()
    exit_code = ValidatorEventDeclarationDrift.main(list(args))
    lines = [
        ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("ERROR")
    ]
    findings = [
        {"severity": "ERROR", "rule_id": ln.split("[", 1)[1].split("]", 1)[0]}
        for ln in lines
    ]
    return exit_code, {
        "overall_status": "ERROR" if findings else "PASS",
        "findings": findings,
    }


def _rule_ids(report: dict[str, object]) -> list[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return sorted(str(f["rule_id"]) for f in findings)


def _severities(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {str(f["severity"]) for f in findings}


def _check(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    contract_dir: Path,
    registry: Path,
    *extra: str,
):
    return _run(
        tmp_path,
        capsys,
        "--source-contracts",
        str(contract_dir),
        "--registry-topics-yaml",
        str(registry),
        *extra,
    )


def test_agreeing_sources_pass_with_zero_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(tmp_path)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 0
    assert report["overall_status"] == "PASS"
    assert report["findings"] == []


def test_required_field_order_is_not_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reordered = _REGISTRY.replace(
        "[call_id, model_name, tenant_id, timestamp]",
        "[timestamp, tenant_id, model_name, call_id]",
    )
    contract_dir, registry = _layout(tmp_path, registry=reordered)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert (exit_code, report["overall_status"]) == (0, "PASS")


def test_registration_missing_from_registry_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_text = _REGISTRY.split("  delegation.run_step:")[0]
    contract_dir, registry = _layout(tmp_path, registry=registry_text)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"
    assert "event_source_only" in _rule_ids(report)


def test_registration_missing_from_source_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(
        tmp_path, contracts={"usage.yaml": _USAGE_CONTRACT}
    )
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert "event_registry_only" in _rule_ids(report)


def test_topic_mismatch_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    other = "onex.evt.omnimarket.delegation-usage-call.v2"
    registry_text = _REGISTRY.replace(f"topic: {_USAGE_TOPIC}", f"topic: {other}")
    contract_dir, registry = _layout(tmp_path, registry=registry_text)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert "topics_mismatch" in _rule_ids(report)


def test_partition_key_mismatch_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_text = _REGISTRY.replace(
        "partition_key_field: tenant_id", "partition_key_field: call_id"
    )
    contract_dir, registry = _layout(tmp_path, registry=registry_text)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert _rule_ids(report) == ["partition_key_mismatch"]


def test_required_fields_mismatch_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_text = _REGISTRY.replace(
        "[call_id, model_name, tenant_id, timestamp]",
        "[call_id, model_name, tenant_id]",
    )
    contract_dir, registry = _layout(tmp_path, registry=registry_text)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert _rule_ids(report) == ["required_fields_mismatch"]


def test_duplicate_contract_declaration_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(
        tmp_path,
        contracts={
            "usage.yaml": _USAGE_CONTRACT,
            "usage_copy.yaml": _USAGE_CONTRACT,
            "run_step.yaml": _RUN_STEP_CONTRACT,
        },
    )
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_duplicate_registry_key_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    duplicated = (
        _REGISTRY + _REGISTRY.split("events:\n")[1].split("  delegation.run_step:")[0]
    )
    contract_dir, registry = _layout(tmp_path, registry=duplicated)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_no_contract_declares_a_registration_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = _USAGE_CONTRACT.split("event_registration:")[0]
    contract_dir, registry = _layout(tmp_path, contracts={"usage.yaml": plain})
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


@pytest.mark.parametrize(
    ("label", "broken"),
    [
        ("unparseable yaml", "topic: [unclosed\n"),
        ("not a mapping", "- a\n- b\n"),
        (
            "no producer event_type",
            _USAGE_CONTRACT.replace("  event_type: delegation.usage_call\n", ""),
        ),
        (
            "partition key not declared",
            _USAGE_CONTRACT.replace("  partition_key_field: tenant_id\n", ""),
        ),
        (
            "empty fan_out",
            _USAGE_CONTRACT.replace(
                f'  fan_out:\n    - topic: "{_USAGE_TOPIC}"\n', "  fan_out: []\n"
            ),
        ),
        (
            "contract topic not in fan_out",
            _USAGE_CONTRACT.replace(
                f'  fan_out:\n    - topic: "{_USAGE_TOPIC}"\n',
                '  fan_out:\n    - topic: "onex.evt.omnimarket.other.v1"\n',
            ),
        ),
        (
            "required field the wire contract does not declare",
            _USAGE_CONTRACT.replace(
                "[call_id, model_name, tenant_id, timestamp]",
                "[call_id, model_name, tenant_id, timestamp, undeclared]",
            ),
        ),
    ],
)
def test_malformed_contract_is_error_never_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], label: str, broken: str
) -> None:
    contract_dir, registry = _layout(
        tmp_path,
        contracts={"usage.yaml": broken, "run_step.yaml": _RUN_STEP_CONTRACT},
    )
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1, label
    assert report["overall_status"] == "ERROR", label
    assert _severities(report) == {"ERROR"}, label


def test_missing_registry_file_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, _ = _layout(tmp_path)
    exit_code, report = _check(tmp_path, capsys, contract_dir, tmp_path / "absent.yaml")
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_missing_contract_directory_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, registry = _layout(tmp_path)
    exit_code, report = _check(tmp_path, capsys, tmp_path / "no_such_dir", registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_registry_without_events_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(tmp_path, registry="events: {}\n")
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_baselined_registry_only_event_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(
        tmp_path, contracts={"usage.yaml": _USAGE_CONTRACT}
    )
    baseline = _write(
        tmp_path / "baseline.txt",
        "# intentional\nevent_registry_only delegation.run_step\nregistry_only "
        f"{_RUN_STEP_TOPIC}\n",
    )
    exit_code, report = _check(
        tmp_path, capsys, contract_dir, registry, "--baseline", str(baseline)
    )
    assert (exit_code, report["overall_status"]) == (0, "PASS")


def test_malformed_baseline_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(tmp_path)
    baseline = _write(tmp_path / "baseline.txt", "not_a_kind delegation.run_step\n")
    exit_code, report = _check(
        tmp_path, capsys, contract_dir, registry, "--baseline", str(baseline)
    )
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_registration_document_joins_contract_sources(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(
        tmp_path, contracts={"usage.yaml": _USAGE_CONTRACT}
    )
    document = _write(
        tmp_path / "hook_registrations.yaml",
        "event_registrations:\n"
        "  - event_type: delegation.run_step\n"
        "    topics: [" + _RUN_STEP_TOPIC + "]\n"
        "    partition_key_field: correlation_id\n"
        "    required_fields: [tenant_id, correlation_id, step_sequence]\n",
    )
    exit_code, report = _check(
        tmp_path, capsys, contract_dir, registry, "--source-document", str(document)
    )
    assert (exit_code, report["overall_status"]) == (0, "PASS")


def test_registration_in_both_contract_and_document_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(tmp_path)
    document = _write(
        tmp_path / "hook_registrations.yaml",
        "event_registrations:\n"
        "  - event_type: delegation.run_step\n"
        "    topics: [" + _RUN_STEP_TOPIC + "]\n"
        "    partition_key_field: correlation_id\n"
        "    required_fields: [tenant_id, correlation_id, step_sequence]\n",
    )
    exit_code, report = _check(
        tmp_path, capsys, contract_dir, registry, "--source-document", str(document)
    )
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


_RUN_STEP_DOCUMENT = (
    "event_registrations:\n"
    "  - event_type: delegation.run_step\n"
    "    topics: [" + _RUN_STEP_TOPIC + "]\n"
    "    partition_key_field: correlation_id\n"
    "    required_fields: [tenant_id, correlation_id, step_sequence]\n"
)


def test_missing_source_document_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(
        tmp_path, contracts={"usage.yaml": _USAGE_CONTRACT}
    )
    exit_code, report = _check(
        tmp_path,
        capsys,
        contract_dir,
        registry,
        "--source-document",
        str(tmp_path / "absent_registrations.yaml"),
    )
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_contract_directory_declaring_nothing_beside_a_document_is_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    plain = _USAGE_CONTRACT.split("event_registration:")[0]
    contract_dir, registry = _layout(tmp_path, contracts={"usage.yaml": plain})
    document = _write(
        tmp_path / "hook_registrations.yaml",
        _RUN_STEP_DOCUMENT
        + "  - event_type: delegation.usage_call\n"
        + "    topics: ["
        + _USAGE_TOPIC
        + "]\n"
        + "    partition_key_field: tenant_id\n"
        + "    required_fields: [call_id, model_name, tenant_id, timestamp]\n",
    )
    exit_code, report = _check(
        tmp_path, capsys, contract_dir, registry, "--source-document", str(document)
    )
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_unreadable_contract_file_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(tmp_path)
    (contract_dir / "undecodable.yaml").write_bytes(b"topic: \xff\xfe\xfd\n")
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_registry_fan_out_rule_without_a_topic_name_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_text = _REGISTRY.replace(
        f"      - topic: {_USAGE_TOPIC}\n",
        f"      - topic: {_USAGE_TOPIC}\n      - topic: 7\n",
    )
    contract_dir, registry = _layout(tmp_path, registry=registry_text)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_registry_required_field_that_is_not_a_name_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_text = _REGISTRY.replace(
        "[call_id, model_name, tenant_id, timestamp]",
        "[call_id, model_name, tenant_id, timestamp, 7]",
    )
    contract_dir, registry = _layout(tmp_path, registry=registry_text)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_contract_file_too_large_to_read_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_dir, registry = _layout(tmp_path)
    oversized = "# padding\n" * (6 * 1024 * 1024 // 10) + "topic: onex.evt.x.v1\n"
    _write(contract_dir / "oversized.yaml", oversized)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_registry_fan_out_repeating_a_topic_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_text = _REGISTRY.replace(
        f"      - topic: {_USAGE_TOPIC}\n",
        f"      - topic: {_USAGE_TOPIC}\n      - topic: {_USAGE_TOPIC}\n",
    )
    contract_dir, registry = _layout(tmp_path, registry=registry_text)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"


def test_registry_repeating_a_required_field_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_text = _REGISTRY.replace(
        "[call_id, model_name, tenant_id, timestamp]",
        "[call_id, model_name, tenant_id, timestamp, call_id]",
    )
    contract_dir, registry = _layout(tmp_path, registry=registry_text)
    exit_code, report = _check(tmp_path, capsys, contract_dir, registry)
    assert exit_code == 1
    assert report["overall_status"] == "ERROR"
