"""TypedDict for default output state from contract state reducer."""

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.enums.enum_onex_status import EnumOnexStatus
    from omnibase_core.models.primitives.model_semver import ModelSemVer


class TypedDictDefaultOutputState(TypedDict):
    """TypedDict for default output state from contract state reducer."""

    status: "EnumOnexStatus"
    message: str
    version: "ModelSemVer"
