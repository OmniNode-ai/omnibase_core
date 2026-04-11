# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""PlanContract model for contract-driven plan lifecycle.

Provides the main lifecycle contract wrapping ModelPlanDocument with
phase state machine, ticket linkage, review tracking, fingerprinting,
and YAML persistence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from typing import Any, ClassVar

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.plan import (
    PLAN_PHASE_ALLOWED_ACTIONS,
    PLAN_VALID_TRANSITIONS,
    EnumPlanAction,
    EnumPlanPhase,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.plan.model_dod_item import ModelDoDItem
from omnibase_core.models.plan.model_plan_document import ModelPlanDocument
from omnibase_core.models.plan.model_plan_entry import ModelPlanEntry
from omnibase_core.models.plan.model_plan_review_result import ModelPlanReviewResult
from omnibase_core.models.plan.model_plan_ticket_link import ModelPlanTicketLink
from omnibase_core.utils.util_decorators import allow_dict_str_any, allow_string_id

_EPIC_ID_PATTERN = re.compile(r"^OMN-\d+$")


@allow_string_id(reason="Plan ID is an external identifier (e.g., PLAN-OMN-5971)")
@allow_dict_str_any(
    reason="Context accumulates arbitrary orchestration metadata during workflow"
)
class ModelPlanContract(BaseModel):
    """Lifecycle contract for plans.

    Wraps a frozen ModelPlanDocument with mutable lifecycle state: phase
    tracking, ticket linkage, review governance, and fingerprinting.

    Mutability:
        This model is mutable (NOT frozen) to allow state updates during
        workflow execution. All mutations go through explicit validated
        methods that enforce preconditions and update the fingerprint.
        Use update_fingerprint() after any direct field modifications.

    YAML Persistence:
        The contract is designed to be serialized to/from YAML for persistence.
        Use to_yaml() and from_yaml() methods for serialization.
    """

    # Plan identification
    # string-id-ok: Plan ID is an external identifier (e.g., PLAN-OMN-5971)
    plan_id: str = Field(..., description="Unique plan ID (e.g., PLAN-OMN-5971)")

    # The frozen structural plan document
    document: ModelPlanDocument = Field(
        ..., description="The frozen structural plan document"
    )

    # Workflow state
    phase: EnumPlanPhase = Field(
        default=EnumPlanPhase.DRAFT, description="Current lifecycle phase"
    )

    # Review tracking
    reviews: list[ModelPlanReviewResult] = Field(
        default_factory=list, description="Adversarial review results"
    )

    # Ticket linkage
    ticket_links: list[ModelPlanTicketLink] = Field(
        default_factory=list, description="Plan entry to Linear ticket links"
    )

    # Context and extensibility metadata
    # dict-str-any-ok: Context accumulates arbitrary orchestration metadata during workflow
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-core extensibility metadata (orchestration, session, etc.)",
    )

    # -------------------------------------------------------------------------
    # Enforcement-chain metadata (OMN-8421)
    # -------------------------------------------------------------------------
    # These fields support the plan -> epic -> tickets -> PR -> dogfood
    # enforcement chain (OMN-8416). They live at the top level (not in
    # context) so downstream hooks and skills get type-safe access.
    #
    # NAMING: `plan_phases` (plural, list) is distinct from the existing
    # `phase: EnumPlanPhase` field above, which tracks lifecycle state
    # (DRAFT -> REVIEWED -> TICKETED -> EXECUTING -> CLOSED). `plan_phases`
    # is the ordered list of plan-defined phase IDs (e.g. ["P0", "P1", "P2"])
    # that the plan decomposes its work into. They are different concepts.
    epic_id: str | None = Field(
        default=None,
        description=(
            "Linear epic identifier that this plan is realized under "
            "(e.g. 'OMN-8416'). Must match `^OMN-\\d+$`."
        ),
    )
    plan_phases: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of plan-defined phase IDs. Distinct from "
            "`phase: EnumPlanPhase` lifecycle state."
        ),
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Plan IDs that must complete before this plan starts.",
    )
    success_criteria: list[ModelDoDItem] = Field(
        default_factory=list,
        description="Definition-of-done items for this plan.",
    )
    halt_conditions: list[str] = Field(
        default_factory=list,
        description=(
            "Plain-string halt conditions. Structured ModelHaltCondition "
            "support is deferred to OMN-8375 territory."
        ),
    )
    supersedes: list[str] = Field(
        default_factory=list,
        description="Plan IDs that this plan replaces.",
    )
    superseded_by: str | None = Field(
        default=None,
        description="Plan ID that replaces this plan, if any.",
    )

    # Fingerprinting and timestamps
    contract_fingerprint: str | None = Field(
        default=None, description="SHA256 fingerprint of contract state"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When the contract was created (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When the contract was last updated (UTC)",
    )

    # ConfigDict rationale:
    # - extra="allow": YAML contracts may accumulate plugin-specific fields.
    #   Using "allow" ensures graceful deserialization when new optional fields
    #   are added to persisted contracts.
    # - NOT frozen: The contract is mutated in-place during workflow execution
    #   (phase transitions, fingerprint updates, adding reviews/links).
    # - from_attributes=True: Required for pytest-xdist where workers import
    #   classes independently.
    model_config = ConfigDict(
        extra="allow",
        from_attributes=True,
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("epic_id", mode="after")
    @classmethod
    def _validate_epic_id(cls, v: str | None) -> str | None:
        """Enforce OMN-<digits> format on epic_id when set."""
        if v is None:
            return v
        if not _EPIC_ID_PATTERN.match(v):
            raise ValueError(  # error-ok: Pydantic field_validator requires ValueError
                f"epic_id {v!r} does not match required pattern '^OMN-\\d+$'"
            )
        return v

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _enforce_utc_timezone(cls, v: Any) -> Any:
        """Enforce UTC timezone on datetime fields during deserialization.

        Naive datetimes (no timezone info) are assumed UTC and have the UTC
        timezone attached. Datetimes with a non-UTC timezone are converted
        to UTC. Already-UTC datetimes pass through unchanged.
        """
        if not isinstance(v, datetime):
            return v

        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)

        return v.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_ticket_links(self) -> ModelPlanContract:
        """Validate that all ticket link entry_ids exist in document entries.

        Also enforces link uniqueness: one entry -> one ticket (no duplicate
        entry_id in ticket_links).
        """
        entry_ids = {entry.id for entry in self.document.entries}
        seen_entry_ids: set[str] = set()

        for link in self.ticket_links:
            if link.entry_id not in entry_ids:
                raise ValueError(  # error-ok: Pydantic model_validator requires ValueError
                    f"Ticket link entry_id {link.entry_id!r} does not exist "
                    f"in document entries: {sorted(entry_ids)}"
                )
            if link.entry_id in seen_entry_ids:
                raise ValueError(  # error-ok: Pydantic model_validator requires ValueError
                    f"Duplicate ticket link for entry_id {link.entry_id!r}: "
                    f"each entry may have at most one ticket link"
                )
            seen_entry_ids.add(link.entry_id)

        return self

    # =========================================================================
    # Phase Enforcement Methods
    # =========================================================================

    def allowed_actions(self) -> frozenset[EnumPlanAction]:
        """Get the frozenset of actions allowed in the current phase.

        Returns:
            Frozenset of EnumPlanAction enum values (not strings).
        """
        return PLAN_PHASE_ALLOWED_ACTIONS.get(self.phase, frozenset())

    def assert_action_allowed(self, action: EnumPlanAction | str) -> None:
        """Assert that an action is allowed in the current phase.

        Accepts both enum values and strings for CLI ergonomics.

        Args:
            action: The action to check (enum or string).

        Raises:
            ModelOnexError: If the action is not allowed in the current phase,
                or if the action value is not a valid EnumPlanAction.
        """
        # Reject non-str, non-enum types early
        if not isinstance(action, (str, EnumPlanAction)):
            raise ModelOnexError(
                message=(
                    f"Invalid action type: expected str or EnumPlanAction, "
                    f"got {type(action).__name__}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                action=repr(action),
                valid_actions=[a.value for a in EnumPlanAction],
            )

        # Normalize string input to enum
        if isinstance(action, str):
            try:
                action = EnumPlanAction(action)
            except ValueError as e:
                raise ModelOnexError(
                    message=f"Invalid action: {action!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    action=action,
                    valid_actions=[a.value for a in EnumPlanAction],
                ) from e

        allowed = self.allowed_actions()
        if action not in allowed:
            raise ModelOnexError(
                message=(
                    f"Action {action.value!r} is not allowed in phase "
                    f"{self.phase.value!r}. "
                    f"Allowed actions: {[a.value for a in allowed]}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                action=action.value,
                phase=self.phase.value,
                allowed_actions=[a.value for a in allowed],
            )

    # =========================================================================
    # Phase Transition
    # =========================================================================

    def transition_to(self, target: EnumPlanPhase) -> None:
        """Transition to a new phase with guard enforcement.

        Valid transitions (enforced):
            DRAFT -> REVIEWED:    requires is_review_complete()
            REVIEWED -> DRAFT:    always valid (revision path)
            REVIEWED -> TICKETED: requires is_fully_ticketed()
            TICKETED -> EXECUTING: always valid
            EXECUTING -> CLOSED:  requires is_lifecycle_complete()
            CLOSED -> (nothing):  terminal, raises ModelOnexError

        Args:
            target: The target phase to transition to.

        Raises:
            ModelOnexError: If transition is invalid or guards fail.
        """
        valid_targets = PLAN_VALID_TRANSITIONS.get(self.phase, frozenset())

        if target not in valid_targets:
            raise ModelOnexError(
                message=(
                    f"Invalid phase transition: {self.phase.value!r} -> "
                    f"{target.value!r}. Valid targets: "
                    f"{[t.value for t in valid_targets]}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                current_phase=self.phase.value,
                target_phase=target.value,
                valid_targets=[t.value for t in valid_targets],
            )

        # Guard: DRAFT -> REVIEWED requires passing review
        if self.phase == EnumPlanPhase.DRAFT and target == EnumPlanPhase.REVIEWED:
            if not self.is_review_complete():
                raise ModelOnexError(
                    message=(
                        "Cannot transition DRAFT -> REVIEWED: no passing review "
                        "matching current document fingerprint"
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    current_fingerprint=self.document_fingerprint(),
                )

        # Guard: REVIEWED -> TICKETED requires all entries linked
        if self.phase == EnumPlanPhase.REVIEWED and target == EnumPlanPhase.TICKETED:
            if not self.is_fully_ticketed():
                unlinked = [e.id for e in self.unlinked_entries()]
                raise ModelOnexError(
                    message=(
                        "Cannot transition REVIEWED -> TICKETED: not all entries "
                        f"have ticket links. Unlinked: {unlinked}"
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    unlinked_entries=unlinked,
                )

        # Guard: EXECUTING -> CLOSED requires lifecycle complete (defense-in-depth)
        if self.phase == EnumPlanPhase.EXECUTING and target == EnumPlanPhase.CLOSED:
            if not self.is_lifecycle_complete():
                raise ModelOnexError(
                    message=(
                        "Cannot transition EXECUTING -> CLOSED: lifecycle not "
                        "complete (review and ticketing checks failed)"
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

        self.phase = target
        self.update_fingerprint()

    # =========================================================================
    # Mutation Methods
    # =========================================================================

    def add_ticket_link(self, link: ModelPlanTicketLink) -> None:
        """Add a ticket link for a plan entry.

        Validates that the entry_id exists in the document and that no
        duplicate link exists for the same entry.

        Args:
            link: The ticket link to add.

        Raises:
            ModelOnexError: If action not allowed, entry_id invalid, or duplicate.
        """
        self.assert_action_allowed(EnumPlanAction.LINK_TICKET)

        # Validate entry_id exists in document
        entry_ids = {entry.id for entry in self.document.entries}
        if link.entry_id not in entry_ids:
            raise ModelOnexError(
                message=(
                    f"Cannot link ticket: entry_id {link.entry_id!r} does not "
                    f"exist in document entries"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                entry_id=link.entry_id,
                valid_entry_ids=sorted(entry_ids),
            )

        # Reject duplicate entry_id
        existing_entry_ids = {tl.entry_id for tl in self.ticket_links}
        if link.entry_id in existing_entry_ids:
            raise ModelOnexError(
                message=(
                    f"Cannot link ticket: entry_id {link.entry_id!r} already "
                    f"has a ticket link"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                entry_id=link.entry_id,
            )

        self.ticket_links.append(link)
        self.update_fingerprint()

    def add_review(self, result: ModelPlanReviewResult) -> None:
        """Record an adversarial review result.

        Validates that the review's document_fingerprint matches the current
        document fingerprint (reviews are tied to specific document revisions).

        Args:
            result: The review result to record.

        Raises:
            ModelOnexError: If action not allowed or fingerprint mismatch.
        """
        self.assert_action_allowed(EnumPlanAction.RECORD_REVIEW)

        current_fp = self.document_fingerprint()
        if result.document_fingerprint != current_fp:
            raise ModelOnexError(
                message=(
                    f"Cannot record review: document_fingerprint "
                    f"{result.document_fingerprint!r} does not match current "
                    f"document fingerprint {current_fp!r}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                review_fingerprint=result.document_fingerprint,
                current_fingerprint=current_fp,
            )

        self.reviews.append(result)
        self.update_fingerprint()

    def replace_document(self, new_doc: ModelPlanDocument) -> None:
        """Replace the plan document with a new revision.

        Re-validates all existing ticket_links against the new document
        entries. If phase is REVIEWED, automatically demotes to DRAFT
        (existing reviews are stale against the new document).

        Args:
            new_doc: The new plan document.

        Raises:
            ModelOnexError: If action not allowed or existing links reference
                entries not in the new document.
        """
        self.assert_action_allowed(EnumPlanAction.EDIT_PLAN)

        # Validate existing ticket links against new document
        new_entry_ids = {entry.id for entry in new_doc.entries}
        for link in self.ticket_links:
            if link.entry_id not in new_entry_ids:
                raise ModelOnexError(
                    message=(
                        f"Cannot replace document: existing ticket link "
                        f"references entry_id {link.entry_id!r} which does "
                        f"not exist in the new document"
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    orphaned_entry_id=link.entry_id,
                    new_entry_ids=sorted(new_entry_ids),
                )

        self.document = new_doc

        # Auto-demote to DRAFT if in REVIEWED (reviews are stale)
        if self.phase == EnumPlanPhase.REVIEWED:
            self.phase = EnumPlanPhase.DRAFT

        self.update_fingerprint()

    # =========================================================================
    # Completion Checks
    # =========================================================================

    def document_fingerprint(self) -> str:
        """Compute 16-char SHA256 fingerprint of the document.

        Used to tie reviews to specific document revisions.

        Returns:
            16-character hex string.
        """
        data = self.document.model_dump(mode="json")
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def is_review_complete(self) -> bool:
        """Check if the plan has a passing review matching the current document.

        A passing review against a previous document revision does not count.
        This is the key governance rule: edits invalidate prior reviews.

        Returns:
            True if at least one review has passed=True AND document_fingerprint
            matching the current document_fingerprint().
        """
        current_fp = self.document_fingerprint()
        return any(
            r.passed and r.document_fingerprint == current_fp for r in self.reviews
        )

    def is_fully_ticketed(self) -> bool:
        """Check if every document entry has exactly one ticket link.

        Returns:
            True if all entries are linked, False otherwise.
        """
        linked_entry_ids = {link.entry_id for link in self.ticket_links}
        return all(entry.id in linked_entry_ids for entry in self.document.entries)

    def is_execution_complete(self, ticket_statuses: dict[str, bool]) -> bool:
        """Check if all linked tickets are done.

        Pure function: caller passes ticket statuses from external source.
        Fail-closed: missing keys return False.

        Args:
            ticket_statuses: Mapping of ticket_id -> is_done.

        Returns:
            True only if ALL linked ticket IDs are present in the dict
            and all are True.
        """
        linked_ids = self.linked_ticket_ids()
        if not linked_ids:
            return False
        return all(ticket_statuses.get(tid, False) for tid in linked_ids)

    def is_lifecycle_complete(self) -> bool:
        """Check if review and ticketing lifecycle requirements are met.

        Used as the EXECUTING -> CLOSED guard. Does NOT include execution
        completeness (that requires external data).

        Returns:
            True if is_review_complete() and is_fully_ticketed().
        """
        return self.is_review_complete() and self.is_fully_ticketed()

    def is_done(self) -> bool:
        """Check if the contract lifecycle is in its terminal valid state.

        This means phase == CLOSED and structurally complete. It does NOT
        claim all linked tickets are done -- that is is_execution_complete(),
        which requires external data.

        Returns:
            True if phase is CLOSED and lifecycle is complete.
        """
        return self.phase == EnumPlanPhase.CLOSED and self.is_lifecycle_complete()

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def unlinked_entries(self) -> list[ModelPlanEntry]:
        """Get document entries that have no ticket link.

        Returns:
            List of ModelPlanEntry instances without a corresponding ticket link.
        """
        linked_entry_ids = {link.entry_id for link in self.ticket_links}
        return [
            entry for entry in self.document.entries if entry.id not in linked_entry_ids
        ]

    def linked_ticket_ids(self) -> list[str]:
        """Get unique ticket IDs from all ticket links (deduplicated).

        Returns:
            List of unique ticket IDs in first-seen order.
        """
        seen: set[str] = set()
        result: list[str] = []
        for link in self.ticket_links:
            if link.ticket_id not in seen:
                seen.add(link.ticket_id)
                result.append(link.ticket_id)
        return result

    def is_transitively_superseded(
        self, resolver: dict[str, ModelPlanContract]
    ) -> bool:
        """Walk the superseded_by chain and detect supersession.

        Pure function: caller supplies the plan_id -> contract resolver.
        Follows superseded_by pointers until the chain terminates at a live
        plan (superseded_by=None), a cycle is detected, or an unresolvable
        plan_id is encountered.

        Args:
            resolver: Mapping of plan_id to ModelPlanContract, used to walk
                the superseded_by chain beyond the immediate successor.

        Returns:
            True only when the chain terminates at a confirmed live successor
            (superseded_by=None) or when a cycle is detected. False when this
            plan has no successor or when the chain leads to an unresolvable
            plan_id (no false-positive supersession claims).
        """
        if self.superseded_by is None:
            return False
        visited: set[str] = {self.plan_id}
        cursor: str | None = self.superseded_by
        while cursor is not None:
            if cursor in visited:
                # Cycle — treat as superseded (abnormal but confirmed non-live)
                return True
            visited.add(cursor)
            next_contract = resolver.get(cursor)
            if next_contract is None:
                # Unresolvable successor — cannot confirm supersession
                return False
            cursor = next_contract.superseded_by
        # Loop exited with cursor=None: chain terminated at a live plan
        return True

    def link_for_entry(self, entry_id: str) -> ModelPlanTicketLink | None:
        """Look up the ticket link for a given entry ID.

        Unambiguous because entry_id is unique in ticket_links.

        Args:
            entry_id: The plan entry ID to look up.

        Returns:
            The ModelPlanTicketLink if found, None otherwise.
        """
        for link in self.ticket_links:
            if link.entry_id == entry_id:
                return link
        return None

    # =========================================================================
    # Fingerprinting Methods
    # =========================================================================

    def compute_fingerprint(self) -> str:
        """Compute a 16-character hex SHA256 fingerprint of the contract.

        The fingerprint excludes contract_fingerprint (circular), created_at
        (immutable metadata), and updated_at (mechanical timestamp).

        Included: plan_id, document, phase, reviews, ticket_links, context.

        Returns:
            16-character hex string.
        """
        data = self.model_dump(
            mode="json",
            exclude={"contract_fingerprint", "created_at", "updated_at"},
        )
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def update_fingerprint(self) -> None:
        """Update the contract fingerprint and updated_at timestamp."""
        self.contract_fingerprint = self.compute_fingerprint()
        self.updated_at = datetime.now(tz=UTC)

    # =========================================================================
    # YAML Serialization
    # =========================================================================

    def to_yaml(self) -> str:
        """Serialize the contract to YAML.

        Uses mode='json' to ensure datetime and enum serialization.

        Returns:
            YAML string representation.
        """
        data = self.model_dump(mode="json")
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> ModelPlanContract:
        """Deserialize a contract from YAML.

        Args:
            yaml_str: YAML string to parse.

        Returns:
            ModelPlanContract instance.

        Raises:
            ModelOnexError: If YAML parsing or validation fails.
        """
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise ModelOnexError(
                message=f"Failed to parse YAML: {e}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            ) from e

        if not isinstance(data, dict):
            raise ModelOnexError(
                message=f"Expected dict from YAML, got {type(data).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        try:
            return cls.model_validate(data)
        except ValidationError as e:
            raise ModelOnexError(
                message=f"Contract validation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    # =========================================================================
    # Contract Grace Period (Bootstrap Paradox)
    # =========================================================================

    # Plans created before this date are exempt from contract requirements.
    # This handles the bootstrap paradox where plans exist before the
    # ModelPlanContract format was introduced.
    #
    # Default: 2026-03-23 (the date contract enforcement was first deployed).
    # Override via PLAN_CONTRACT_REQUIRED_AFTER env var (ISO date).
    PLAN_CONTRACT_REQUIRED_AFTER: ClassVar[datetime] = datetime.fromisoformat(
        os.environ.get("PLAN_CONTRACT_REQUIRED_AFTER", "2026-03-23T00:00:00+00:00")
    )

    @classmethod
    def is_contract_required(cls, plan_created_at: datetime | str) -> bool:
        """Check whether a plan is required to have a contract.

        Plans created before PLAN_CONTRACT_REQUIRED_AFTER get a grace period
        and are NOT required to have a contract. This prevents false failures
        when scanning pre-existing plans.

        Args:
            plan_created_at: When the plan was created (datetime or ISO string).

        Returns:
            True if the plan must have a contract, False if in grace period.
        """
        if isinstance(plan_created_at, str):
            plan_created_at = datetime.fromisoformat(plan_created_at)

        # Ensure timezone-aware comparison
        if plan_created_at.tzinfo is None:
            plan_created_at = plan_created_at.replace(tzinfo=UTC)

        return plan_created_at >= cls.PLAN_CONTRACT_REQUIRED_AFTER

    # =========================================================================
    # Repr
    # =========================================================================

    def __repr__(self) -> str:
        """Return concise representation for debugging."""
        return (
            f"ModelPlanContract("
            f"id={self.plan_id!r}, "
            f"phase={self.phase.value!r}, "
            f"entries={len(self.document.entries)}, "
            f"reviews={len(self.reviews)}, "
            f"links={len(self.ticket_links)})"
        )


# Alias for cleaner imports
PlanContract = ModelPlanContract

__all__ = [
    "ModelPlanContract",
    "PlanContract",
]
