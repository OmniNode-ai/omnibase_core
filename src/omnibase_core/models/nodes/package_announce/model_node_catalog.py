# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The node catalog: one entry per announced contract name (OMN-21589).

The catalog is a pure value. ``apply`` takes an announcement and returns the next
catalog, so the runtime reads a catalog built from announcements instead of
scanning entry points, and the same sequence of announcements gives the same
catalog on every bus. Identity is the content hash together with the package
reference. A generation older than or equal to the one held is rejected and
counted, so a delayed record cannot undo a newer one, and a withdrawn entry keeps
the newest withdrawal's generation so a delayed older announcement cannot
resurrect it.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_announce_refusal_reason import EnumAnnounceRefusalReason
from omnibase_core.enums.enum_announcement_operation import EnumAnnouncementOperation
from omnibase_core.enums.enum_catalog_entry_state import EnumCatalogEntryState
from omnibase_core.models.events.contract_registration.model_node_announcement import (
    ModelNodeAnnouncement,
)
from omnibase_core.models.nodes.package_announce.model_catalog_change import (
    ModelCatalogChange,
)
from omnibase_core.models.nodes.package_announce.model_catalog_entry import (
    ModelCatalogEntry,
)
from omnibase_core.models.nodes.package_announce.model_catalog_outcome import (
    ModelCatalogOutcome,
)
from omnibase_core.models.nodes.package_announce.model_node_announce_policy import (
    ModelNodeAnnouncePolicy,
)


class ModelNodeCatalog(BaseModel):
    """Catalog entries by contract name, under one policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: ModelNodeAnnouncePolicy
    entries: dict[str, ModelCatalogEntry] = Field(default_factory=dict)
    stale_generation_rejections: int = 0

    def lookup(self, name: str) -> ModelCatalogEntry | None:
        """Return the entry for a name, or ``None`` when the name was never announced."""
        return self.entries.get(name)

    def apply(
        self,
        announcement: ModelNodeAnnouncement,
        *,
        installed_bytes: bytes | None = None,
        installed_path: Path | None = None,
    ) -> tuple["ModelNodeCatalog", ModelCatalogOutcome, tuple[ModelCatalogChange, ...]]:
        """Apply one announcement; return the next catalog, the outcome and the changes.

        Args:
            announcement: The record to apply.
            installed_bytes: The installed contract file's bytes, read by the caller;
                needed for an ``announce`` and ignored for a ``withdraw``.
            installed_path: Where the caller found that file, kept on the entry.
        """
        held = self.entries.get(announcement.entity_id)
        if held is not None and announcement.generation <= held.generation:
            return (
                self.model_copy(
                    update={
                        "stale_generation_rejections": self.stale_generation_rejections
                        + 1
                    }
                ),
                self._refusal(announcement, EnumAnnounceRefusalReason.STALE_GENERATION),
                (),
            )
        if announcement.operation is EnumAnnouncementOperation.WITHDRAW:
            return self._withdraw(announcement, held)
        return self._announce(announcement, held, installed_bytes, installed_path)

    def _with(self, entry: ModelCatalogEntry) -> "ModelNodeCatalog":
        return self.model_copy(update={"entries": {**self.entries, entry.name: entry}})

    def _withdraw(
        self, announcement: ModelNodeAnnouncement, held: ModelCatalogEntry | None
    ) -> tuple["ModelNodeCatalog", ModelCatalogOutcome, tuple[ModelCatalogChange, ...]]:
        authority = self.policy.authoritative_announcers.get(
            announcement.package.distribution
        )
        if authority != announcement.announcer_id:
            return (
                self,
                self._refusal(
                    announcement, EnumAnnounceRefusalReason.NON_AUTHORITATIVE_ANNOUNCER
                ),
                (),
            )
        entry = _entry_from(
            announcement,
            EnumCatalogEntryState.WITHDRAWN,
            contract_path=held.contract_path if held is not None else None,
        )
        return (
            self._with(entry),
            self._acceptance(announcement, entry.state),
            (_change(held, entry),),
        )

    def _announce(
        self,
        announcement: ModelNodeAnnouncement,
        held: ModelCatalogEntry | None,
        installed_bytes: bytes | None,
        installed_path: Path | None,
    ) -> tuple["ModelNodeCatalog", ModelCatalogOutcome, tuple[ModelCatalogChange, ...]]:
        if (
            held is not None
            and held.state is not EnumCatalogEntryState.WITHDRAWN
            and held.content_hash == announcement.content_hash
            and held.package == announcement.package
        ):
            refreshed = held.model_copy(
                update={
                    "generation": announcement.generation,
                    "announcer_id": announcement.announcer_id,
                }
            )
            return (
                self._with(refreshed),
                self._acceptance(announcement, refreshed.state),
                (),
            )
        announced = _entry_from(announcement, EnumCatalogEntryState.ANNOUNCED)
        admission = self.policy.admit(announcement, installed_bytes)
        if admission.refusal_reason is None:
            final = announced.model_copy(
                update={
                    "state": EnumCatalogEntryState.ADMITTED,
                    "contract_path": installed_path,
                }
            )
            return (
                self._with(final),
                self._acceptance(announcement, final.state),
                (_change(held, announced), _change(announced, final)),
            )
        refused = announced.model_copy(
            update={
                "state": EnumCatalogEntryState.REFUSED,
                "contract_path": installed_path,
                "refusal_reason": admission.refusal_reason,
            }
        )
        return (
            self._with(refused),
            ModelCatalogOutcome(
                name=announcement.entity_id,
                generation=announcement.generation,
                accepted=False,
                state=refused.state,
                refusal_reason=admission.refusal_reason,
            ),
            (_change(held, announced), _change(announced, refused)),
        )

    @staticmethod
    def _acceptance(
        announcement: ModelNodeAnnouncement, state: EnumCatalogEntryState
    ) -> ModelCatalogOutcome:
        return ModelCatalogOutcome(
            name=announcement.entity_id,
            generation=announcement.generation,
            accepted=True,
            state=state,
        )

    @staticmethod
    def _refusal(
        announcement: ModelNodeAnnouncement, reason: EnumAnnounceRefusalReason
    ) -> ModelCatalogOutcome:
        return ModelCatalogOutcome(
            name=announcement.entity_id,
            generation=announcement.generation,
            accepted=False,
            refusal_reason=reason,
        )


def _entry_from(
    announcement: ModelNodeAnnouncement,
    state: EnumCatalogEntryState,
    *,
    contract_path: Path | None = None,
) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        name=announcement.entity_id,
        state=state,
        content_hash=announcement.content_hash,
        package=announcement.package,
        node_kind=announcement.node_kind,
        declared_topics=announcement.declared_topics,
        handler_dependencies=announcement.handler_dependencies,
        announcer_id=announcement.announcer_id,
        generation=announcement.generation,
        contract_path=contract_path,
    )


def _change(
    previous: ModelCatalogEntry | None, entry: ModelCatalogEntry
) -> ModelCatalogChange:
    return ModelCatalogChange(
        previous_state=previous.state if previous is not None else None, entry=entry
    )
