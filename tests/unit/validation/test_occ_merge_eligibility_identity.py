# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit goal identity validation for the shared OCC resolver (OMN-20070)."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import UUID

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_goal_attempt_status import EnumGoalAttemptStatus
from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason
from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
)
from omnibase_core.models.validation.model_goal_mutation_state import (
    ModelGoalMutationState,
)
from omnibase_core.models.validation.model_goal_verification_attempt import (
    ModelGoalVerificationAttempt,
)
from omnibase_core.models.validation.model_occ_eligibility_input import (
    ModelOccEligibilityInput,
)
from omnibase_core.models.validation.model_occ_eligibility_result import (
    ModelOccEligibilityResult,
)
from omnibase_core.validation.validator_occ_merge_eligibility import (
    validate_occ_merge_eligibility,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

GOAL_ID = UUID("747a3ba5-2ae9-4fa3-8c98-4d7475ce30c5")
CONTRACT_REVISION = UUID("00000000-0000-4000-8000-000000000001")
CONTRACT_SCHEMA_VERSION = "1.0.0"
SOURCE_COMMIT_SHA = "a" * 40
SOURCE_SHA256 = "sha256:" + "b" * 64
SUBJECT_COMMIT_SHA = "c" * 40
SUBJECT_TREE_SHA = "d" * 40
REPOSITORY = "OmniNode-ai/omnibase_core"
CONTRACT_RELATIVE_PATH = PurePosixPath("contracts/goals/example.yaml")
GOAL_ITEM_ID = "goal-contract-identity-proof"
GOAL_CHECK_TYPE = "command"
GOAL_CHECK_VALUE = "uv run pytest tests/unit/validation/test_identity.py -q"
PROTECTED_TEST_PATH = "tests/test_goal_criterion_baseline.py"
PROTECTED_TEST_BYTES = b"def test_goal_criterion_is_exercised():\n    assert True\n"


def _attempt_allocation(
    *,
    goal_id: UUID,
    repository: str,
    contract_revision: UUID,
    subject_commit_sha: str,
    subject_tree_sha: str,
    statuses: tuple[EnumGoalAttemptStatus, ...] = (EnumGoalAttemptStatus.PASS,),
) -> ModelGoalAttemptAllocationSnapshot:
    attempts = tuple(
        ModelGoalVerificationAttempt(
            goal_id=goal_id,
            repository=repository,
            contract_revision=contract_revision,
            subject_commit_sha=subject_commit_sha,
            subject_tree_sha=subject_tree_sha,
            attempt_id=UUID(int=sequence),
            sequence=sequence,
            status=status,
            execution_request_sha256=(
                "sha256:" + hashlib.sha256(f"request-{sequence}".encode()).hexdigest()
            ),
            running_store_revision=(
                UUID(int=10_000 + sequence)
                if status is EnumGoalAttemptStatus.PASS
                else None
            ),
            running_snapshot_sha256=(
                "sha256:" + hashlib.sha256(f"running-{sequence}".encode()).hexdigest()
                if status is EnumGoalAttemptStatus.PASS
                else None
            ),
            result_sha256=(
                "sha256:" + hashlib.sha256(f"result-{sequence}".encode()).hexdigest()
            )
            if status is EnumGoalAttemptStatus.PASS
            else None,
        )
        for sequence, status in enumerate(statuses, start=1)
    )
    count = len(attempts)
    snapshot_values = {
        "goal_id": goal_id,
        "repository": repository,
        "contract_revision": contract_revision,
        "subject_commit_sha": subject_commit_sha,
        "subject_tree_sha": subject_tree_sha,
        "allocation_count": count,
        "watermark_sequence": count,
        "store_revision": UUID(int=100),
        "attempts": attempts,
    }
    return ModelGoalAttemptAllocationSnapshot(
        **snapshot_values,
        snapshot_sha256=ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
            **snapshot_values
        ),
    )


