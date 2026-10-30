# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Policy the lane overlay supplies to the catalog, and admission under it (OMN-21589).

Every value is an overlay binding with no default in code. Admission is a pure
function of the announcement, the policy and the installed file's bytes, so the
local catalog (in-memory bus) and the registry (durable bus) refuse for the same
typed reasons: the file is read by the caller, never here.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_announce_refusal_reason import EnumAnnounceRefusalReason
from omnibase_core.models.events.contract_registration.model_node_announcement import (
    ModelNodeAnnouncement,
)
from omnibase_core.models.nodes.package_announce.model_announce_admission_result import (
    ModelAnnounceAdmissionResult,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates


def _handler_modules(contract: dict[object, object]) -> list[str]:
    routing = contract.get("handler_routing")
    handlers = routing.get("handlers") if isinstance(routing, dict) else None
    modules: list[str] = []
    if not isinstance(handlers, list):
        return modules
    for entry in handlers:
        if not isinstance(entry, dict):
            continue
        handler = entry.get("handler")
        module = handler.get("module") if isinstance(handler, dict) else None
        module = module or entry.get("handler_module")
        if isinstance(module, str) and module:
            modules.append(module)
    return modules


class ModelNodeAnnouncePolicy(BaseModel):
    """What this lane admits and who may withdraw what.

    Attributes:
        trusted_handler_prefixes: Module prefixes a contract's handlers may live under.
        active_profiles: Runtime profiles this lane owns.
        authoritative_announcers: Distribution name to the one announcer allowed to
            withdraw its contracts.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    trusted_handler_prefixes: tuple[str, ...]
    active_profiles: tuple[str, ...]
    authoritative_announcers: dict[str, UUID]

    def admit(
        self, announcement: ModelNodeAnnouncement, installed_bytes: bytes | None
    ) -> ModelAnnounceAdmissionResult:
        """Check the installed file, the handler prefixes and the profiles, in that order.

        Args:
            announcement: The record being admitted.
            installed_bytes: The installed contract file's bytes as read by the
                caller, or ``None`` when the file is not installed.
        """
        if installed_bytes is None:
            return ModelAnnounceAdmissionResult(
                refusal_reason=EnumAnnounceRefusalReason.INSTALLED_FILE_MISSING
            )
        if (
            ModelNodeAnnouncement.canonical_content_hash(installed_bytes)
            != announcement.content_hash
        ):
            return ModelAnnounceAdmissionResult(
                refusal_reason=EnumAnnounceRefusalReason.HASH_MISMATCH
            )
        contract = load_yaml_mapping_no_duplicates(
            installed_bytes.decode("utf-8"), source=announcement.entity_id
        )
        for module in _handler_modules(contract):
            if not module.startswith(self.trusted_handler_prefixes):
                return ModelAnnounceAdmissionResult(
                    refusal_reason=EnumAnnounceRefusalReason.HANDLER_OUTSIDE_TRUSTED_PREFIXES
                )
        profiles = contract.get("runtime_profiles")
        if (
            isinstance(profiles, list)
            and profiles
            and not any(profile in self.active_profiles for profile in profiles)
        ):
            return ModelAnnounceAdmissionResult(
                refusal_reason=EnumAnnounceRefusalReason.PROFILE_NOT_OWNED
            )
        return ModelAnnounceAdmissionResult()