def _goal_snapshot_fields(repo_root: Path) -> dict[str, object]:
    """Return the explicit source and subject bindings for one goal snapshot."""
    return {
        "repo": REPOSITORY,
        "pr_number": 123,
        "pr_title": "feat: verify a goal contract",
        "pr_body": "",
        "pr_branch": "jonah/omn-20070-goal-contract",
        "pr_commit_shas": (SUBJECT_COMMIT_SHA,),
        "pr_commit_texts": (),
        "goal_id": GOAL_ID,
        "goal_ticket_id": None,
        "contract_revision": CONTRACT_REVISION,
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "goal_contract_root": repo_root,
        "goal_contract_path": CONTRACT_RELATIVE_PATH,
        "goal_contract_source_commit_sha": SOURCE_COMMIT_SHA,
        "goal_contract_sha256": SOURCE_SHA256,
        "subject_commit_sha": SUBJECT_COMMIT_SHA,
        "subject_tree_sha": SUBJECT_TREE_SHA,
    }


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({completed.returncode}): "
            f"stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _canonical_goal_sha256(contract: dict[str, object]) -> str:
    canonical = json.dumps(
        contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _goal_receipt_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": None,
        "goal_id": str(GOAL_ID),
        "repository": REPOSITORY,
        "contract_revision": str(CONTRACT_REVISION),
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "attempt_id": str(UUID(int=1)),
        "attempt_sequence": 1,
        "attempt_result_sha256": "sha256:" + f"{1:064x}",
        "artifact_sha256": (),
        "evidence_item_id": GOAL_ITEM_ID,
        "check_type": GOAL_CHECK_TYPE,
        "check_value": GOAL_CHECK_VALUE,
        "contract_entry_sha256": "sha256:" + "b" * 64,
        "status": EnumReceiptStatus.PASS.value,
        "run_timestamp": datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
        "commit_sha": SUBJECT_COMMIT_SHA,
        "tree_sha": SUBJECT_TREE_SHA,
        "runner": "goal-test-runner",
        "verifier": "independent-goal-test-verifier",
        "probe_command": GOAL_CHECK_VALUE,
        "probe_stdout": "PASS\n",
        "exit_code": 0,
        "pr_number": 123,
    }
    payload.update(overrides)
    return payload


def _goal_contract(
    *,
    revision: UUID = CONTRACT_REVISION,
    schema_version: str = CONTRACT_SCHEMA_VERSION,
    description: str = "The contract criterion is satisfied.",
    second_item: bool = False,
    ticket_id: str | None = None,
    item_id: str = GOAL_ITEM_ID,
) -> dict[str, object]:
    items: list[dict[str, object]] = [
        {
            "id": item_id,
            "description": description,
            "binds_ac": ["criterion-goal-contract"],
            "checks": [
                {"check_type": GOAL_CHECK_TYPE, "check_value": GOAL_CHECK_VALUE}
            ],
        }
    ]
    if second_item:
        items.append(
            {
                "id": "goal-contract-second-required-criterion",
                "description": "A second required criterion is covered.",
                "binds_ac": ["criterion-second-required"],
                "checks": [{"check_type": "command", "check_value": "uv run true"}],
            }
        )
    contract: dict[str, object] = {
        "repository": REPOSITORY,
        "goal_id": str(GOAL_ID),
        "contract_revision": str(revision),
        "schema_version": schema_version,
        "subject_manifest": {
            "phase": "pre_merge",
            "required_subject_kind": "merge_group",
            "dependencies": [],
            "parent_integration_criterion_id": None,
        },
        "dod_evidence": items,
    }
    if ticket_id is not None:
        contract["ticket_id"] = ticket_id
    return contract


def _commit_file(repo_root: Path, relative_path: str, text: str, message: str) -> str:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo_root, "add", relative_path)
    _git(repo_root, "commit", "-m", message)
    return _git(repo_root, "rev-parse", "HEAD")


def _goal_repo(
    tmp_path: Path,
    *,
    contract: dict[str, object] | None = None,
    final_newline: bool = True,
    duplicate_repository_key: bool = False,
    origin_url: str = "https://github.com/OmniNode-ai/omnibase_core.git",
) -> dict[str, object]:
    """Build an isolated Git repo with one pinned goal source and candidate head."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _git(repo_root, "init", "-b", "main")
    _git(repo_root, "config", "user.name", "OMN-20070 fixture")
    _git(repo_root, "config", "user.email", "omn-20070-fixture@example.invalid")
    base_commit = _commit_file(
        repo_root, "README.md", "temporary source fixture\n", "fixture base"
    )
    source_repo_root = Path(__file__).parents[3]
    shutil.copyfile(
        source_repo_root / ".pre-commit-config.yaml",
        repo_root / ".pre-commit-config.yaml",
    )
    shutil.copyfile(source_repo_root / ".yamlfmt", repo_root / ".yamlfmt")
    _git(repo_root, "add", ".pre-commit-config.yaml", ".yamlfmt")
    _git(repo_root, "commit", "-m", "pin yaml formatting policy")

    goal_contract = contract or _goal_contract()
    contract_text = yaml.safe_dump(
        goal_contract,
        sort_keys=True,
        allow_unicode=True,
        explicit_start=True,
    )
    if duplicate_repository_key:
        contract_text = contract_text.replace(
            f"repository: {REPOSITORY}\n",
            f"repository: attacker/omnibase_core\nrepository: {REPOSITORY}\n",
        )
    source_repo_root = Path(__file__).parents[3]
    formatter = shutil.which("yamlfmt")
    assert formatter is not None, "the resolver requires the pinned yamlfmt binary"
    formatter_input = tmp_path / "goal-contract.yaml"
    formatter_input.write_text(contract_text, encoding="utf-8")
    formatted = subprocess.run(
        (
            formatter,
            "-conf",
            str(source_repo_root / ".yamlfmt"),
            "-no_global_conf",
            str(formatter_input),
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    assert formatted.returncode == 0, formatted.stderr
    contract_text = formatter_input.read_text(encoding="utf-8")
    if not final_newline:
        contract_text = contract_text.rstrip("\n")
    contract_source_commit = _commit_file(
        repo_root,
        CONTRACT_RELATIVE_PATH.as_posix(),
        contract_text,
        "pin goal contract source",
    )
    contract_source_tree = _git(
        repo_root, "rev-parse", f"{contract_source_commit}^{{tree}}"
    )
    parsed_contract = yaml.safe_load(contract_text)
    assert isinstance(parsed_contract, dict)

    subject_commit = _commit_file(
        repo_root, "subject.txt", "candidate subject\n", "candidate subject"
    )
    subject_tree = _git(repo_root, "rev-parse", f"{subject_commit}^{{tree}}")
    _git(repo_root, "remote", "add", "origin", origin_url)

    return {
        "repo_root": repo_root,
        "base_commit": base_commit,
        "contract": parsed_contract,
        "contract_source_commit": contract_source_commit,
        "contract_source_tree": contract_source_tree,
        "subject_commit": subject_commit,
        "subject_tree": subject_tree,
    }


def _add_protected_test_source(fixture: dict[str, object]) -> None:
    """Pin the known protected criterion file into the immutable subject tree."""
    if fixture.get("protected_test_source_committed") is True:
        return
    repo_root = fixture["repo_root"]
    assert isinstance(repo_root, Path)
    existing = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"HEAD:{PROTECTED_TEST_PATH}"],
        check=False,
        capture_output=True,
        env=scrub_git_location_env(),
    )
    if existing.returncode == 0 and existing.stdout == PROTECTED_TEST_BYTES:
        fixture["subject_commit"] = _git(repo_root, "rev-parse", "HEAD")
        fixture["subject_tree"] = _git(repo_root, "rev-parse", "HEAD^{tree}")
        fixture["protected_test_source_committed"] = True
        return
    path = repo_root / PROTECTED_TEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PROTECTED_TEST_BYTES)
    _git(repo_root, "add", PROTECTED_TEST_PATH)
    _git(repo_root, "commit", "-m", "pin protected goal criterion test")
    fixture["subject_commit"] = _git(repo_root, "rev-parse", "HEAD")
    fixture["subject_tree"] = _git(repo_root, "rev-parse", "HEAD^{tree}")
    fixture["protected_test_source_committed"] = True


def _goal_snapshot(
    fixture: dict[str, object],
    *,
    goal_ticket_id: str | None = None,
) -> ModelOccEligibilityInput:
    _add_protected_test_source(fixture)
    repo_root = fixture["repo_root"]
    assert isinstance(repo_root, Path)
    contract = fixture["contract"]
    assert isinstance(contract, dict)
    fields = _goal_snapshot_fields(repo_root)
    manifest = contract.get("subject_manifest")
    assert isinstance(manifest, dict)
    fields.update(
        {
            "goal_id": UUID(str(contract["goal_id"])),
            "goal_ticket_id": goal_ticket_id,
            "contract_revision": UUID(str(contract["contract_revision"])),
            "contract_schema_version": str(contract["schema_version"]),
            "goal_contract_root": repo_root,
            "goal_contract_source_commit_sha": fixture["contract_source_commit"],
            "goal_contract_sha256": _canonical_goal_sha256(
                fixture["contract"]  # type: ignore[arg-type]
            ),
            "subject_commit_sha": fixture["subject_commit"],
            "subject_tree_sha": fixture["subject_tree"],
            "pr_commit_shas": (fixture["subject_commit"],),
            "pr_body": f"Evidence-Ticket: {goal_ticket_id}" if goal_ticket_id else "",
        }
    )
    if (
        manifest.get("required_subject_kind") != "commit"
        or manifest.get("commit_source") != "pull_request"
    ):
        fields.update(
            {
                "pr_number": None,
                "pr_title": "",
                "pr_body": "",
                "pr_branch": "",
                "pr_commit_shas": (),
                "pr_commit_texts": (),
            }
        )
    return ModelOccEligibilityInput.model_validate(fields)


@dataclass
class _AttemptStoreOnlyProvider:
    """Test provider exposes allocation but no protected trust material."""

    allocation: ModelGoalAttemptAllocationSnapshot | None

    def read_current_goal_mutation_state(self, **_: object) -> ModelGoalMutationState:
        return ModelGoalMutationState(
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            store_revision=UUID("00000000-0000-4000-8000-000000000903"),
            status="clear",
        )

    def read_current_attempt_snapshot(self, **_: object):
        return self.allocation

    def get_policy(self, **_: object):
        return None

    def get_attestation(self, **_: object):
        return None

    def read_current_revision_history(self, **_: object):
        return None

    def get_evaluation_observation(self, **_: object):
        return None

    def get_work_ledger_key_provider(self):
        return None

    def get_domain_trust_root(self, domain_id: str):
        return None

    def read_artifact_bytes(self, digest: str):
        return None


def _snapshot_allocation(
    snapshot: ModelOccEligibilityInput,
    statuses: tuple[EnumGoalAttemptStatus, ...] = (EnumGoalAttemptStatus.PASS,),
) -> ModelGoalAttemptAllocationSnapshot:
    assert snapshot.goal_id is not None
    assert snapshot.contract_revision is not None
    assert snapshot.subject_commit_sha is not None
    assert snapshot.subject_tree_sha is not None
    return _attempt_allocation(
        goal_id=snapshot.goal_id,
        repository=snapshot.repo,
        contract_revision=snapshot.contract_revision,
        subject_commit_sha=snapshot.subject_commit_sha,
        subject_tree_sha=snapshot.subject_tree_sha,
        statuses=statuses,
    )


def _validate_goal_snapshot(
    snapshot: ModelOccEligibilityInput,
    allocation: ModelGoalAttemptAllocationSnapshot | None = None,
    *,
    trusted: bool = True,
) -> ModelOccEligibilityResult:
    del trusted
    return validate_occ_merge_eligibility(
        snapshot,
        goal_admission_provider=_AttemptStoreOnlyProvider(
            allocation if allocation is not None else _snapshot_allocation(snapshot)
        ),
    )


def _evaluate_goal(
    fixture: dict[str, object], *, goal_ticket_id: str | None = None
) -> object:
    return _validate_goal_snapshot(
        _goal_snapshot(fixture, goal_ticket_id=goal_ticket_id)
    )


@pytest.mark.unit
def test_ticket_free_goal_identity_is_explicit_and_not_derived_from_pr_text(
    tmp_path: Path,
) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields["pr_title"] = "feat: unrelated title"
    fields["pr_body"] = "Closes: OMN-10484"
    fields["pr_branch"] = "jonah/omn-10484-unrelated"
    fields["goal_ticket_id"] = None

    snapshot = ModelOccEligibilityInput.model_validate(fields)

    assert snapshot.goal_id == GOAL_ID
    assert snapshot.goal_ticket_id is None
    assert snapshot.repo == "OmniNode-ai/omnibase_core"
    assert snapshot.contract_revision == CONTRACT_REVISION
    assert snapshot.subject_commit_sha == SUBJECT_COMMIT_SHA
    assert snapshot.subject_tree_sha == SUBJECT_TREE_SHA


@pytest.mark.unit
def test_ticketed_goal_correlation_is_explicit_and_does_not_replace_goal_identity(
    tmp_path: Path,
) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields["goal_ticket_id"] = "OMN-20070"

    snapshot = ModelOccEligibilityInput.model_validate(fields)

    assert snapshot.goal_id == GOAL_ID
    assert snapshot.goal_ticket_id == "OMN-20070"
    assert snapshot.goal_ticket_id != str(snapshot.goal_id)


@pytest.mark.unit
def test_goal_input_allows_non_pr_subject_without_pr_metadata(tmp_path: Path) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields["pr_number"] = None
    fields["pr_commit_shas"] = ()
    fields["pr_title"] = ""
    fields["pr_body"] = ""
    fields["pr_branch"] = ""

    snapshot = ModelOccEligibilityInput.model_validate(fields)

    assert snapshot.pr_number is None
    assert not snapshot.pr_commit_shas
    assert snapshot.subject_commit_sha == SUBJECT_COMMIT_SHA


@pytest.mark.unit
def test_goal_semver_json_roundtrip_preserves_canonical_contract_string(
    tmp_path: Path,
) -> None:
    snapshot = ModelOccEligibilityInput.model_validate(
        _goal_snapshot_fields(tmp_path / "repo")
    )

    serialized = snapshot.model_dump(mode="json")
    assert serialized["contract_schema_version"] == CONTRACT_SCHEMA_VERSION
    reparsed = ModelOccEligibilityInput.model_validate(serialized)
    assert reparsed.contract_schema_version == snapshot.contract_schema_version


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_field",
    [
        "contract_revision",
        "contract_schema_version",
        "goal_contract_root",
        "goal_contract_path",
        "goal_contract_source_commit_sha",
        "goal_contract_sha256",
        "subject_commit_sha",
        "subject_tree_sha",
    ],
)
def test_goal_admission_refuses_each_missing_source_or_subject_binding(
    tmp_path: Path, missing_field: str
) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields[missing_field] = None

    with pytest.raises(ValidationError, match=missing_field):
        ModelOccEligibilityInput.model_validate(fields)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("goal_contract_source_commit_sha", "a" * 39),
        ("goal_contract_sha256", "sha256:" + "b" * 63),
        ("subject_commit_sha", "C" * 40),
        ("subject_tree_sha", "d" * 39),
        ("contract_schema_version", "1.0.0-rc.1"),
    ],
)
def test_goal_admission_refuses_malformed_identity_components(
    tmp_path: Path, field: str, value: str
) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields[field] = value

    with pytest.raises(ValidationError):
        ModelOccEligibilityInput.model_validate(fields)


@pytest.mark.unit
def test_goal_admission_requires_canonical_repository_identity(tmp_path: Path) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields["repo"] = "omnibase_core"

    with pytest.raises(ValidationError, match="owner/repository"):
        ModelOccEligibilityInput.model_validate(fields)


@pytest.mark.unit
@pytest.mark.parametrize(
    "repo",
    ["OmniNode-ai/omnibase_core/fork", "/omnibase_core", "OmniNode-ai/"],
)
def test_goal_admission_refuses_noncanonical_repository_paths(
    tmp_path: Path, repo: str
) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields["repo"] = repo

    with pytest.raises(ValidationError):
        ModelOccEligibilityInput.model_validate(fields)


@pytest.mark.unit
@pytest.mark.parametrize("goal_ticket_id", ["OMN-abc", "OMN-", " PR-123 "])
def test_goal_ticket_correlation_must_be_a_well_formed_omn_id(
    tmp_path: Path, goal_ticket_id: str
) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields["goal_ticket_id"] = goal_ticket_id

    with pytest.raises(ValidationError):
        ModelOccEligibilityInput.model_validate(fields)


@pytest.mark.unit
def test_goal_contract_path_cannot_escape_the_repository(tmp_path: Path) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields["goal_contract_path"] = PurePosixPath("contracts/goals/../../outside.yaml")

    with pytest.raises(ValidationError, match="contracts/goals"):
        ModelOccEligibilityInput.model_validate(fields)


@pytest.mark.unit
def test_goal_fields_without_goal_identity_do_not_fall_back_to_ticket_mode(
    tmp_path: Path,
) -> None:
    fields = _goal_snapshot_fields(tmp_path / "repo")
    fields["goal_id"] = None
    fields["goal_ticket_id"] = None

    with pytest.raises(ValidationError, match="require goal_id"):
        ModelOccEligibilityInput.model_validate(fields)


@pytest.mark.unit
def test_legacy_ticket_snapshot_keeps_the_historical_input_shape(
    tmp_path: Path,
) -> None:
    snapshot = ModelOccEligibilityInput(
        repo="omnibase_core",
        pr_number=123,
        pr_title="fix(OMN-20070): preserve ticket path",
        pr_body="Closes: OMN-20070",
        pr_branch="jonah/omn-20070-legacy-ticket",
        pr_commit_shas=(SUBJECT_COMMIT_SHA,),
        pr_commit_texts=("fix(OMN-20070): preserve ticket path",),
        occ_commit_sha="e" * 40,
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
    )

    serialized = snapshot.model_dump(exclude_none=True)
    assert "goal_id" not in serialized
    assert "goal_ticket_id" not in serialized
    assert "contract_revision" not in serialized
    assert "contract_schema_version" not in serialized
    assert "subject_commit_sha" not in serialized
    assert "subject_tree_sha" not in serialized


@pytest.mark.unit
def test_legacy_ticket_snapshot_still_requires_pr_number(tmp_path: Path) -> None:
    with pytest.raises(
        ValidationError, match="legacy OCC mode requires a pull request number"
    ):
        ModelOccEligibilityInput(
            repo="omnibase_core",
            pr_number=None,
            occ_commit_sha="e" * 40,
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )


@pytest.mark.unit
def test_legacy_ticket_receipt_keeps_opaque_goal_id_parsing() -> None:
    receipt = ModelDodReceipt.model_validate(
        {
            "schema_version": "1.0.0",
            "ticket_id": "OMN-20070",
            "goal_id": "delegate-session:historical-opaque-id",
            "evidence_item_id": "dod-001",
            "check_type": "command",
            "check_value": "uv run pytest tests/unit/validation/test_legacy.py -q",
            "status": EnumReceiptStatus.PASS.value,
            "run_timestamp": datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
            "commit_sha": SUBJECT_COMMIT_SHA,
            "runner": "historical-runner",
            "verifier": "independent-reviewer",
            "probe_command": "uv run pytest tests/unit/validation/test_legacy.py -q",
            "probe_stdout": "1 passed\n",
            "exit_code": 0,
        }
    )

    assert receipt.ticket_id == "OMN-20070"
    assert receipt.goal_id == "delegate-session:historical-opaque-id"
    assert receipt.model_dump(mode="json", exclude_none=True)["goal_id"] == (
        "delegate-session:historical-opaque-id"
    )


@pytest.mark.unit
def test_ticket_free_goal_receipt_requires_complete_typed_identity() -> None:
    receipt = ModelDodReceipt.model_validate(_goal_receipt_payload())

    assert receipt.ticket_id is None
    assert receipt.goal_id == str(GOAL_ID)
    assert receipt.repository == REPOSITORY
    assert receipt.contract_revision == CONTRACT_REVISION
    assert receipt.contract_schema_version is not None
    assert receipt.contract_schema_version.to_string() == CONTRACT_SCHEMA_VERSION
    assert len(receipt.commit_sha) == 40
    assert len(receipt.tree_sha or "") == 40


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_field",
    [
        "goal_id",
        "repository",
        "contract_revision",
        "contract_schema_version",
        "tree_sha",
    ],
)
def test_ticket_free_goal_receipt_rejects_missing_identity_bindings(
    missing_field: str,
) -> None:
    payload = _goal_receipt_payload()
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        ModelDodReceipt.model_validate(payload)


@pytest.mark.unit
def test_ticket_free_goal_receipt_rejects_non_uuid_goal_id() -> None:
    payload = _goal_receipt_payload(goal_id="delegate-session:opaque")

    with pytest.raises(ValidationError, match="UUID"):
        ModelDodReceipt.model_validate(payload)


@pytest.mark.unit
def test_goal_bound_receipt_rejects_abbreviated_subject_commit() -> None:
    payload = _goal_receipt_payload(commit_sha="abc1234")

    with pytest.raises(ValidationError, match="full Git object id"):
        ModelDodReceipt.model_validate(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    "repository",
    [
        "owner with spaces/repo",
        "owner/repo ",
        " owner/repo",
        "owner/repo/extra",
    ],
)
def test_goal_bound_receipt_rejects_noncanonical_repository(repository: str) -> None:
    with pytest.raises(ValidationError, match="canonical owner/repository"):
        ModelDodReceipt.model_validate(_goal_receipt_payload(repository=repository))


@pytest.mark.unit
def test_goal_bound_receipt_preserves_canonical_repository_spelling() -> None:
    receipt = ModelDodReceipt.model_validate(
        _goal_receipt_payload(repository="Owner/Repo")
    )

    assert receipt.repository == "Owner/Repo"


@pytest.mark.unit
def test_legacy_ticket_receipt_preserves_sha256_tree_id_parsing() -> None:
    payload = _goal_receipt_payload(
        ticket_id="OMN-20070",
        goal_id="delegate-session:historical-opaque-id",
        tree_sha="f" * 64,
    )
    payload.pop("repository")
    payload.pop("contract_revision")
    payload.pop("contract_schema_version")
    payload.pop("attempt_id")
    payload.pop("attempt_sequence")
    payload.pop("attempt_result_sha256")
    payload.pop("artifact_sha256")

    receipt = ModelDodReceipt.model_validate(payload)

    assert receipt.ticket_id == "OMN-20070"
    assert receipt.tree_sha == "f" * 64


@pytest.mark.unit
def test_ticket_free_goal_contract_identity_is_not_derived_from_pr_ticket_text(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _goal_snapshot(fixture).model_copy(
        update={
            "pr_title": "feat: unrelated legacy ticket citation OMN-10484",
            "pr_body": "Closes: OMN-10484",
            "pr_branch": "jonah/omn-10484-unrelated",
        }
    )

    result = _validate_goal_snapshot(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert result.attempt_sequence == 1
    assert result.attempt_watermark_sequence == 1
    assert result.ticket_ids == ()


@pytest.mark.unit
def test_ticket_correlated_goal_identity_remains_explicit(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path, contract=_goal_contract(ticket_id="OMN-20070"))

    result = _evaluate_goal(fixture, goal_ticket_id="OMN-20070")

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert result.attempt_sequence == 1


@pytest.mark.unit
def test_goal_resolution_refuses_repository_remote_mismatch(tmp_path: Path) -> None:
    fixture = _goal_repo(
        tmp_path, origin_url="https://github.com/attacker/omnibase_core.git"
    )

    result = _validate_goal_snapshot(_goal_snapshot(fixture))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH


@pytest.mark.unit
def test_goal_resolution_rejects_non_github_scp_remote(tmp_path: Path) -> None:
    fixture = _goal_repo(
        tmp_path,
        origin_url="git@attacker.example:OmniNode-ai/omnibase_core.git",
    )

    result = _validate_goal_snapshot(_goal_snapshot(fixture))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH


@pytest.mark.unit
def test_goal_resolution_refuses_source_commit_without_pinned_contract_path(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _goal_snapshot(fixture).model_copy(
        update={"goal_contract_source_commit_sha": fixture["base_commit"]}
    )

    result = _validate_goal_snapshot(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CONTRACT_INVALID


@pytest.mark.unit
def test_goal_resolution_refuses_wrong_repo_relative_source_path(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _goal_snapshot(fixture).model_copy(
        update={"goal_contract_path": PurePosixPath("contracts/goals/other.yaml")}
    )

    result = _validate_goal_snapshot(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CONTRACT_INVALID


@pytest.mark.unit
def test_goal_resolution_refuses_canonical_contract_digest_mismatch(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _goal_snapshot(fixture).model_copy(
        update={"goal_contract_sha256": "sha256:" + "f" * 64}
    )

    result = _validate_goal_snapshot(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CONTRACT_INVALID


@pytest.mark.unit
def test_goal_resolution_refuses_subject_commit_that_is_not_the_pr_head(
    tmp_path: Path,
) -> None:
    contract = _goal_contract()
    contract["subject_manifest"] = {
        "phase": "post_merge",
        "required_subject_kind": "commit",
        "commit_source": "pull_request",
        "subject_ref": "refs/heads/jonah/omn-20070-goal-contract",
        "base_ref": "refs/heads/main",
        "dependencies": [],
        "parent_integration_criterion_id": None,
    }
    fixture = _goal_repo(tmp_path, contract=contract)
    snapshot = _goal_snapshot(fixture).model_copy(
        update={
            "subject_commit_sha": fixture["contract_source_commit"],
            "subject_tree_sha": fixture["contract_source_tree"],
        }
    )

    result = _validate_goal_snapshot(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH


@pytest.mark.unit
def test_goal_resolution_refuses_subject_tree_mismatch(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _goal_snapshot(fixture).model_copy(update={"subject_tree_sha": "f" * 40})

    result = _validate_goal_snapshot(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH


@pytest.mark.unit
@pytest.mark.unit
def test_newest_pass_is_selected_but_still_waits_for_trusted_admission(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _goal_snapshot(fixture)
    allocation = _snapshot_allocation(
        snapshot, (EnumGoalAttemptStatus.PASS, EnumGoalAttemptStatus.PASS)
    )

    result = _validate_goal_snapshot(snapshot, allocation, trusted=False)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert result.attempt_id == UUID(int=2)
    assert result.attempt_sequence == 2
    assert result.attempt_watermark_sequence == 2


@pytest.mark.unit
def test_goal_allocation_rejects_duplicate_sequence_and_attempt_id(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _snapshot_allocation(
        _goal_snapshot(fixture),
        (EnumGoalAttemptStatus.PASS, EnumGoalAttemptStatus.FAIL),
    )

    duplicate_sequence = snapshot.attempts[1].model_copy(update={"sequence": 1})
    duplicate_id = snapshot.attempts[1].model_copy(
        update={"attempt_id": snapshot.attempts[0].attempt_id}
    )
    for attempts in (
        (snapshot.attempts[0], duplicate_sequence),
        (snapshot.attempts[0], duplicate_id),
    ):
        values = snapshot.model_dump()
        values["attempts"] = attempts
        with pytest.raises(ValidationError):
            ModelGoalAttemptAllocationSnapshot.model_validate(values)


@pytest.mark.unit
def test_goal_allocation_rejects_gap_or_wrong_partition_row(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _snapshot_allocation(
        _goal_snapshot(fixture),
        (EnumGoalAttemptStatus.PASS, EnumGoalAttemptStatus.FAIL),
    )
    gapped_attempt = snapshot.attempts[1].model_copy(update={"sequence": 3})
    wrong_partition_attempt = snapshot.attempts[1].model_copy(
        update={"subject_tree_sha": "f" * 40}
    )
    for attempts in (
        (snapshot.attempts[0], gapped_attempt),
        (snapshot.attempts[0], wrong_partition_attempt),
    ):
        values = snapshot.model_dump()
        values["attempts"] = attempts
        with pytest.raises(ValidationError):
            ModelGoalAttemptAllocationSnapshot.model_validate(values)


@pytest.mark.unit
def test_goal_allocation_digest_cannot_be_replayed_after_row_change(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _snapshot_allocation(_goal_snapshot(fixture))
    values = snapshot.model_dump()
    values["store_revision"] = UUID(int=101)

    with pytest.raises(ValidationError, match="digest"):
        ModelGoalAttemptAllocationSnapshot.model_validate(values)


@pytest.mark.unit
def test_recomputed_truncated_snapshot_is_only_internally_consistent(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    base_snapshot = _goal_snapshot(fixture)
    full = _snapshot_allocation(
        base_snapshot,
        (EnumGoalAttemptStatus.PASS, EnumGoalAttemptStatus.ALLOCATED),
    )
    attempts = (full.attempts[0],)
    values = {
        "goal_id": full.goal_id,
        "repository": full.repository,
        "contract_revision": full.contract_revision,
        "subject_commit_sha": full.subject_commit_sha,
        "subject_tree_sha": full.subject_tree_sha,
        "allocation_count": 1,
        "watermark_sequence": 1,
        "store_revision": UUID(int=101),
        "attempts": attempts,
    }
    truncated = ModelGoalAttemptAllocationSnapshot(
        **values,
        snapshot_sha256=ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
            **values
        ),
    )

    # A self-consistent digest cannot prove that a caller did not omit rows.
    # The trusted transactional loader/CAS and supervisor attestation must
    # bind the authoritative revision and watermark before eligibility.
    assert truncated.allocation_count == 1
    assert truncated.watermark_sequence == 1
    assert len(truncated.attempts) == 1
    supplied_fields = base_snapshot.model_dump()
    supplied_fields["attempt_allocation"] = truncated
    with pytest.raises(ValidationError, match="extra"):
        ModelOccEligibilityInput.model_validate(supplied_fields)


@pytest.mark.unit
def test_valid_allocation_without_trusted_admission_stays_incomplete(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)

    result = _validate_goal_snapshot(_goal_snapshot(fixture), trusted=False)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert result.attempt_id == UUID(int=1)
    assert result.attempt_sequence == 1
    assert result.attempt_snapshot_sha256 is not None


@pytest.mark.unit
def test_missing_attempt_allocation_returns_incomplete_goal_verdict(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _goal_snapshot(fixture)

    result = validate_occ_merge_eligibility(
        snapshot, goal_admission_provider=_AttemptStoreOnlyProvider(None)
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE


@pytest.mark.unit
def test_contract_without_final_newline_fails_pinned_formatter_policy(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path, final_newline=False)

    snapshot = _goal_snapshot(fixture)
    assert snapshot.goal_contract_sha256 == _canonical_goal_sha256(
        fixture["contract"]  # type: ignore[arg-type]
    )

    result = _validate_goal_snapshot(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_FORMAT_INVALID


@pytest.mark.unit
def test_goal_contract_duplicate_yaml_keys_are_rejected_as_invalid_source(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path, duplicate_repository_key=True)

    result = _validate_goal_snapshot(_goal_snapshot(fixture))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CONTRACT_INVALID
